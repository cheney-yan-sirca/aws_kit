#!/bin/bash
if [ $# -lt 2 ];
then
    echo Usage: $0 version from_account
    exit 1
fi
for ami_id in $(aws ec2 describe-images --owners $2 --filters Name=name,Values=*$1 | grep ImageId | awk -F'"' '{print $4}')
do
    echo copying ami: $ami_id
    copy-ami $ami_id &
done
wait
