#!/usr/bin/python

'''
This project is made to provide the following functions:
 1. Run a report on all reconciled configlets
 2. create a configlet based on reconcile for each device with date and timestamp
 
This script utilizes cvprac, for information on setup see:
https://github.com/aristanetworks/cvprac

'''

import cvprac.cvp_client
import json
import sys
from ConfigParser import SafeConfigParser
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

version = '1.1'
cfg_file = '/etc/auto-reconcile.cfg'


def get_credentials(config_file):
    def remove_quotes(item):
        item = item.replace("'",'')
        item = item.replace('"','')
        return item

    parser = SafeConfigParser()
    parser.read(config_file)
    user = remove_quotes( parser.get('authentication', 'username') )
    pwd = remove_quotes( parser.get('authentication', 'password') )
    cvp_nodes = remove_quotes( parser.get('cvp_instances', 'nodes') ).split(',')
    return (user, pwd, cvp_nodes)


def get_devices(client):
    devices = []
    containers = client.api.get_containers()
    container_list = containers['data']
    number_of_containers = containers['total']

    for container in container_list:
        container_name = container['name']
        _devices = client.api.get_devices_in_container(container_name)
        devices.extend(_devices)

    return devices


def validate_and_compare_configlets(client, device_id, configlet_keys):
    client.log.debug('validate_and_compare_configlets: configlet_keys: %s ' % (configlet_keys))

    body = {'netElementId': device_id, 'configIdList': configlet_keys, 'pageType': 'string'}
    data = client.post('/provisioning/v2/validateAndCompareConfiglets.do', 
                        data=body, timeout=client.api.request_timeout)

    return data


def update_add_reconcile(client, name, config, key, device_id):
    client.log.debug('update_add_reconcile: name: %s config: %s key: %s' % (name, config, key))

    body = {'name': name, 'config': config, 'key': key, 'reconciled': True}
    data = client.post('/provisioning/updateReconcileConfiglet.do?netElementId=%s' % device_id,
                        data=body, timeout=client.api.request_timeout)

    return data


def cancel_pending_tasks(client):
    tasks = client.api.get_tasks_by_status('Pending')
    for task in tasks:
        if 'auto-reconcile' in task['description']:
            client.api.cancel_task(task['workOrderId'])

    return


def reconcile(client, device):
    configlet_keys = []
    reconcile_applied = False

    try:
        reconcile = client.api.get_configlet_by_name('RECONCILE_%s' % device['ipAddress'])
    except:
        reconcile = {'name': None}
    
    device_id = device['systemMacAddress']
    print 'Gathering configlets for: %s' % device['fqdn']
    configlets = client.api.get_configlets_by_device_id(device_id)
    for configlet in configlets:
        if reconcile['name'] == configlet['name']:
            print 'reconcile applied'
            reconcile_applied = True
            continue
        else:
            configlet_keys.append(configlet['key'])

    result = validate_and_compare_configlets(client, device_id, configlet_keys)
    
    if result['reconcile'] > 0:
        print 'Begin reconciling process for: %s' % device['fqdn']
        configlet_name = result['reconciledConfig']['name']
        configlet_config = result['reconciledConfig']['config']

        if result['reconciledConfig']['key'] == None:
            reconcile_key = client.api.add_configlet(configlet_name, configlet_config)   
        else:
            reconcile_key = result['reconciledConfig']['key']
        
        print 'Updating reconcile configlet for: %s' % device['fqdn']
        reconcile_result = update_add_reconcile(client, configlet_name,
                                                configlet_config, reconcile_key, device_id)
        
        if not reconcile_applied:
            print 'Reconcile configlet not applied...applying to %s' % device['fqdn']
            apply_configlets = [ {'name': configlet_name, 'key': reconcile_key} ]
            client.api.apply_configlets_to_device('auto-reconcile.py', device,
                                                   apply_configlets, True)

    return




def main():
    user, pwd, cvp_nodes = get_credentials(cfg_file)
    cvp_client = cvprac.cvp_client.CvpClient()
    cvp_client.connect(cvp_nodes, user, pwd)

    failed_devices = []
    devices = get_devices(cvp_client)
    print 'Starting compliance checks'
    for device in devices:
        device_id = device['systemMacAddress']
        device_type = device['type']
        device_name = device['fqdn'].split('.')[0]
        result = cvp_client.api.check_compliance(device_id, device_type)
        
        if result['complianceCode'] != '0000':
            print 'Compliance check did not pass for: %s' % device['fqdn']
            print 'Beginning reconcile...'
            failed_devices.append(device)
            reconcile(cvp_client, device)
    
    print 'Cancelling pending tasks generated by auto-reconcile.py'
    cancel_pending_tasks(cvp_client)
    
    print 'Running compliance check for all failed devices'
    for device in failed_devices:
        device_id = device['systemMacAddress']
        device_type = device['type']
        print 'Running compliance check again on: %s' % device['fqdn']
        cvp_client.api.check_compliance(device_id, device_type)

    print ''
    print 'Auto-reconcile Complete'
    
    return


if __name__ == '__main__':
    main()