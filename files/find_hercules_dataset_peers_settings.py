#!/usr/bin/env python
import copy
import datetime
import json
import os
import subprocess
import tempfile
from time import sleep
import cli.app
import commands
import sys
from requests import Request
import requests


def execute_cmd(cmd, exit_on_failure=True):
    status, out = commands.getstatusoutput(cmd)
    if status != 0 and exit_on_failure:
        print >> sys.stderr, out
        sys.exit(status)
    return out


@cli.app.CommandLineApp
def analyze_vpc_peering(app):
    print "This commands analyze vpc-peering settings between hercules cloud %s and dataset cloud %s" % (
        app.params.hercules_cloud_name, app.params.dataset_cloud_name)
    hercules_vpc_id = \
        json.loads(
            execute_cmd('aws ec2 describe-vpcs --filters Name=tag:aws:cloudformation:stack-name,Values="%s-%s"'
                        % (app.params.hercules_cloud_name, 'vpc')))['Vpcs'][0]['VpcId']
    dataset_vpc_id = \
        json.loads(
            execute_cmd('aws ec2 describe-vpcs --filters Name=tag:aws:cloudformation:stack-name,Values="%s-%s"'
                        % (app.params.dataset_cloud_name, 'vpc')))['Vpcs'][0]['VpcId']
    # print hercules_vpc_id, dataset_vpc_id
    hercules_routing_tables = \
        json.loads(execute_cmd('aws ec2 describe-route-tables --filters Name=vpc-id,Values="%s" '
                               % hercules_vpc_id))['RouteTables']
    dataset_routing_tables = \
        json.loads(execute_cmd('aws ec2 describe-route-tables --filters Name=vpc-id,Values="%s" '
                               % dataset_vpc_id))['RouteTables']
    hercules_subnets = json.loads(execute_cmd('aws ec2 describe-subnets --filters Name=vpc-id,Values="%s" '
                                              % hercules_vpc_id))['Subnets']
    dataset_subnets = json.loads(execute_cmd('aws ec2 describe-subnets --filters Name=vpc-id,Values="%s" '
                                             % dataset_vpc_id))['Subnets']

    all_load_balancers = json.loads(execute_cmd('aws elb describe-load-balancers '
                                                ))['LoadBalancerDescriptions']

    hercules_route_table_list = []
    dataset_route_table_list = []

    # print "Hercules subnets and Dataset subnets:"
    # print hercules_subnets, dataset_subnets

    for subnets, routing_tables, result_list, stack_name, cloud_name in [
        (hercules_subnets, hercules_routing_tables, hercules_route_table_list, app.params.hercules_stack_name,
         app.params.hercules_cloud_name),
        (dataset_subnets, dataset_routing_tables, dataset_route_table_list, app.params.dataset_stack_name,
         app.params.dataset_cloud_name)]:
        subnet_info = {}
        for subnet in subnets:
            name_match = False
            logical_id_match = False
            for tag in subnet['Tags']:
                # print tag['Value']
                if tag['Key'] == 'aws:cloudformation:stack-name' and tag['Value'] \
                        == ('%s-%s' % (cloud_name, stack_name)):
                    name_match = True
            if name_match:
                for tag in subnet['Tags']:
                    if tag['Key'] == 'aws:cloudformation:logical-id' and 'elbAZ' in tag['Value']:
                        logical_id_match = True
            if logical_id_match:
                subnet_info[subnet['SubnetId']] = subnet['CidrBlock']
        for route_table in routing_tables:
            for association in route_table['Associations']:
                if association.get('SubnetId', "NONE") in subnet_info:
                    result_list.append(association['RouteTableId'])
    # print hercules_route_table_list, dataset_route_table_list
    if len(hercules_route_table_list) > 0 and len(dataset_route_table_list) > 0:
        print "Suggested VPC peering command: =======>"
        print "aws-vpc-peer --region ap-southeast-2 --request-route-table %s --accept-route-table %s" \
              " %s-vpc %s-vpc" % (",".join(hercules_route_table_list),
                                  ",".join(dataset_route_table_list),
                                  app.params.hercules_cloud_name,
                                  app.params.dataset_cloud_name)
    else:
        print "Failed to analyze the routing table...you may want to check it manually"


    # collecting the info in the target cloud

    if "SSH_KEY_FILE" in os.environ and "AWS_CONFIG_FILE" in os.environ and "not found" not in execute_cmd(
            'which cloud_ssh_util', exit_on_failure=False):
        now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%sZ")
        dataset_load_balancer_dns = None
        hercules_load_balancer_dns = None
        for load_balancer in all_load_balancers:
            if load_balancer.get('VPCId') == dataset_vpc_id:
                dataset_load_balancer_dns = load_balancer['DNSName']
            elif load_balancer.get('VPCId') == hercules_vpc_id and "Public" in load_balancer.get('DNSName'):
                hercules_load_balancer_dns = load_balancer['DNSName']

        if not dataset_load_balancer_dns or not hercules_load_balancer_dns:
            print "Cannot find load balancer DNSName for cloud %s and stack %s" % (app.params.dataset_cloud_name,
                                                                                   app.params.dataset_stack_name)
        else:
            ssh_config_file = tempfile.NamedTemporaryFile()
            ssh_config_file.close()
            ssh_config_file_name = ssh_config_file.name
            collection_file = "%s_collection.json" % ssh_config_file.name
            collection_file_content = ""
            known_collections = {}
            processed_collections = {}
            processed_datasets = {}
            collection_content = execute_cmd(
                "BUCKET=$(aws s3 ls | grep metadata | awk '{print $NF}');aws s3 ls --recursive $BUCKET | awk '{print $NF}'")
            for line in collection_content.splitlines():
                tokens = line.split('/')

                if len(tokens) > 2 and len(tokens[0]) > 0 and len(tokens[1]) > 0 and tokens[2].endswith('.json'):
                    known_collections[tokens[1]] = tokens[0]
            execute_cmd('cloud_ssh_util -F %s %s ' % (ssh_config_file_name, app.params.dataset_cloud_name))
            # set up tunnel
            port_settings = "12391:localhost:80"
            tunnel_cmd = 'ssh -N -n -F %s -L %s %s-%s1' % (ssh_config_file_name, port_settings,
                                                           app.params.dataset_cloud_name,
                                                           app.params.dataset_stack_name)
            subprocess.Popen(tunnel_cmd, shell=True, close_fds=True)
            sleep(2)
            for dataset, collection in known_collections.items():
                url = 'http://localhost:12391/%s/%s/v1/meta' % (collection, dataset)
                # print url
                try:
                    r = requests.get(url)
                    if r.status_code == 200 and r.json():
                        dataset_meta = {}
                        dataset_meta['uri'] = "http://%s/%s/%s/v1" % (dataset_load_balancer_dns, collection, dataset)
                        dataset_meta["collections"] = [collection]
                        processed_datasets[dataset] = json.dumps(dataset_meta, indent=2)
                        processed_collections[dataset] = collection
                except:
                    pass
            if len(processed_collections) != 0:
                collection_content = []
                dataset_template = {
                    "id": processed_collections.values()[0],
                    "displayName": "",
                    "description": "",
                    "longDescription": "",
                    "lastUpdated": now
                }
                print "********Retrieve the file from https://github.com/sirca/datasets/blob/" \
                      "develop/collections/%s.json and update into your own file"\
                      % collection
                collection_content=dataset_template
                #
                # for collection in set(processed_collections.values()):
                #     cp = copy.deepcopy(dataset_template)
                #     cp['id'] = collection
                #     cp['displayName'] = collection
                #     cp['description'] = collection
                #     cp['longDescription'] = collection
                #     collection_content.append(cp)
                collection_file_content = json.dumps(collection_content, indent=2)
                

            # write to files
            print "Suggested registration command: (the files are generated for you as follows)============>"

            dataset_file_list = []
            for dataset, content in processed_datasets.items():
                file_name = "%s_dataset_%s.json" % (ssh_config_file.name, dataset)

                with open(file_name, 'w') as f:
                    f.write(content)
                dataset_file_list.append(file_name)
                # print "csload --owner %s --type dataset --domain dash-registry-dev %s" % (
                # app.params.hercules_cloud_name,
                # file_name)
                # print "OR"
                print 'curl -i -k -H "Authorization: bearer $TOKEN" -X POST -H "Content-Type: application/json" ' \
                      ' -d @%s https://%s/v1/discovery ' % (file_name, hercules_load_balancer_dns)

            with open(collection_file, 'w') as f:
                f.write(collection_file_content)
            # print "csload --owner %s --type collection --domain dash-registry-dev %s" % (app.params.hercules_cloud_name,
            #                                                                              collection_file)
            # print "OR"
            print 'curl -i -k -H "Authorization: bearer $TOKEN" -X POST -H "Content-Type: application/json" ' \
                  ' -d @%s https://%s/v1/collections ' % (collection_file, hercules_load_balancer_dns)

            print "-------------edit and validate the above json files via: ---"
            print "http://metadata-tool.sirca.org.au.s3-website-ap-southeast-2.amazonaws.com/#editor-screen "
            execute_cmd("for x in $(ps -ef | grep '%s' | grep -v grep | awk '{print $2}'); do kill -9 $x; done" % \
                        (port_settings))


    else:
        for load_balancer in all_load_balancers:
            if load_balancer.get('VPCId') == dataset_vpc_id:
                print "Suggested uri in the meta file: ============>"
                print '"uri":"http://%s/<collection/<dataset>/v1"' % load_balancer['DNSName']
        print "Suggested csload command:============>"
        print "csload --owner %s --type dataset --domain dash-registry-dev dataset.json" % app.params.hercules_cloud_name
        print "csload --owner %s --type collection --domain dash-registry-dev collection.json" % app.params.hercules_cloud_name


analyze_vpc_peering.add_param("-H", "--hercules-cloud-name", help="the hercules cloud name", required=True)
analyze_vpc_peering.add_param("-HS", "--hercules-stack-name",
                              help="the hercules stack name to peer from, default queryapiserver",
                              default="queryapiserver")
analyze_vpc_peering.add_param("-D", "--dataset-cloud-name", help="the hercules cloud name", required=True)
analyze_vpc_peering.add_param("-DS", "--dataset-stack-name",
                              help="the hercules stack name to peer to, default datasetapi", default="datasetapi")

if __name__ == "__main__":
    analyze_vpc_peering.run()
