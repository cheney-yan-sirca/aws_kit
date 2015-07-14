#!/usr/bin/env python
import json
import cli.app
import commands
import sys


def execute_or_exit(cmd):
    status, out = commands.getstatusoutput(cmd)
    if status != 0:
        print >> sys.stderr, out
        sys.exit(status)
    return out


@cli.app.CommandLineApp
def analyze_vpc_peering(app):
    print "This commands analyze vpc-peering settings between hercules cloud %s and dataset cloud %s" % (
        app.params.hercules_cloud_name, app.params.dataset_cloud_name)
    hercules_vpc_id = \
        json.loads(execute_or_exit('aws ec2 describe-vpcs --filters Name=tag:aws:cloudformation:stack-name,Values="%s*"'
                                   % app.params.hercules_cloud_name))['Vpcs'][0]['VpcId']
    dataset_vpc_id = \
        json.loads(execute_or_exit('aws ec2 describe-vpcs --filters Name=tag:aws:cloudformation:stack-name,Values="%s*"'
                                   % app.params.dataset_cloud_name))['Vpcs'][0]['VpcId']
    hercules_routing_tables = \
        json.loads(execute_or_exit('aws ec2 describe-route-tables --filters Name=vpc-id,Values="%s" '
                                   % hercules_vpc_id))['RouteTables']
    dataset_routing_tables = \
        json.loads(execute_or_exit('aws ec2 describe-route-tables --filters Name=vpc-id,Values="%s" '
                                   % dataset_vpc_id))['RouteTables']
    hercules_subnets = json.loads(execute_or_exit('aws ec2 describe-subnets --filters Name=vpc-id,Values="%s" '
                                                  % hercules_vpc_id))['Subnets']
    dataset_subnets = json.loads(execute_or_exit('aws ec2 describe-subnets --filters Name=vpc-id,Values="%s" '
                                                 % dataset_vpc_id))['Subnets']
    hercules_route_table_list = []
    dataset_route_table_list = []

    for subnets, routing_tables, result_list, stack_name in [
        (hercules_subnets, hercules_routing_tables, hercules_route_table_list, app.params.hercules_stack_name),
        (dataset_subnets, dataset_routing_tables, dataset_route_table_list, app.params.dataset_stack_name)]:
        subnet_info = {}
        for subnet in subnets:
            name_match = False
            logical_id_match = False
            for tag in subnet['Tags']:
                if tag['Key'] == 'aws:cloudformation:stack-name' and tag['Value']. \
                        endswith('-%s' % stack_name):
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

    if len(hercules_route_table_list) > 0 and len(dataset_route_table_list) > 0:
        print "Suggested command:"
        print "aws-vpc-peer --region ap-southeast-2 --request-route-table %s --accept-route-table %s" \
              " %s-vpc %s-vpc" % (",".join(hercules_route_table_list),
                                  ",".join(dataset_route_table_list),
                                  app.params.hercules_cloud_name,
                                  app.params.dataset_cloud_name)
    else:
        print "Failed to analyze the routing table...you may want to check it manually"


analyze_vpc_peering.add_param("-H", "--hercules-cloud-name", help="the hercules cloud name", required=True)
analyze_vpc_peering.add_param("-HS", "--hercules-stack-name", help="the hercules cloud name, default queryapiserver", default="queryapiserver")
analyze_vpc_peering.add_param("-D", "--dataset-cloud-name", help="the hercules cloud name", required=True)
analyze_vpc_peering.add_param("-DS", "--dataset-stack-name", help="the hercules cloud name, default datasetapi", default="datasetapi")

if __name__ == "__main__":
    analyze_vpc_peering.run()
