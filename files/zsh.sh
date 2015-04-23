#!/usr/bin/env zsh

rm -rf ~/.boto;
mkdir ~/bin;
mkdir ~/data;
mkdir ~/work;

cd ~

mkdir -p ~/.config
cd ~
mv _tmux.conf .tmux.conf
mkdir .tmuxinator
mv prepare-env.py powerline.sh env.json .tmuxinator

mv *pem ~/.ssh
chmod 600 ~/.ssh/*
cat >> ~/.ssh/config << EOL
UserKnownHostsFile /dev/null
LogLevel QUIET              
StrictHostKeyChecking no    
EOL
chmod 600  ~/.ssh/config

mv _rpmmacros .rpmmacros
mv ~/rsync_remote.sh ~/bin
~/.tmuxinator/prepare-env.py init-layout


#=============== using zsh============================================
sed -i 's/bashrc/zshrc/g' ~/.zshrc
sed -i 's/ZSH_THEME.*/ZSH_THEME="agnoster"/g' ~/.zshrc
wget https://raw.github.com/robbyrussell/oh-my-zsh/master/tools/install.sh -O - | sh
mkdir ~/.oh-my-zsh/completions
mv ~/_mux ~/.oh-my-zsh/completions
autoload -U compinit
compinit

echo >> ~/.zshrc << EOF
export PATH="$PATH:$HOME/bin"
#unsetopt share_history
EOF
