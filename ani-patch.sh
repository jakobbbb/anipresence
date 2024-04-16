#!/bin/bash

declare -r DIR="$HOME/git/ani-cli"
declare -r FILE="$(which ani-cli)"

help() {
    echo "./ani-patch.sh - reverts the changes so one can pull without conflicts"
    echo "0 - changes to fullscreen, full volume"
    echo "1 - adds higher saturation on top of the 0 parameters"
    echo "2 - changes the audio delay for bluetooth and also fullscreen"
    exit 0
}

# have noch checked out the skip feature, orig below might need to be uncommented instead
# orig="                nohup \"\$player_function\" \$skip_flag --force-media-title=\"\${allanime_title}Episode \${ep_no}\" \"\$episode\""
orig="                nohup \"\$player_function\""
zero="$orig --volume=100 --fs"
one="$zero --saturation=45"
two="$orig --audio-delay=-2.44 --fs"

# cleanup
if [ -d "$DIR" ]; then
	cd "$DIR" || exit 1
	git restore ani-cli
	[ $# != "1" ] && git pull && exit
fi
# args
case $1 in
	"0" ) new="$zero";;
	"1" ) new="$one";;
	"2" ) new="$two";;
	* ) echo "bad argument" && help;;
esac

# write param changes in ani-cli
sed -i --follow-symlinks "s/^${orig}/${new}/" "$FILE"
