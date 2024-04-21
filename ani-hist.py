#!/usr/bin/env python3

# small script to update your ani-cli history via anilist
# useful when using the former on multiple devices
# without having a syncthing or sth. similar set up

import requests
import json
import os.path
import re
import sys
import time
import signal
from subprocess import Popen, PIPE

def get_al_list(username, medium="ANIME", status="CURRENT"):
        query = '''
    query ($username: String, $type: MediaType, $status: MediaListStatus) {
        MediaListCollection(userName: $username, type: $type, status: $status) {
            lists {
                entries {
                    media {
                        title {
                            romaji
                        }
                        episodes
                    }
                progress
                }
            }
        }
    }
        '''
        variables = {
            'username': username,
            'type': medium,
            'status': status
        }

        url = 'https://graphql.anilist.co'

        response = requests.post(url, json={'query': query, 'variables': variables})

        if not response.status_code == 200:
           print(str(response.status_code) + " could not retrieve data\n" + response.text)
           return
        return json.loads(response.text)["data"]["MediaListCollection"]["lists"][0]["entries"]

def get_ac_list(hist_path, hist_file):
    tmp_res = []
    if not os.path.isfile(hist_path + hist_file):
        print("no histfile found, path is " + hist_path)
        res = input("would you like to create a file at that location? [y/N]")
        if res == "N" or res == "n" or res == "":
            sys.exit(1)
        if not os.path.exists(hist_path):
            os.makedirs(hist_path)
        with open(hist_path + hist_file, 'w') as nf:
            nf.write("")
        return tmp_res
    with open(hist_path + hist_file) as hsf:
        for line in hsf:
            # make it presentable
            tmp = line.split("\t")
            # remove ep count
            # could be improved by going from the left removing everything till "(" +1
            tmp.append(re.sub(" \([0-9]+ episodes\)\n", "", tmp[2]))
            tmp_res.append(tmp)
    return tmp_res

def get_hash(ale, ace):
    hash = []
    for i in ale:
        found = False
        for j in ace:
            if i["media"]["title"]["romaji"].casefold() == j[3].casefold():
                found = True
                hash.append(j[1])
                ace.remove(j)
                break
        if found == False:
            hash.append("0")
            print("couldn't find hash for \"" + i["media"]["title"]["romaji"] + "\" in hist")
    return hash

def update_list(ale, hl):
    entries = []
    idx = 0
    for i in ale:
        if hl[idx] != "0":
            s = str(i["progress"]) + "\t" + str(hl[idx]) + "\t" + i["media"]["title"]["romaji"] + " (" + str(i["media"]["episodes"]) +" episodes)\n"
            entries.append(s)
            idx = idx + 1
    return entries

def main():
    # hardcoded for now, can also be found with grep ^histfile $(which ani-cli)
    ac_hist_path = os.path.expanduser("~/.local/state/ani-cli/")
    ac_hist_file ="ani-hsts"
    ac_hist_old = "ani-hsts.bak"
    # specify your username via arg1 (./ani-hist.py testuser)
    user = sys.argv[1]
    al_entries = get_al_list(user)
    ac_entries = get_ac_list(ac_hist_path, ac_hist_file)
    hash_list = get_hash(al_entries, ac_entries)

    new_entries = update_list(al_entries, hash_list)

    # append titles to backup file
    with open(ac_hist_path + ac_hist_old, "a") as bak:
        for i in ac_entries:
            bak.write(str(i[0]) + "\t" + str(i[1]) + "\t" + str(i[2]))

    # overwrite hist
    with open(ac_hist_path + ac_hist_file, "w") as newhs:
        for i in new_entries:
            newhs.write(i)

    idx = 0
    for i in al_entries:
        if hash_list[idx] == "0":
            process = Popen(["ani-cli", i["media"]["title"]["romaji"], "-e", str(i["progress"])], stdout=PIPE, stdin=PIPE)
            # TODO fix
            # while mpv has no pid -> sleep, else wait 1s, kill
            # pid = os.popen(f"ps aux | grep mpv | grep \"title=" + i["media"]["title"]["romaji"] + "\" | awk '{print $2}'").read()
            # print(pid)
            # ugly and bad but it wouldnt cooperate with pid stuff :(
            # ideally os.kill(pid, signal.SIGKILL)
            time.sleep(5)
            os.popen(f"pkill -9 mpv")
            process.kill()
        idx = idx + 1

if __name__ == "__main__":
    main()
