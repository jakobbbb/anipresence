#!/usr/bin/env python3

import os
import re
import requests
import json
import argparse
import time

from typing import Pattern, Union
from enum import Enum

from pypresence import Presence
# check pypresence ActivityType support
try:
    from pypresence import ActivityType
    ACTIVITY_TYPE_SUPPORT = True
except ImportError:
    ACTIVITY_TYPE_SUPPORT = False


class TitleFormat(Enum):
    ROMAJI = 1
    NATIVE = 2
    ENGLISH = 3    

class Anime:
    display_title = mpv_title = ""
    imglink = "watching" # fallback is set by default
    currep = 1
    epcount = duration = 0
    hyphenated = False
    title_format = TitleFormat.ROMAJI

    def __init__(self, title, currep, hyphenated, format):
        self.display_title = self.mpv_title = title
        self.currep = currep
        self.hyphenated = hyphenated
        self.title_format = format


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
            with open(self.cache_path, "r", encoding='utf-8') as f:
                self.cache = json.loads(f.read())
        else:
            self._write_cache()

    def _write_cache(self):
        with open(self.cache_path, "w+", encoding='utf-8') as f:
            f.write(json.dumps(self.cache, indent=4))

    def get_cover_image_url(self, anime:Anime, fallback="watching") -> Anime:
        # new key since epcount can't be determined until after the AL query
        key = anime.mpv_title

        if key not in self.cache.keys():
            new_anime = self._get_cover_image_url(
                anime, fallback
            )
            # creating the new anime json object
            self.cache[key]= {
                "displaytitle"  : new_anime.display_title,
                "epcount"       : new_anime.epcount,
                "duration"      : new_anime.duration,
                "imglink"       : new_anime.imglink
            }
            self._write_cache()
            return new_anime

        updated_anime = anime
        updated_anime.display_title = self.cache[key]["displaytitle"]
        updated_anime.epcount       = self.cache[key]["epcount"]
        updated_anime.duration      = self.cache[key]["duration"]
        updated_anime.imglink       = self.cache[key]["imglink"]
        return updated_anime

    def _get_cover_image_url(self, anime:Anime, fallback="watching") -> Anime:

        query = """
            query($title: String) {
              Page(page: 1, perPage: 10) {
                media(search: $title, type: ANIME) {
                  title {
                    romaji
                    english
                    native
                  }
                  synonyms
                  episodes
                  duration
                  coverImage {
                    medium
                  }
                }
              }
            }
        """
        variables = {"title": anime.mpv_title}
        url = "https://graphql.anilist.co"

        print("Requesting", variables)
        resp = requests.post(
            url, json={"query": query, "variables": variables}
        )
        if not resp.status_code == 200:
            return fallback

        json_animes = list(resp.json()["data"]["Page"]["media"])
        json_anime = None

        if len(json_animes) > 1:
            # romaji
            filtered_a = list(
                filter(
                    lambda a: a["title"]["romaji"].lower() == anime.mpv_title.lower(),
                    json_animes,
                )
            )
            # english
            filtered_b = list(
                filter(
                    lambda a: a["title"]["english"] is not None and a["title"]["english"].lower() == anime.mpv_title.lower(),
                    json_animes,
                )
            )
            # synonyms
            filtered_c = list(
                filter(
                    lambda a: len(a["synonyms"]) != 0 and any(i.lower() == anime.mpv_title.lower() for i in a["synonyms"]),
                    json_animes,
                )
            )

            for li in [filtered_a, filtered_b, filtered_c]:
                if len(li) == 1:
                    json_anime = li[0]
                    break
        elif len(json_animes) == 1:
            json_anime = json_animes[0]

        # todo check if english title exists?
        if json_anime is not None:
            if anime.title_format == TitleFormat.NATIVE:
                anime.display_title = json_anime["title"]["native"]
            elif anime.title_format == TitleFormat.ENGLISH:
                anime.display_title = json_anime["title"]["english"]
            anime.epcount = json_anime["episodes"]
            anime.duration = json_anime["duration"]
            anime.imglink = json_anime["coverImage"]["medium"]

        return anime


class AniPlayerRegex:
    pattern: Pattern
    is_hyphenated: bool

    def __init__(self, pattern_str, is_hyphenated):
        self.pattern = re.compile(pattern_str)
        self.is_hyphenated = is_hyphenated


class AniPresence:
    anime: Anime

    regexes = [
        AniPlayerRegex(
            r".*mpv.*--force-media-title=(?P<title>.*)-"
            r"episode-(?P<ep>[^-]+).*",
            is_hyphenated=True,
        ),
        AniPlayerRegex(
            r".*mpv.*--force-media-title=(?P<title>.*) "
            r"Episode (?P<ep>[0-9]+).*",
            is_hyphenated=False,
        ),
    ]

    CACHE_PATH = os.path.expanduser("~/.cache/anipresence/cover.json")
    cache: MetaDataCache
    mpv_pid = None
    rpc: Union[Presence, None] = None
    rpc_connected = False
    title_format = TitleFormat.ROMAJI # fallback if not set

    def __init__(self, client_id, title_format):
        if self.other_is_running():
            print("Other instance already running.")
            return
        print("Initializing RPC...")
        self.rpc = Presence(client_id)
        self.rpc.connect()
        self.rpc_connected = True
        print("...done")
        self.anime = Anime
        self.title_format = title_format
        self.cache = MetaDataCache(self.CACHE_PATH)

    def __del__(self):
        if self.rpc is not None and self.rpc_connected:
            self.rpc.clear()
            self.rpc.close()

    def get_anime(self) -> Anime:
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
                    return Anime(
                        m.group("title"),
                        m.group("ep"),
                        regex.is_hyphenated,
                        self.title_format
                    )
        self.mpv_pid = None
        return None

    def update(self):
        # get currently playing anime from mpv (usually in romaji)
        newanime = self.get_anime()

        if newanime is None or self.rpc is None:
            return False

        if self.anime.mpv_title == newanime.mpv_title and self.anime.currep == newanime.currep:
            return True

        self.anime = newanime

        if self.anime.hyphenated and self.title_format != TitleFormat.NATIVE :
            self.anime.display_title = " ".join([word.capitalize() for word in self.anime.mpv_title.split("-")])

        # set relevant values for anime object from cache / AL
        self.try_get_cover_image_url()

        print(f"Watching {self.anime.mpv_title} episode {self.anime.currep}, epcount {self.anime.epcount}")

        ep_line = f"Episode {self.anime.currep}"
        if self.anime.epcount != 0:
            ep_line = f"{ep_line} / {self.anime.epcount}"
        if self.anime.epcount == 1:
            ep_line = "Watching"
        

        update_args = {
            "details": f"{self.anime.display_title}",
            "state": ep_line,
            "large_image":self.anime.imglink,
            "start": int(time.time()),
            "end": int(time.time()) + int(self.anime.duration) * 60
        }
        self.rpc.clear()

        if ACTIVITY_TYPE_SUPPORT:
            self.rpc.update(activity_type=ActivityType.WATCHING, **update_args)
        else:
            self.rpc.update(**update_args)
        print(f"Updated RPC with {self.anime.display_title} {ep_line}")

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

    def try_get_cover_image_url(self, fallback="watching"):
        try:
            self.anime = self.cache.get_cover_image_url(self.anime, fallback)
        except Exception as e:
            print(e)
            return


def main():
    # parsing
    parser = argparse.ArgumentParser(
        prog="anipresence", description="Dicord rpc for ani-cli"
    )
    parser.add_argument(
        "-t",
        "--titleformat",
        nargs="?",
        choices=['r', 'romaji', 'n', 'native', 'e', 'english'],
        default=TitleFormat.ROMAJI,
        help="which title to use ([R]omaji/ [n]ative / [e]nglish)"
    )
    args = parser.parse_args()
    if args.titleformat == 'n' or args.titleformat == 'native':
        title_format = TitleFormat.NATIVE
    elif args.titleformat == 'e' or args.titleformat == 'english':
        title_format = TitleFormat.ENGLISH
    else:
        title_format = TitleFormat.ROMAJI
    print(f"using {title_format} for displaying titles")

    # rpc 
    client_id = "908703808966766602"
    try:
        if a := AniPresence(client_id, title_format):
            a.loop()
    except ConnectionRefusedError:
        print("Connection refused.  Is Discord running?")


if __name__ == "__main__":
    main()
