#!/usr/bin/env zsh

mkdir ~/work;

cd ~

mv _tmux.conf .tmux.conf
mkdir .tmuxinator
mv prepare-env.py powerline.sh env.json .tmuxinator

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
wget https://raw.github.com/robbyrussell/oh-my-zsh/master/tools/install.sh -O - | sh
mkdir ~/.oh-my-zsh/completions
mv ~/_mux ~/.oh-my-zsh/completions
autoload -U compinit
compinit

echo >> ~/.zshrc << EOF
export PATH="$PATH:$HOME/bin"
#unsetopt share_history
alias cld='cloud_ssh_util -F ~/.ssh/config'
EOF

sed -i 's/ZSH_THEME.*/ZSH_THEME="agnoster"/g' ~/.zshrc

#======================================================================
mv '~/*.sh' ~/bin