#!/usr/bin/env bash
set -vx
export HERE=$(dirname $(realpath $0))
export IMG=marq_ci_agent_201603101328
export BILLING_INFO=dash+cg-dev-dev
export SSH_KEY_NAME=$(echo $SSH_KEY_FILE|awk -F'/' '{print $NF}'| awk -F'.' '{print $1}')
export INSTANCE_PROFILE=baker-role
export instance_type=t2.micro
export EBS_OPTIONS="--block-device-mappings file://$HERE/block-device-mapping.json"
