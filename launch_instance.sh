#!/usr/bin/env bash                         
HERE=$(cd $(dirname $0); pwd)
popd > /dev/null
source $HERE/env.sh
echo "preparing the new instance"

export name=$(aws ec2 describe-images --filters Name=name,Values="${IMG}" | grep '"Name"' | grep $IMG | awk -F'"' '{print $4}' | sort | tail -1 | xargs )
echo "${name} is the latest $IMG iamge."
export image_id=$(aws ec2 describe-images --filters Name=name,Values=${name} | grep '"ImageId"' | awk -F'"' '{print $4}' | sort | tail -1 | xargs )
echo "${image_id} is the iamge id for ${name}."
if [ "${image_id}" == "" ]; then
    echo "Something is wrong! Could not figure out image_id"
    exit 1
fi
instance_id=$(aws ec2 run-instances --image-id ${image_id} $EBS_OPTIONS --key-name $SSH_KEY_NAME --security-groups  remote-working-desktop  --iam-instance-profile Name=$INSTANCE_PROFILE --instance-initiated-shutdown-behavior stop  --instance-type $instance_type | grep '"InstanceId"' | awk -F'"' '{print $4}' |xargs)
if [ "${instance_id}" == "" ]; then
        echo "Something is wrong! Could not create instance"
        exit 1
fi
echo "${instance_id} is the newly generated instance id."
aws ec2 create-tags --resource ${instance_id} --tags Key=Name,Value=${user_name}-desktop
aws ec2 create-tags --resource ${instance_id} --tags Key=Billing,Value=${use}
aws ec2 create-tags --resource ${instance_id} --tags Key=User,Value=${user_name}
aws ec2 create-tags --resource ${instance_id} --tags Key=Owner,Value=${user_name}
aws ec2 create-tags --resource ${instance_id} --tags Key=Janitor,Value='\{"expires":"never"\}'
echo "Now the instance ${user_name}-desktop is up."

public_ip=''
while [ "$public_ip" == "" ]; do
   public_ip=$(aws ec2 describe-instances --instance-id $instance_id | grep PrivateIp | awk -F'"' '{print $4}' | head -n 1 | xargs )
done
echo "Please find information "$(aws ec2 describe-instances --instance-id $instance_id | grep Ip)