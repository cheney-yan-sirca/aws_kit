#!/usr/bin/env bash                         
pushd `dirname $0` > /dev/null              
HERE=`pwd`                                  
popd > /dev/null
user_name=$(whoami|xargs)
if [ $(uname|xargs) == 'Darwin' ]; then
    home_dir="/Users/$user_name"
    sed_cmd="sed -i '' "
else
    home_dir="/home/$user_name"
    sed_cmd="sed -i "
fi

echo "Need to get root priority to update your /etc/hosts file"
sudo ls / > /dev/null
ssh-keygen -f "$home_dir/.ssh/known_hosts" -R remote
# this script will bake a new image of qa_env and launch it.

source $HERE/env.sh

## terminate instance
old_ip=$(cat /etc/hosts | grep 'remote$' | awk '{print $1}'|xargs)

old_instance_id=$(aws ec2 describe-instances --filters Name=ip-address,Values=${old_ip} | grep InstanceId  | awk -F'"' '{print $4}'|xargs)
if [ "$old_instance_id" != "" ]; then
    aws ec2 terminate-instances --instance-ids ${old_instance_id}
    echo "Terminating old instance."
    echo "At the same time, "
fi
echo "preparing the new instance"
cd $HERE

export name=$(aws ec2 describe-images --filters Name=name,Values="${IMG}" | grep '"Name"' | grep $IMG | awk -F'"' '{print $4}' | sort | tail -1 | xargs )
echo "${name} is the latest $IMG iamge."
export image_id=$(aws ec2 describe-images --filters Name=name,Values=${name} | grep '"ImageId"' | awk -F'"' '{print $4}' | sort | tail -1 | xargs )
echo "${image_id} is the iamge id for ${name}."
if [ ${image_id} == "" ]; then
    echo "Something is wrong! Could not figure out image_id"
    exit 1
fi
instance_id=$(aws ec2 run-instances --image-id ${image_id} $EBS_OPTIONS --key-name $SSH_KEY_NAME --security-groups  remote-working-desktop  --iam-instance-profile Name=$INSTANCE_PROFILE --instance-initiated-shutdown-behavior stop  --instance-type $instance_type | grep '"InstanceId"' | awk -F'"' '{print $4}' |xargs)
echo "${instance_id} is the newly generated instance id."
aws ec2 create-tags --resource ${instance_id} --tags Key=Name,Value=${user_name}-desktop
aws ec2 create-tags --resource ${instance_id} --tags Key=Billing,Value=${use}
aws ec2 create-tags --resource ${instance_id} --tags Key=User,Value=${user_name}
aws ec2 create-tags --resource ${instance_id} --tags Key=Janitor,Value='\{"expires":"never"\}'
echo "Now the instance ${user_name}-desktop is up. Please got to aws console to check the instance and do your furture operations.
You may want to update 'remote' entry in your hosts file. It will be often used in later stage."
## initialize instance with xx
public_ip=''
while [ "$public_ip" == "" ]; do
   public_ip=$(aws ec2 describe-instances --instance-id $instance_id | grep PublicIp | awk -F'"' '{print $4}' | head -n 1 | xargs )
done

sudo $sed_cmd "s/^.*\Wremote\W*$//g"  /etc/hosts
echo "$public_ip remote" | sudo tee --append /etc/hosts
echo "Wait until ssh is ready for $public_ip"
remote=$public_ip
until [ "$(nc -z -w 4 $remote 22|wc -l|xargs)" == "0" ] ;
do
    echo .
    sleep 5
done
until [ "$(ssh -o ConnectTimeout=4 -i $SSH_KEY_FILE ec2-user@$remote 'ls / | grep boot | wc -l' | xargs )" == '1' ] ;
do
   echo "."
   sleep 1
done
scp -i $SSH_KEY_FILE -o StrictHostKeyChecking=no -r files/* ec2-user@$public_ip:~
scp -i $SSH_KEY_FILE -o StrictHostKeyChecking=no ~/.ssh/id_rsa* ec2-user@$public_ip:~/.ssh/
ssh -t -t -i $SSH_KEY_FILE -o StrictHostKeyChecking=no ec2-user@$public_ip "sudo bash /home/ec2-user/softwares.sh"
ssh -t -t -i $SSH_KEY_FILE -o StrictHostKeyChecking=no ec2-user@$public_ip "bash /home/ec2-user/install_cloud_ssh_util.sh"

if [ "$old_instance_id" != "" ]; then
    echo "Wait until the old instance has been totally terminate"
    while true; do
        status=$(aws ec2 describe-instances --instance-ids $old_instance_id | grep '"Name":' | awk -F '"' '{print $4}' |xargs)
        if [[  "$status" == "" ]] || [[ "$status" == "terminated"  ]];
        then
            break
        fi
    done
fi

cat >> ~/.ssh/config <<EOF

Host remote
        IdentityFile $SSH_KEY_FILE
        HostName remote
        User ec2-user
        StrictHostKeyChecking no
EOF

echo "We are all there! Please use 'ssh remote' to login on the remote hosts and enjoy developing!"

