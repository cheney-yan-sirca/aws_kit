#!/usr/bin/env python
import logging
import os
import re
import sys
from time import sleep

import argparse
import boto
import boto.cloudformation
import boto.ec2
import boto.ec2.autoscale
from boto.ec2.securitygroup import IPPermissions
from boto.exception import EC2ResponseError


class ParseState:
    top_level = 1
    within_host_def = 2


def _is_host_header(line):
    return re.match(r'^Host[ \t]+[a-zA-Z_\-.0-9]+$', line) is not None


def _get_host_name_from_host_line(line):
    return re.split(r'[\t ]+', line)[-1]


def _is_comment(line):
    return re.match(r'^[ \t]*\#.*', line) is not None


def check_file_exists(file):
    if file is not None:
        file = os.path.expanduser(file)
        if os.path.exists(file):
            return file
    return None


def resolve_key_path(key_name, key_file_path_or_dir, logger):
    candidates = []
    if key_file_path_or_dir:
        if key_file_path_or_dir.endswith("%s.pem" % key_name):
            candidates.append(key_file_path_or_dir)
        else:
            if not os.path.isfile(os.path.expanduser(key_file_path_or_dir)):
                candidates.append(os.path.join(key_file_path_or_dir, "%s.pem" % key_name))

    if os.path.join(os.path.expanduser('~'), "%s.pem" % key_name):
        candidates.append(key_file_path_or_dir)

    for candidate in candidates:
        path = check_file_exists(candidate)
        if path:
            os.chmod(path, 0600)
        return path
    logger.error("Cannot find key %s under %s, exit.", key_name, candidates)
    exit(1)


def _generate_ssh_config_lines(hopper_name, hopper_ip, hopper_key, instances, ssh_config_path):
    result = []

    result.append("Host %s" % hopper_name)
    result.append(
        "\tIdentityFile %s" % hopper_key)
    result.append("\tHostName %s" % hopper_ip)
    result.append("\tUser ec2-user")
    result.append("\tConnectTimeout 3")
    result.append("\tStrictHostKeyChecking no")

    for instance_name, instance_info in instances.items():
        result.append("Host %s" % instance_name)
        result.append(
            "\tIdentityFile %s" % instance_info[1])
        result.append("\tHostName %s" % instance_info[0])
        result.append("\tUser ec2-user")
        result.append("\tStrictHostKeyChecking no")
        result.append("\tConnectTimeout 3")
        result.append(
            "\tProxyCommand ssh -F '{0}' ec2-user@{1} nc %h %p ".format(ssh_config_path, hopper_name))

    return result


def get_env(env, default):
    if env in os.environ:
        return os.environ[env]
    else:
        return default


def get_stdout_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


def find_sshbox_stack(cloud_name, region, logger):
    wanted_status = ['UPDATE_COMPLETE', 'ROLLBACK_COMPLETE', 'CREATE_COMPLETE', 'UPDATE_ROLLBACK_COMPLETE']
    logger.info("Connecting to region %s", region)
    stack_connection = boto.cloudformation.connect_to_region(region)
    next_token = None
    while True:
        stacks = stack_connection.list_stacks(wanted_status, next_token)
        next_token = stacks.next_token
        for stack in stacks:
            if stack.stack_name == '%s-sshbox' % cloud_name:
                return stack
        if next_token is not None:
            continue
        else:
            return None


def find_localhost_public_ip():
    from urllib2 import urlopen
    return urlopen('http://ip.42.pl/raw').read()


def prepare_all_instances(cloud_name, region, ssh_key_path, logger):
    results = {}
    logger.info("Finding ASGs for cloud %s", cloud_name)
    full_asg_name_pattern = re.compile('%s-.+-[^-]+-[^-]+' % cloud_name)

    found_instances = []
    autoscale_conn = boto.ec2.autoscale.connect_to_region(region)
    next_token = None
    while True:
        asgs = autoscale_conn.get_all_groups(next_token=next_token)
        next_token = asgs.next_token
        for asg in asgs:
            if full_asg_name_pattern.match(asg.name) and not asg.name.startswith('%s-sshbox' % cloud_name):
                found_instances = found_instances + [
                    instance.instance_id for instance in asg.instances
                    ]
        if next_token is not None:
            continue
        else:
            break
    logger.info("Found instances [%s]", ','.join(found_instances))
    if found_instances:
        ec2_conn = boto.ec2.connect_to_region(region)
        instances = ec2_conn.get_only_instances(instance_ids=found_instances)
        for instance in instances:
            key = '%s-%s' % (instance.tags.get('Name', 'NA'), instance.id)
            value = (instance.private_ip_address, resolve_key_path(instance.key_name, ssh_key_path, logger))
            results[key] = value
    return results


def prepare_ssh_box(asg_name, region, ssh_key_path, logger, action='setup'):
    full_asg_name_pattern = re.compile('%s-[^-]+-[^-]+' % asg_name)
    logger.info("Finding ASG of %s", asg_name)
    autoscale_conn = boto.ec2.autoscale.connect_to_region(region)
    found_asg = None
    while True:
        asgs = autoscale_conn.get_all_groups()
        next_token = asgs.next_token
        for asg in asgs:
            if asg.name == asg_name or full_asg_name_pattern.match(asg.name):
                found_asg = asg
                break
        if next_token is not None:
            continue
        else:
            break

    if not found_asg:
        logger.error("Could not find asg with name like %s", asg_name)
        exit(1)

    ec2_conn = boto.ec2.connect_to_region(region)

    if action == 'setup':
        if found_asg.desired_capacity == 0:
            logger.warn("ASG now configured to be at capacity 0. Updating to 1...")
            if found_asg.min_size == 0:
                found_asg.min_size = 1
            if found_asg.max_size == 0:
                found_asg.max_size = 1
            found_asg.desired_capacity = 1
            found_asg.update()

        logger.info("Waiting for the only instance in ASG %s that is active", asg_name)
        found_instance = None
        while True:
            found_asg = autoscale_conn.get_all_groups(names=[found_asg.name])[0]
            all_instances = list(found_asg.instances)
            if len(all_instances) == 0:
                logger.info('.')
                sleep(10)
                continue

            if all_instances[0].lifecycle_state != 'InService' or all_instances[0].health_status != "Healthy":
                sleep(10)
                continue
            found_instance = all_instances[0]
            break

        logger.info("Checking the instance info.")
        instance = ec2_conn.get_all_instances(instance_ids=[found_instance.instance_id])
        hop_ip_address = instance[0].instances[0].ip_address
        hop_key_name = instance[0].instances[0].key_name
        logger.info("Checking if this host is in security group rule")
        found_security_group = None
        for group in instance[0].instances[0].groups:
            if group.name.startswith(asg_name):
                found_security_group = group
                break
        if found_security_group is None:
            logger.error("Cannot find security group for asg %s. This should not happen." % found_asg.name)
            exit(1)
        logger.info("Finding public ip of this host:")
        public_ip = find_localhost_public_ip()
        logger.info("Public ip of this host: %s", public_ip)

        found_security_group = ec2_conn.get_all_security_groups(group_ids=[found_security_group.id])[0]
        ingress_rule = None
        for rule in found_security_group.rules:
            if 22 >= int(rule.from_port) and 22 <= int(rule.to_port):
                for grant in rule.grants:
                    if "%s/32" % public_ip in grant.cidr_ip:
                        ingress_rule = rule
                        break
        try:
            if ingress_rule is None:
                found_security_group.authorize(ip_protocol='tcp',
                                               from_port=22,
                                               to_port=22,
                                               cidr_ip="%s/32" % public_ip)
            logger.info("Public ip of this host: %s allowed in the security group.", public_ip)
        except EC2ResponseError as e:
            if e.error_code != 'InvalidPermission.Duplicate':
                raise
            logger.warn("Seems we could not find the rule we created, but the existing rule has allowed this host.")

        return asg_name, hop_ip_address, resolve_key_path(hop_key_name, ssh_key_path, logger)
    else:  # teardown
        logger.info("Resizing sshbox asg size to 0")
        if found_asg.desired_capacity != 0:
            logger.warn("ASG now configured to be at capacity > 0. Updating to 0...")
            found_asg.min_size = 0
            found_asg.max_size = 0
            found_asg.desired_capacity = 0
            found_asg.update()
        if len(found_asg.instances) > 0:
            instances = ec2_conn.get_all_instances(instance_ids=[found_asg.instances[0].instance_id])
            public_ip = find_localhost_public_ip()
            for group in instances[0].instances[0].groups:
                if group.name.startswith(asg_name):
                    found_security_group = ec2_conn.get_all_security_groups(group_ids=[group.id])[0]
                    for rule in found_security_group.rules:
                        if 22 >= int(rule.from_port) and 22 <= int(rule.to_port):
                            for grant in rule.grants:
                                if "%s/32" % public_ip in grant.cidr_ip:
                                    try:
                                        found_security_group.revoke(ip_protocol='tcp',
                                                                    from_port=22,
                                                                    to_port=22,
                                                                    cidr_ip="%s/32" % public_ip)
                                        logger.warn("Updating security group, removed %s", public_ip)
                                    finally:
                                        pass


def write_ssh_file(ssh_config_path, cloud_name, new_lines, logger):
    if not os.path.isfile(ssh_config_path):
        os.fdopen(os.open(ssh_config_path, os.O_WRONLY | os.O_CREAT, 0600), 'w').close()
    ssh_config_lines = []
    with open(ssh_config_path, 'r') as content_file:
        ssh_config = content_file.read()
    ssh_config = ssh_config.splitlines()
    parse_state = ParseState.top_level
    current_host_name = None
    current_host_lines = []
    while len(ssh_config) > 0:
        cur_line = ssh_config.pop(0)
        # now we are to preserve all the comments. They could be
        # something useful for other programs
        if (parse_state == ParseState.top_level):
            if (_is_comment(cur_line)):
                ssh_config_lines.append(cur_line)
                continue
            if not _is_host_header(cur_line):
                ssh_config_lines.append(cur_line)
            else:
                current_host_name = _get_host_name_from_host_line(cur_line)
                parse_state = ParseState.within_host_def
                current_host_lines = [cur_line]
        else:  # within a host def
            if (not _is_host_header(cur_line)):
                current_host_lines.append(cur_line)
            else:
                logger.debug("End of %s definition", current_host_name)
                if not current_host_name.startswith("%s-" % cloud_name):
                    ssh_config_lines = ssh_config_lines + current_host_lines
                current_host_name = _get_host_name_from_host_line(cur_line)
                current_host_lines = [cur_line]
    if len(current_host_lines) > 0:
        if not current_host_name.startswith("%s-" % cloud_name):
            ssh_config_lines = ssh_config_lines + current_host_lines

    ssh_config_lines = ssh_config_lines + new_lines
    text_file = open(ssh_config_path, "w")
    text_file.write("\n".join(ssh_config_lines))
    text_file.close()
    logger.info("Successfully updated into %s" % ssh_config_path)


def collect_and_generate_ssh_lines(cloud_name, region, ssh_key_file_or_dir, ssh_config_path, logger, cmd):
    known_regions = ["ap-southeast-2", "us-west-2", "us-east-1", "ap-northeast-1", "sa-east-1",
                     "ap-southeast-1", "us-west-1", "eu-west-1"]  # keep the sequence.
    stack = None
    if region is not None:
        stack = find_sshbox_stack(cloud_name, region, logger)
    else:
        logger.info("No region provided, finding the correct region... ")
        for region_candidate in known_regions:
            stack = find_sshbox_stack(cloud_name, region_candidate, logger)
            if stack:
                region = region_candidate
                break
    if not stack:
        logger.error("Cannot find in any region/specified region that the stack '%s-sshbox' exists.", cloud_name)
        exit(1)
    else:
        logger.info("Find stack %s-sshbox in region %s.", cloud_name, region)

    hopper_info = prepare_ssh_box(stack.stack_name, region, ssh_key_file_or_dir, logger, cmd)
    if cmd == 'setup':
        instances = prepare_all_instances(cloud_name, region, ssh_key_file_or_dir, logger)
        return _generate_ssh_config_lines(hopper_info[0], hopper_info[1], hopper_info[2], instances, ssh_config_path)
    else:
        return []


def update_ssh_config(cloud_name, region, ssh_config_file, ssh_key_file_or_dir, logger, cmd):
    ssh_config_file = os.path.expanduser(ssh_config_file)
    new_lines = collect_and_generate_ssh_lines(cloud_name, region, ssh_key_file_or_dir, ssh_config_file, logger, cmd)
    logger.info("Writting into ssh config file: ---start---\n%s\n----end---", "\n".join(new_lines))
    write_ssh_file(ssh_config_file, cloud_name, new_lines, logger)


def main():
    logger = get_stdout_logger()
    parser = argparse.ArgumentParser(
        "Collect cloud instances and execute a command on all the instances within a stack. This script"
        " looks into sshbox stack to seek .")
    parser.add_argument("-F", dest="config_file", default='~/.ssh/config',
                        help='Specifies an alternative per-user configuration file to update the host name into.  '
                             'By default this writes into ~/.ssh/config.')
    parser.add_argument("-K", dest="ssh_key_file_or_dir",
                        help='If it looks like *.pem, then this will be the key file be used to access all the instances.'
                             'Else, it is the path of where to find the correct key from. Example, ~/.ssh. Then the script'
                             'will try to use the ~/.ssh/key_name.pem as the private key. If the file does not exist,'
                             'then the script fails.', default=get_env('SSH_KEY_FILE', '~/.ssh/'))
    parser.add_argument('--verbose', dest='verbose', help='Print verbose information.', action='store_true',
                        default=False)
    parser.add_argument('--region', dest='region', help='If you know the region, please specify to fastern process.',
                        default=None)
    parser.add_argument('--cmd', dest='cmd', help='Setup or shutdown the sshbox asg.', default="setup",
                        choices=['setup', 'teardown'])
    parser.set_defaults(quiet=False)

    parser.add_argument('cloud_name', type=str, help='The name of cloud to collect ssh info from.')

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)
    update_ssh_config(args.cloud_name, args.region, args.config_file, args.ssh_key_file_or_dir, logger, args.cmd)


if __name__ == '__main__':
    sys.exit(main())
