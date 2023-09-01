#!/bin/bash

# ./ani-patch.sh - reverts the changes so one can pull without conflicts
# 0 - changes to fullscreen, full volume
# 1 - adds higher saturation on top of the 0 parameters
# 2	- changes the audio delay for bluetooth and also fullscreen

declare -r DIR="$HOME/git/ani-cli"
declare -r FILE="$(which ani-cli)"

orig="        mpv\*) nohup \"\$player_function\""
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
	* ) echo "bad argument" && exit 1;;
esac

# write param changes in ani-cli
sed -i --follow-symlinks "s/^${orig}/${new}/" "$FILE"
# change the title so that it looks nicer
sed -i --follow-symlinks "s/\\\{allanime_title/\\\{title/" "$FILE"