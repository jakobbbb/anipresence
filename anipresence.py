#!/usr/bin/env python3

import time
from typing import Pattern, Union
from pypresence import Presence
import os
import re
import requests
import json


class MetaDataCache:
    cache = {}
    cache_path = None

    def __init__(self, cache_path):
        self.cache_path = cache_path
        self.cache = {}
        cache_dir = os.path.dirname(self.cache_path)
        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir)
        if os.path.exists(self.cache_path):
            with open(self.cache_path, "r") as f:
                self.cache = json.loads(f.read())
        else:
            self._write_cache()

    def _write_cache(self):
        with open(self.cache_path, "w+") as f:
            f.write(json.dumps(self.cache, indent=4))

    def get_cover_image_url(self, title, epcount, fallback="watching") -> str:
        key = f"{title} -- {epcount}"

        if key not in self.cache.keys():
            self.cache[key] = self._get_cover_image_url(
                title, epcount, fallback
            )
            self._write_cache()

        return self.cache[key]

    def _get_cover_image_url(self, title, epcount, fallback="watching") -> str:
        if epcount is not None:
            epcount = int(epcount)

        query = """
            query($title: String) {
              Page(page: 1, perPage: 10) {
                media(search: $title, type: ANIME) {
                  title {
                    romaji
                    english
                  }
                  episodes
                  coverImage {
                    medium
                  }
                }
              }
            }
        """
        variables = {"title": title}
        url = "https://graphql.anilist.co"

        print("Requesting", variables)
        resp = requests.post(
            url, json={"query": query, "variables": variables}
        )
        print(resp.text)
        if not resp.status_code == 200:
            return fallback

        animes = list(resp.json()["data"]["Page"]["media"])
        anime = None

        if len(animes) > 1:
            filtered_a = list(
                filter(
                    lambda a: a["title"]["romaji"].lower() == title.lower()
                    and a["episodes"] == epcount,
                    animes,
                )
            )
            filtered_b = list(
                filter(
                    lambda a: a["title"]["romaji"].lower() == title.lower(),
                    animes,
                )
            )
            filtered_c = list(
                filter(lambda a: a["episodes"] == epcount, animes)
            )

            for li in [filtered_a, filtered_b, filtered_c]:
                if len(li) == 1:
                    anime = li[0]
                    break
        elif len(animes) == 1:
            anime = animes[0]

        if anime is not None:
            return anime["coverImage"]["medium"]
        return fallback


class AniPlayerRegex:
    pattern: Pattern
    has_epcount: bool
    is_hyphenated: bool

    def __init__(self, pattern_str, has_epcount, is_hyphenated):
        self.pattern = re.compile(pattern_str)
        self.has_epcount = has_epcount
        self.is_hyphenated = is_hyphenated


class AniPresence:
    anime = None

    regexes = [
        AniPlayerRegex(
            r".*mpv.*--force-media-title=(?P<title>.*) \((?P<epcount>[0-9]+) "
            r"episodes.*episode-(?P<ep>[^-]+).*",
            has_epcount=True,
            is_hyphenated=False,
        ),
        AniPlayerRegex(
            r".*mpv.*--force-media-title=(?P<title>.*)-"
            r"episode-(?P<ep>[^-]+).*",
            has_epcount=False,
            is_hyphenated=True,
        ),
        AniPlayerRegex(
            r".*mpv.*--force-media-title=(?P<title>.*) "
            r"Episode (?P<ep>[0-9]+).*",
            has_epcount=False,
            is_hyphenated=False,
        ),
    ]

    CACHE_PATH = os.path.expanduser("~/.cache/anipresence/cover.json")
    cache: MetaDataCache
    mpv_pid = None
    rpc: Union[Presence, None] = None
    rpc_connected = False

    def __init__(self, client_id):
        if self.other_is_running():
            print("Other instance already running.")
            return
        print("Initializing RPC...")
        self.rpc = Presence(client_id)
        self.rpc.connect()
        self.rpc_connected = True
        print("...done")
        self.cache = MetaDataCache(self.CACHE_PATH)

    def __del__(self):
        if self.rpc is not None and self.rpc_connected:
            self.rpc.clear()
            self.rpc.close()

    def get_anime(self):
        if self.mpv_pid is not None and self.mpv_pid != "PID":
            try:
                mpv_pid = int(self.mpv_pid)
                os.kill(mpv_pid, 0)
            except OSError:
                print("Our mpv died")
                return None, None
        ps = os.popen("ps aux").read()
        for line in ps.splitlines():
            pid = re.split(r"[ ]+", line)[1]
            for regex in self.regexes:
                if m := regex.pattern.fullmatch(line):
                    if self.mpv_pid is not None:
                        self.mpv_pid = pid
                    return (
                        (
                            m.group("title"),
                            m.group("ep"),
                            m.group("epcount") if regex.has_epcount else None,
                        ),
                        regex.is_hyphenated,
                    )
        self.mpv_pid = None
        return None, None

    def update(self):
        anime_new, hyphenated = self.get_anime()
        print(anime_new)

        if anime_new is None or self.rpc is None:
            return False

        if self.anime == anime_new:
            return True

        self.anime = anime_new

        title, ep, epcount = self.anime

        if hyphenated:
            title = " ".join([word.capitalize() for word in title.split("-")])

        print(f"Watching {title} episode {ep}, epcount {epcount}")

        ep_line = f"Episode {ep}"
        if epcount is not None and epcount == "1":
            ep_line = "Watching"

        self.rpc.clear()

        self.rpc.update(
            details=f"{title}",
            state=ep_line,
            large_image=self.try_get_cover_image_url(title, epcount),
            start=int(time.time()),
        )
        print(f"Updated RPC with {title} and ep {ep}")

        return True

    def try_update(self):
        try:
            print("Updating")
            return self.update()
        except Exception as e:
            print(e)
            return True

    def loop(self):
        if self.other_is_running():
            return
        while self.try_update():
            time.sleep(2)

    def other_is_running(self):
        pid = os.getpid()
        return (
            "python3"
            in os.popen(f"ps aux | grep anipresence | grep -v {pid}").read()
        )

    def try_get_cover_image_url(
        self, title, epcount, fallback="watching"
    ) -> str:
        try:
            return self.cache.get_cover_image_url(title, epcount, fallback)
        except Exception as e:
            print(e)
            return fallback


def main():
    client_id = "908703808966766602"
    try:
        if a := AniPresence(client_id):
            a.loop()
    except ConnectionRefusedError:
        print("Connection refused.  Is Discord running?")


if __name__ == "__main__":
    main()
