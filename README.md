# anipresence

discord rich presence for ani-cli/animdl:

<p align="center">
    <img style="width: 400px" alt="screenshot" src="https://gist.githubusercontent.com/jakobbbb/d46ec01fc919d857cf5dbc8e9b051bc8/raw/61f74b486b94df68235565119a1cd99e0b254156/screenshot.png"/>
</p>

## deps

your player must be `mpv`, and you must have either `pypresence` or `lynxpresence` installed.

from AUR: `yay -S python-pypresence` / `yay -S python-lynxpresence`.

for Discord to display 'Watching' instead of 'Playing' you'll currently need either lynxpresence or the [git version](https://github.com/qwertyquerty/pypresence#Installation) of pypresence.

for Windows it's similar in that you need mpv and either lynxpresence or pypresence,
however the autostart as described below in **how** is not working (yet) so you have to manually start it at the beginning of every episode. _proper_ Windows support should not be expected, the current state is more of a stop-gap measure to get it working at all.

## how

start the `anipresence.py` after mpv has been started.
there's many ways to do this. one hacky way:
add this to your `mpv.conf`:

```ini
[discord-rpc]
profile-cond=os.execute("/path/to/anipresence.py > /dev/null &")
```

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
