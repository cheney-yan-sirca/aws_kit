#!/usr/bin/env zsh

mkdir ~/work;
mkdir ~/bin/
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
mv ~/rsync_remote.sh ~/bin/
~/.tmuxinator/prepare-env.py

#=============== using zsh============================================
wget https://raw.github.com/robbyrussell/oh-my-zsh/master/tools/install.sh -O - | sh
mkdir ~/.oh-my-zsh/completions
mv ~/_mux ~/.oh-my-zsh/completions
zsh -c "autoload -U compinit"
zsh -c "compinit"

echo >> ~/.zshrc <<EOF
export PATH="$PATH:$HOME/bin"
#unsetopt share_history
alias cld='cloud_ssh_util -F ~/.ssh/config'
unsetopt share_history
EOF

sed -i 's/ZSH_THEME.*/ZSH_THEME="blinks"/g' ~/.zshrc

#======================================================================
mv '~/*.sh' ~/bin/

