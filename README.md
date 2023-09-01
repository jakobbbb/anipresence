# discord rich presence for ani-cli/animdl

![screenshot](https://gist.githubusercontent.com/jakobbbb/d46ec01fc919d857cf5dbc8e9b051bc8/raw/6b9ed96c5b66111b3724679d3e594fb57d7f1a71/screenshot.png)

## deps

`yay -S python-pypresence`, or a similar package on your system i guess

## how

start the `anipresence.py` after mpv has been started.
there's many ways to do this. one hacky way:
add this to your `mpv.conf`:

```ini
[discord-rpc]
profile-cond=os.execute("/path/to/anipresence.py > /dev/null &")
```


## nicer titles

patch `ani-cli`:

```diff
-       mpv*) nohup "$player_function" --force-media-title="${allanime_title}episode-${ep_no}-${mode}" "$episode" >/dev/null 2>&1 & ;;
+       mpv*) nohup "$player_function" --force-media-title="${title}episode-${ep_no}-${mode}" "$episode" >/dev/null 2>&1 & ;;
```
