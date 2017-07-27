#!/usr/bin/env bash
user=$(whoami|xargs)
sudo chsh -s $(which zsh) $user

mkdir ~/work;

cat >> ~/.ssh/config << EOL
UserKnownHostsFile /dev/null
LogLevel QUIET
StrictHostKeyChecking no
EOL
chmod 600  ~/.ssh/*

