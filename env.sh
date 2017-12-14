#!/usr/bin/env bash
set -vx
export HERE=$(dirname $(realpath $0))
export IMG=amzn-ami-hvm-2017.09.1.20171120-x86_64-gp2
export BILLING_INFO=gateway
export SSH_KEY_NAME=$(echo $SSH_KEY_FILE|awk -F'/' '{print $NF}')
export INSTANCE_PROFILE=build-agent
export instance_type=t2.small
export EBS_OPTIONS="--block-device-mappings file://$HERE/block-device-mapping.json"
export SECURITY_GROUP=cheney-desktop
export subnet=subnet-49d36f12
export vpc=vpc-2aea144c
