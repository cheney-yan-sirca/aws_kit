#!/usr/bin/env bash
#yum groupinstall -y 'Development Tools' # not happy with py27?

yum install -y git ruby ruby-devel rubygems gcc mysql-devel -y bash-completion zsh --enablerepo epel
gem install io-console
pip install --upgrade awscli pyCLI
touch /home/ec2-user/.zshrc
chown ec2-user /home/ec2-user/.zshrc
chsh -s `which zsh` ec2-user

# working environment tools
yum install -y tmux
gem install tmuxinator -v 0.6.8
echo "ServerAliveInterval 10" | tee -a /etc/ssh/ssh_config

# prepare personal tools
runuser -l ec2-user -c 'zsh /home/ec2-user/zsh.sh'
gem install papertrail

for x in /etc/yum.repos.d/* # this will enable all the repos by default
do
    sed -i 's/^enabled=.*$/enabled=1/g' $x
done
#
#yum install -y docker
#service docker start
#sudo usermod -a -G docker ec2-user

yum install -y mosh
