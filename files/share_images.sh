#!/bin/bash
set -vx
if [ $# -lt 2 ];
then
    echo Usage: $0 version shared_account
    exit 1
fi

for ami_id in $(aws ec2 describe-images --filters Name=name,Values=*$1 | grep ImageId | awk -F'"' '{print $4}')
do
    echo sharing ami: $ami_id
    aws ec2 modify-image-attribute --image-id $ami_id --launch-permission "{\"Add\":[{\"UserId\":\"$2\"}]}" 
done
set +vx
