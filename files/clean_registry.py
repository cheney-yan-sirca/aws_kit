#!/usr/bin/env python
from time import sleep

import boto
from boto.cloudsearch2.domain import Domain
from boto.cloudsearchdomain.layer1 import CloudSearchDomainConnection

import json

import cli.app
import sys

def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")

def delete_doc_in_cloudsearch(doc_ids, cloudsearch_domain_name, validate=True, region='ap-southeast-2'):
    """

    :param doc_ids: the doc id array
    :param cloudsearch_domain_name: the domain name

    !!! This method is in-efficient for validating.
    """

    conn = boto.cloudsearch2.connect_to_region(region)
    domain = conn.describe_domains([cloudsearch_domain_name]) \
        ['DescribeDomainsResponse']['DescribeDomainsResult']['DomainStatusList']
    doc_service = CloudSearchDomainConnection(host=domain[0]['DocService']['Endpoint'],
                                              region=region)
    if len(doc_ids) > 0:
        batch = []
        for id in doc_ids:
            batch.append({
                "id": str(id),
                "type": "delete"
            })
        doc_service.upload_documents(json.dumps(batch), 'application/json')

    if validate:
        # we need some time for the cloudsearch to apply the deletion.
        MAX_RETRIES = 100
        SLEEP_GAP = 10
        for id in doc_ids:
            retry = 0
            while retry < MAX_RETRIES:
                result = doc_service.search(query="(term field=_id '%s')" % id, query_parser='structured')
                if (result['hits']['found'] == 0):
                    break
                retry += 1
                sleep(SLEEP_GAP)
            if retry >= MAX_RETRIES:
                raise ValueError(
                    "Intended to delete cloudsearch documents with id %s, but it still exists after deletion. "
                    "Culprit document: %s" % (doc_ids, id))


def query_by_structured(cs_comain, search_term, limit=10, return_fields=['_score'], region='ap-southeast-2'):
    cs_conn = boto.cloudsearch2.connect_to_region(region)
    desc_res = cs_conn.describe_domains([cs_comain])
    desc = desc_res['DescribeDomainsResponse']['DescribeDomainsResult']['DomainStatusList']
    _domain = Domain(cs_conn, desc[0])
    search_conn = boto.cloudsearch2.search.SearchConnection(_domain)
    search_q = search_conn.build_query(
        q=search_term,
        parser='structured',
        return_fields=return_fields,
        start=0,
        size=(limit if limit else 10)
    )
    results = search_conn.get_all_hits(search_q)  # Returns a generator
    return list(results)


@cli.app.CommandLineApp
def clean_registry(app):
    if clean_registry.params.dataset_cloud_name:
        id_list = query_by_structured(app.params.cs_domain, "(term field=_id '%s_%s')" % (
            app.params.hercules_cloud_name,
            app.params.dataset_cloud_name
        ), limit=10)
    else:
        id_list = query_by_structured(app.params.cs_domain, '(matchall)', limit=10000)
        id_list = [x for x in id_list if x['id'].startswith('%s_' % app.params.hercules_cloud_name)]
    matched_ids = [x['id'] for x in id_list]
    if len(matched_ids)==0 :
        print "No record associated is found!"
    else:
        print "Registry items found: ", ",".join(matched_ids)
        if query_yes_no("Do you want to proceed to Delete?"):
            print "Deleting..."
            delete_doc_in_cloudsearch(matched_ids, app.params.cs_domain)


clean_registry.add_param("-c", "--cs_domain", help="cloudsearch-domain", default='dash-registry-dev-v2')
clean_registry.add_param("-H", "--hercules-cloud-name", help="hercules cloud name", required=True)
clean_registry.add_param("-d", "--dataset-cloud-name", help="dataset cloud name, default means ALL", default=None)

if __name__ == "__main__":
    clean_registry.run()
