#!/usr/bin/env bash
#yum groupinstall -y 'Development Tools' # not happy with py27?
yum install -y git ruby ruby-devel rubygems gcc mysql-devel -y bash-completion zsh tmux mosh rlwrap --enablerepo epel
gem install io-console
pip install --upgrade awscli pyCLI boto3 requests[security] pylint tox twine thefuck
# working environment tools
gem install tmuxinator -v 0.6.8
gem install papertrail

echo "ServerAliveInterval 10" | tee -a /etc/ssh/ssh_config

for x in /etc/yum.repos.d/* # this will enable all the repos by default
do
    sed -i 's/^enabled=.*$/enabled=1/g' $x
done

yum install -y docker
service docker start
sudo usermod -a -G docker ec2-user

# a patch for the compinit error
chmod a-r /etc/profile.d/aws-cli.sh