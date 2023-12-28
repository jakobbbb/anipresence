#!/usr/bin/env python3

# small script to update your ani-cli history via anilist
# useful when using the former on multiple devices
# without having a syncthing or sth. similar set up

import requests
import json
import os.path
import re
import sys

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

def get_ac_list(hist_path):
    tmp_res = []
    if not os.path.isfile(hist_path):
        print("no histfile found, path is " + hist_path)
        return
    with open(hist_path) as hsf:
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
            if i["media"]["title"]["romaji"] == j[3]:
                found = True
                hash.append(j[1])
                ace.remove(j)
                break
        if found == False:
            # this is a placeholder
            # the new title will be in the history but not show up
            # TODO add the hash gen here
            hash.append("00000000000000000")
            print("couldn't find hash for \"" + i["media"]["title"]["romaji"] + "\" in hist")
    return hash

def update_list(ale, hl):
    entries = []
    idx = 0
    for i in ale:
        s = str(i["progress"]) + "\t" + str(hl[idx]) + "\t" + i["media"]["title"]["romaji"] + " (" + str(i["media"]["episodes"]) +" episodes)\n"
        entries.append(s)
        idx = idx + 1
        print(s)
    return entries

def main():
    # hardcoded for now, can also be found with grep ^histfile $(which ani-cli)
    ac_hist = os.path.expanduser("~/.local/state/ani-cli/ani-hsts")
    ac_hist_old = os.path.expanduser("~/.local/state/ani-cli/ani-hsts.bak")
    # specify your username via arg1 (./ani-hist.py testuser)
    user = sys.argv[1]
    al_entries = get_al_list(user)
    ac_entries = get_ac_list(ac_hist)
    hash_list = get_hash(al_entries, ac_entries)

    new_entries = update_list(al_entries, hash_list)

    # append titles to backup file
    with open(ac_hist_old, "a") as bak:
        for i in ac_entries:
            bak.write(str(i[0]) + "\t" + str(i[1]) + "\t" + str(i[2]))

    # overwrite hist
    with open(ac_hist, "w") as newhs:
        for i in new_entries:
            newhs.write(i)

if __name__ == "__main__":
    main()