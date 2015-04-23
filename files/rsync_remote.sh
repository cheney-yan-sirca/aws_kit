#!/usr/bin/env bash
#set -vx
REMOTE_ROOT_DIR='remote:~'
LOCAL_ROOT_DIR=$HOME
if [ $# -lt 1 ]; then
   echo "Usage: $0 path "
   exit 2
fi

if [ -d $1 ]; then
   sync_dir=$(cd $1;pwd)
elif [ -f $1 ]; then
   sync_dir=$(cd $(dirname $1);pwd)
else
   echo "$1 must exist"
   exit 1
fi
if [[ $sync_dir != $LOCAL_ROOT_DIR* ]]; then
   echo "$1 must be under $LOCAL_ROOT_DIR. exit"
   exit 1
fi
#OPTIONS='--delete --links --exclude="lost+found" '
OPTIONS='-zrv --exclude .tox --exclude *.pyc --exclude *~ '
remote_dir=${sync_dir/$LOCAL_ROOT_DIR/$REMOTE_ROOT_DIR}
remote_dir=$(dirname $remote_dir)
ssh remote mkdir -p ${remote_dir/remote:/}
rsync  $OPTIONS $sync_dir $remote_dir
#set +xv
