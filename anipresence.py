#!/usr/bin/env python3

import time
from pypresence import Presence
import os
import re
import requests
import json


class AniCliRPC:
    anime = None
    mpv_re = re.compile(
        r".*mpv.*--force-media-title=(?P<title>.*) \((?P<epcount>[0-9]+) "
        r"episodes.*episode-(?P<ep>[^-]+).*"
    )
    mpv_re_alt = re.compile(
        r".*mpv.*--force-media-title=(?P<title>.*)-episode-(?P<ep>[^-]+).*"
    )
    CACHE_PATH = os.path.expanduser("~/.cache/anipresence/cover.json")
    cache = None
    rpc: Presence

    def __init__(self, client_id):
        print("Initializing RPC...")
        self.rpc = Presence(client_id)
        self.rpc.connect()
        print("...done")

    def __del__(self):
        self.rpc.clear()
        self.rpc.close()

    def get_anime(self):
        ps = os.popen("ps aux").read()
        for line in ps.splitlines():
            if m := self.mpv_re.fullmatch(line):
                return (
                    (m.group("title"), m.group("ep"), m.group("epcount")),
                    False,
                )
            if m := self.mpv_re_alt.fullmatch(line):
                return (
                    (m.group("title"), m.group("ep"), None),
                    True,
                )
        return None, None

    def update(self):
        anime_new, hyphenated = self.get_anime()

        if anime_new is None:
            return False

        print(self.anime)
        print(anime_new)
        print(self.anime == anime_new)

        if self.anime == anime_new:
            return True

        self.anime = anime_new

        title, ep, epcount = self.anime

        if hyphenated:
            title = " ".join([word.capitalize() for word in title.split("-")])

        print(f"Watching {title} episode {ep}, epcount {epcount}")

        ep_line = (
            f"Episode {ep}"
            if epcount is not None and epcount != "1"
            else "Watching"
        )

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
            time.sleep(20)

    def other_is_running(self):
        return re.match(r"python3.*anipresence.py", os.popen("ps aux").read())

    def try_get_cover_image_url(
        self, title, epcount, fallback="watching"
    ) -> str:
        try:
            return self.get_cover_image_url(title, epcount, fallback)
        except Exception as e:
            print(e)
            return fallback

    def get_cover_image_url(self, title, epcount, fallback="watching") -> str:
        key = f"{title} -- {epcount}"
        if not self.cache:
            cachedir = os.path.dirname(self.CACHE_PATH)
            if not os.path.exists(cachedir):
                os.mkdir(cachedir)
            if os.path.exists(self.CACHE_PATH):
                with open(self.CACHE_PATH, "r") as f:
                    self.cache = json.loads(f.read())
            else:
                with open(self.CACHE_PATH, "w+") as f:
                    self.cache = {}
                    f.write(json.dumps(self.cache))

        if key not in self.cache.keys():
            self.cache[key] = self._get_cover_image_url(
                title, epcount, fallback
            )
            with open(self.CACHE_PATH, "w+") as f:
                f.write(json.dumps(self.cache))

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


def main():
    client_id = "908703808966766602"
    AniCliRPC(client_id).loop()


if __name__ == "__main__":
    main()
