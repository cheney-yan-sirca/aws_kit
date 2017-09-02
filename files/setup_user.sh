#!/usr/bin/env bash
sudo chsh -s $(which zsh) $USER

mkdir ~/work;

cat >> ~/.ssh/config << EOL
UserKnownHostsFile /dev/null
LogLevel QUIET
StrictHostKeyChecking no
EOL
chmod 600  ~/.ssh/*
virtualenv -p /usr/bin/python27 ~/py27
source ~/py27/bin/activate
pip install --upgrade pycli simplejson pyaml godaddypy aws-ec2-assign-elastic-ip requests[security] boto3 thefuck pyCLI
