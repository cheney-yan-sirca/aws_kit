#!/usr/bin/env bash
yum groupinstall -y 'Development Tools' # not happy with py27?
yum install -y git ruby ruby-devel rubygems gcc mysql-devel python-devel bash-completion zsh tmux mosh rlwrap jq # --enablerepo epel
gem install io-console
pip install --upgrade awscli pyCLI boto3 requests[security] pylint tox twine thefuck godaddypy
# working environment tools
gem install tmuxinator -v 0.6.8
gem install papertrail
mazon-linux-extras install python3

echo "ServerAliveInterval 10" | tee -a /etc/ssh/ssh_config

for x in /etc/yum.repos.d/* # this will enable all the repos by default
do
    sed -i 's/^enabled=.*$/enabled=1/g' $x
done

yum install -y docker
service docker start
sudo usermod -a -G docker ec2-user

# a patch for the compinit error
#chmod a-r /etc/profile.d/aws-cli.sh

easy_install pip
pip install virtualenv
curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.33.6/install.sh | bash


#--------mosh
sudo yum -y install autoconf automake gcc gcc-c++ make boost-devel zlib-devel ncurses-devel protobuf-devel openssl-devel
cd /usr/local/src
sudo wget http://mosh.mit.edu/mosh-1.2.4.tar.gz
sudo tar xvf mosh-1.2.4.tar.gz
cd mosh-1.2.4
sudo ./autogen.sh
sudo ./configure
sudo make
sudo make install
#----------------
