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
