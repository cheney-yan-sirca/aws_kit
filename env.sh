#!/usr/bin/env bash
export AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:=ap-southeast-2}
export BOTO_CONFIG=${BOTO_CONFIG:=/var/tmp/tmux-session-config/dash_dev_sydney/boto_config}
#export IMG=software_development
export IMG=dash_develop
export BILLING_INFO=dash+cg-dev-dev
export SSH_KEY_FILE=${SSH_KEY_FILE:=/Users/cyan/.ssh/dash-dev-key-ap-southeast-2.pem}
export SSH_KEY_NAME=$(echo $SSH_KEY_FILE|awk -F'/' '{print $NF}'| awk -F'.' '{print $1}')
export INSTANCE_PROFILE=dev-role
#export INSTANCE_PROFILE=software-development
export AWS_CONFIG_FILE=${AWS_CONFIG_FILE:=/var/tmp/tmux-session-config/dash_dev_sydney/aws_config}
export instance_type=t2.small

