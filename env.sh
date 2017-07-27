#!/usr/bin/env bash
set -vx
export HERE=$(dirname $(realpath $0))
export IMG=mzn-ami-hvm-2017.03.rc-0.20170320-x86_64-gp2
export BILLING_INFO=cyan
export SSH_KEY_NAME=$(echo $SSH_KEY_FILE|awk -F'/' '{print $NF}')
export INSTANCE_PROFILE=build-agent
export instance_type=t2.small
export EBS_OPTIONS="--block-device-mappings file://$HERE/block-device-mapping.json"
export SECURITY_GROUP...