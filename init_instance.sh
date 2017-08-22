#!/usr/bin/env bash                         
HERE=$(cd $(dirname $0) ; pwd)
EC2_USER=ec2-user

set -evx
function usage() {
    cat >&2 <<EOF
Usage: $0 [-h] -H host_ip  [-K SSH_KEY_FILE] [-U EC2_USER_NAME] [-R] -r remote_name [-S(setup_ssh_auth) true|false]

OPTIONS
    -h                          This help
    -H host_ip                The remote host domain name or ip
    -K SSH_KEY_FILE             If not provided, it will use \$SSH_KEY_FILE
    -U EC2_USER_NAME             If not provided, it will use 'ec2-user'
    -R set RESET_KEY             If set, replace the original SSH_KEY with local personal identity
    -r remote_name             Give it a remote host name.
    -S setup_ssh_auth         Do we need to setup net authentication. Default is true

EOF
    exit 1
}

while getopts 'K:H:U:r:S:N:hR' o; do
    case "$o" in
        H) host_ip=$OPTARG;;
        K) SSH_KEY_FILE=$OPTARG;;
        U) EC2_USER=$OPTARG;;
        r) remote_name=$OPTARG;;
        R) replace_key="true";;
        S) set_ssh_auth=$OPTARG;;
        *) usage;;
    esac
done

[[ "$SSH_KEY_FILE" == "" ]] && echo "Must provide SSH_KEY_FILE" && exit
[[ "$host_ip" == "" ]] && echo "Must provide remote host IP" && exit
[[ "$remote_name" == "" ]] && echo "Must provide a friendly name to the host" && exit
### replace key for security
if [ "$set_ssh_auth" == "true" ]; then
  sed -i "s/^Host ${remote_name}$/Host ${remote_name}.$(date +%s)/" ~/.ssh/config
  if [ "$replace_key" == "true" ]; then
    cat ~/.ssh/id_rsa.pub | ssh -i $SSH_KEY_FILE $EC2_USER@$host_ip 'cat > .ssh/authorized_keys'
    cat >> ~/.ssh/config <<EOF
Host ${remote_name}
            HostName $host_ip
            User $EC2_USER
            StrictHostKeyChecking no
EOF
  else
    cat >> ~/.ssh/config <<EOF
Host ${remote_name}
            HostName $host_ip
            User $EC2_USER
            StrictHostKeyChecking no
            IdentityFile $SSH_KEY_FILE
EOF
  fi
scp  -r ~/.ssh/id_rsa* ${remote_name}:~/.ssh/
fi
scp  -r $HERE/files/* ${remote_name}:~
ssh -t -t  ${remote_name} "sudo bash /home/$EC2_USER/softwares.sh"
ssh -t -t  ${remote_name} "curl -fsSL https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh | bash || true"

rsync  -r ~/.ssh ${remote_name}:~/ --include '*.pem' -v
rsync  -r ~/bin ${remote_name}:~/ -v --exclude packer.io --exclude bookmarks --exclude .git
rsync  -r ~/.oh-my-zsh ${remote_name}:~/ -v --exclude .git
rsync  -r ~/.vim ${remote_name}:~/ -v --exclude .git
scp  -r ~/.tmux.conf ~/.*rc ${remote_name}:~/
rsync  -r ~/.tmuxinator ${remote_name}:~/ -v --exclude .git

ssh -t -t  ${remote_name} "bash /home/$EC2_USER/setup_user.sh"

echo "We are all there! Please use 'mosh ${remote_name}' to login on the remote hosts and enjoy!"

