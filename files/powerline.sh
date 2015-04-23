#!/usr/bin/env bash


CLOCK=""
CALENDAR=""

WIDTH=${1}

SMALL=80
MEDIUM=140


if [ "$WIDTH" -ge "$SMALL" ]; then
   LOG="#[fg=colour16,bg=colour252,bold,noitalics,nounderscore][$(cd /tmp; ls tmux-session-log-*log |  sed  's/^tmux-session-log-//g' | sed 's/.log$//' | tr '\n' ' ')]#[fg=colour252,bg=colour236,bold,noitalics,nounderscore]"
fi

if [ "$WIDTH" -ge "$SMALL" ]; then
   IP="$(cat /tmp/temp_file_for_ip)"
fi

if [ "$WIDTH" -ge "$SMALL" ]; then
  UNAME="#[fg=colour16,bg=colour252,bold,noitalics,nounderscore]$(uname -n)#[fg=colour252,bg=colour236,bold,noitalics,nounderscore]"
fi
if [ "$WIDTH" -ge "$SMALL" ]; then
DATE="$(date +'%D')"
fi
TIME="$(date +'%H:%M')"

echo "$LOG $MPD $DATE $TIME $UNAME $IP"
