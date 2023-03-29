#!/usr/bin/env python3

import time
from pypresence import Presence
import os
import re


class AniCliRPC:
    anime = None
    mpv_re = re.compile(
        r".*mpv --force-media-title=(.*)\(.*episodes.*episode-([^-]+).*"
    )
    mpv_re_alt = re.compile(
        r".*mpv --force-media-title=(.*)-episode-([^-]+).*"
    )

    def get_anime(self):
        ps = os.popen("ps aux").read()
        for line in ps.splitlines():
            if m := self.mpv_re.match(line):
                return m.groups(), False
            if m := self.mpv_re_alt.match(line):
                return m.groups(), True
        return None, None

    def update(self):
        anime_new, hyphenated = self.get_anime()

        if anime_new is None:
            return False

        if self.anime == anime_new:
            return True

        self.anime = anime_new

        title, ep = self.anime

        if hyphenated:
            title = " ".join([word.capitalize() for word in title.split("-")])

        print(f"Watching {title} episode {ep}")

        client_id = "908703808966766602"

        RPC = Presence(client_id)
        RPC.connect()
        RPC.clear()

        RPC.update(
            details=f"{title}",
            state=f"Episode {ep}",
            large_image="watching",
            start=int(time.time()),
        )
        print("Updated RPC")

        return True

    def try_update(self):
        try:
            print("Updating")
            return self.update()
        except Exception as e:
            print(e)
            return True

    def loop(self):
        while self.try_update():
            time.sleep(20)


def main():
    AniCliRPC().loop()


if __name__ == "__main__":
    main()
