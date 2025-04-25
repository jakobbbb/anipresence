# anipresence

discord rich presence for ani-cli/animdl:

<p align="center">
    <img style="width: 400px" alt="screenshot" src="https://gist.githubusercontent.com/jakobbbb/d46ec01fc919d857cf5dbc8e9b051bc8/raw/61f74b486b94df68235565119a1cd99e0b254156/screenshot.png"/>
</p>

## deps

your player must be `mpv`, and you must have either `pypresence` or `lynxpresence` installed.

from AUR: `yay -S python-pypresence` / `yay -S python-lynxpresence`.

for Discord to display 'Watching' instead of 'Playing' you'll currently need either lynxpresence or the [git version](https://github.com/qwertyquerty/pypresence#Installation) of pypresence.

for Windows it's similar in that you need mpv and either lynxpresence or pypresence, autostart however does not work. instead you can use the argument

to use the rpc with local media on Linux, you'll also need `wmctrl` (and a compatible window manager)
## how
Linux:

start the `anipresence.py` after mpv has been started.
there's many ways to do this. one hacky way:
add this to your `mpv.conf`:

```ini
[discord-rpc]
profile-cond=os.execute("/path/to/anipresence.py > /dev/null &")
```

Windows:
you can alternatively start the script with the argument `-d` or `--daemonlike` which checks every 10s if a process matches the regexes. It's called daemon-like, because it will, once started, keep running and check running processes every 10s starting the rpc and connecting to Discord if it finds a matching one.

## show titles on discord

shows usually have three official titles that AL reconizes and makes easily accessible:

`Romaji`, `Native` and `English`. for [EVA](https://anilist.co/anime/30/Shin-Seiki-Evangelion/) that would be "Shin Seiki Evangelion", "新世紀エヴァンゲリオン" and "Neon Genesis Evangelion". anipresence uses romaji as the default title format.

to select which title format to use, set argument `-t` or `--titleformat` with the options `r | romaji | n | native | e | english`. 

should you, for example, want enlish titles just change the `mpv.conf` entry to:

```ini
[discord-rpc]
profile-cond=os.execute("/path/to/anipresence.py -t e > /dev/null &")
```
_**note:**_ anipresence saves only one so called "display title". if you decide to change the title format, all shows watched _before_ this change will still show their title in the _old_ title format.
 
## nicer titles

patch `ani-cli`:

```diff
-       mpv*) nohup "$player_function" --force-media-title="${allanime_title}episode-${ep_no}-${mode}" "$episode" >/dev/null 2>&1 & ;;
+       mpv*) nohup "$player_function" --force-media-title="${title}episode-${ep_no}-${mode}" "$episode" >/dev/null 2>&1 & ;;
```

check `./ani-patch.sh` for an automated way of patching `ani-cli`
