# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

#
# This script checks WiFi/Bluetooth peer devices in the lab and creates
# a google spreadsheet for the one which are down.
# The google sheet is displayed at go/wifi-down
#
# This is used by ACS lab to detect down devices
#
# This script get data from 3 sources
# 1) data from dhcp file /usr/local/google/home/<user>/chromiumos/
#                \chromeos-admin/puppet/modules/lab/files/dhcp-server/dhcpd.conf
# 2) Swarming data of all bots with label-wificell
# 3) data from g/cros_conn_device_lifecycle
#
# Once data from these three sources are combined, the script pings the devices
# that we are interested in. Any unreachable devices is displayed in the dashboard
# for the lab team to rectify.
#
# Data from all sources is collected device data which of following format
# At each stage 'ignore' flag in send to False if the device meet the criteria to be monitored
# Any host/peer with ignore flag set is not displayed in dashboard
#
# 'chromeos15-row8-rack2-host2': {'dhcp': True,
#                                 'doc': True,
#                                 'doc_data': {'board': 'gnawty',
#                                              'btpeers': [],
#                                              'model': 'gnawty',
#                                              'pool': 'wificell_perbuild'},
#                                 'ignore': False,
#                                 'ignore_reason' : ''
#                                 'peers': {'chromeos15-row8-rack2-host2-pcap': {'dhcp': True,
#                                                                                'doc': False,
#                                                                                'ignore': True,
#                                                                                'ssh_status': False,
#                                                                                'swarming': True},
#                                           'chromeos15-row8-rack2-host2-router': {'dhcp': True,
#                                                                                  'doc': False,
#                                                                                  'ignore': True,
#                                                                                  'ssh_status': False,
#                                                                                  'swarming': True}},
#                                 'ssh_status': False,
#                                 'swarming': True,
#                                 'swarming_data': {'bluetooth_label': True,
#                                                   'board': 'gnawty',
#                                                   'bt_label': False,
#                                                   'bt_peers': [],
#                                                   'conductive': True,
#                                                   'deleted': False,
#                                                   'host': 'chromeos15-row8-rack2-host2',
#                                                   'hw_phase': 'PHASE_PVT',
#                                                   'is_dead': False,
#                                                   'missing': False,
#                                                   'model': 'gnawty',
#                                                   'pool': 'wificell_perbuild',
#                                                   'servo': False,
#                                                   'wifichip': 'wireless_intel'}},
#
#
#  Note 1: Only devices is chromeos15- is checked
#  Note 2 : Currently the following peer devices are considered PCAP,ROUTER,BTPEER1-4, SERVO, ATTENUATOR
#  Note 3 : Standalone RPMS in chromeos3 are added as special cases
#  Note 4: For debugging this script, use debug_main and store intermediate results in files.
#
#
#TODO
# debug the hang
# servo already there
# rpm already there?
# attentuator already there
# separate doc issues to different sheet
# send mail

import csv
import datetime
import gspread
import json
import logging
import os
import pprint
import subprocess
import sys
import time
import queue

from oauth2client.service_account import ServiceAccountCredentials
from credentials import json_keyfile
from multiprocessing import Process
from multiprocessing import Queue

import get_wificell_data
import get_wifisheet_data
import get_dhcp_data
import rpm_list

# Change logging level to DEBUG for more logs
#logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

DASHBOARD_REFRESH_INTERVAL = 1000  # Time to wait between dashboard refreshes in seconds
CONNECTIVITY_RETEST_INTERVAL = 180  # Time to wait before rechecking connectivity to down devices in seconds
HOST_UP = 'UP'
HOST_DOWN = 'DOWN'
HOST_NO_SSH = 'Online w/o SSH Con'

PING_COUNT = 2
SPREADSHEET_ALL = 'WiFi Devices DOWN'
WORKSHEET1 = 'LAB'
WORKSHEET2 = 'Documentation'

# Mapping integers to host status strings.
HOST_STATUS = {0: HOST_UP, 1: HOST_DOWN, 3: HOST_NO_SSH}

# Ignore devices in these pools
POOLS_TO_IGNORE = ['cross_device_multi_cb']

# Names of bluetooth peers
BT_PEERS = ['btpeer1', 'btpeer2', 'btpeer3', 'btpeer4']

# Name of wifi peer devices
WIFI_PEERS = ['router', 'pcap']

#Pools with attentuator
ATTENUATOR_POOLS = ['groamer', 'groamer_two', 'bt_groamer']


def _pretty_print(d, msg=''):
    print('------------------------------------------------------------')
    if msg != '':
        print('======   %s =========' % msg)
    if type(d) == dict:
        pp = pprint.PrettyPrinter(indent=1)
        pp.pprint(d)
        print('length is %s' % len(d))
    elif type(d) == list:
        for i in d:
            print(i)
        print('length is %s' % len(d))
    else:
        print(d)
    print('------------------------------------------------------------')


def _parse_doc_model_name(m):
    """ parse Model name in the go/cros-conn-lifecycle sheet so it can be compared with swarming model name

        It can be 'Mordin (Barla)' which be be parsed as [mordin, barla]
        veyron_/auron_ prefixes should be removed
        There can be WIP in the name which means that is should be ignored
    """
    result = []
    m = m.lower()
    if '[wip]' in m:
        result.append('[wip]')
        m = m.strip('[wip]')
        logging.debug('WIP device found')
    if '(' in m:
        for i in m.split('('):
            i = i.strip().replace(')', '').lower()
            result.append(i)
    else:
        result.append(m.strip().lower())
    logging.debug('Returning %s for %s', result, m)
    return result


def _make_peers(h, l):
    if type(l) == list:
        res = []
        for p in l:
            res.append(h + '-' + p)
        return res
    else:
        return h + '-' + p


def getHostStatus(q, host):
    """ Ping the host and check if it is ssh-able"""
    try:
        logging.debug('Checking status of %s', host)
        # Grab the ping exit code.
        host_status_code = subprocess.call(['ping', '-c2', host])
        # if the device is pingable, we check if port 22 is open to accept ssh connection.
        if host_status_code == 0:
            try:
                nc_output_code = subprocess.call(
                    ['nc', '-zv', '-w3', host, '22'])
            except:
                logging.debug('netcat failed: %s', host)
            if nc_output_code != 0:
                host_status_code = 3
        ret_status = HOST_STATUS[host_status_code]
    except Exception as e:
        logging.error('!!!!!!!! Exception %s while checking %s', str(e), host)
        ret_status = HOST_DOWN
    finally:
        logging.debug('Host %s returning status %s', host, ret_status)
        q.put((host, ret_status))


def get_rpm_list():
    """ Read the list of rpms """
    return rpm_list.rpm_list


def update_rpm_data(device_data, rpm_list):
    """ Update list of rpm into device data """
    for h in rpm_list:
        device_data[h] = {
            'ignore': False,
            'ignore_reason': 'RPM not ignored',
            'dhcp': True,  # Found in dhcp file
            'ssh_status': False,
            'swarming': True,  # RPM wont be in swarming
            'doc': True,  # RPM wont be in doc
            'pool': 'RPM',  # Add a false pool
            'peers': {},
            'chromeos': False
        }
        logging.debug('dhcp other device added %s %s', h, device_data[h])


def update_dhcp_data(device_data, hosts, peer_devices, other_devices):
    """
    Update dhcp data into device_data
    """

    for h in other_devices:
        device_data[h] = {
            'ignore': True,  # Ignore by default
            'ignore_reason': 'Other devices ignored in update_dhcp',
            'dhcp': True,  # Found in dhcp file
            'ssh_status': False,
            'swarming': False,
            'doc': False,
            'pool': None,
            'peers': {},
            'chromeos': False
        }
        logging.debug('dhcp other device added %s %s', h, device_data[h])

    for h in hosts:
        device_data[h] = {
            'ignore': True,  # ignore hosts unless it is a wificell
            'ignore_reason': 'host ignored in update_dhcp',
            'dhcp': True,  # Found in dhcp file
            'ssh_status': False,
            'swarming': False,
            'doc': False,
            'pool': None,
            'peers': {},
            'chromeos': True
        }
        logging.debug('dhcp host added  %s %s', h, device_data[h])
    for peer in peer_devices:
        # Do not ignore rpm or servo since these can't be detected from swarming or doc
        if 'rpm' in peer:
            peer_dict = {
                'ignore': False,  # ignore it is a peer of wificell host
                'ignore_reason': 'peer rpm not ignored in update_dhcp',
                'dhcp': True,  # Found in dhcp file
                'ssh_status': False,
                'swarming': True,  # RPM cannot be found in swarming
                'doc': True,  # RPM not recorded in doc
                'chromeos': False
            }
        elif 'servo' in peer:
            peer_dict = {
                'ignore': False,  # ignore it is a peer of wificell host
                'ignore_reason': 'peer servo not ignored in update_dhcp',
                'dhcp': True,  # Found in dhcp file
                'ssh_status': False,
                'swarming':
                True,  # servo is not currently detected from swarming
                'doc':
                True,  # servo is not currentyl detected from the document
                'chromeos': False
            }
        else:
            # Ignore other peer unless they can be found in swarming or doc
            peer_dict = {
                'ignore': True,  # ignore it is a peer of wificell host
                'ignore_reason': 'peer ignored in update_dhcp',
                'dhcp': True,  # Found in dhcp file
                'ssh_status': False,
                'swarming': False,
                'doc': False,
                'chromeos': False
            }
        hostname = '-'.join(peer.split('-')[:4])
        logging.debug('derived host %s from peername %s', hostname, peer)
        # host is not in dhcp but peer is
        if hostname not in device_data:
            logging.debug('peer %s present in dhcp but host %s is not', peer,
                          hostname)
            device_data[hostname] = {
                'ignore': True,  # ignore hosts unless it is a wificell
                'ignore_reason':
                'host derived from peer ignored in update_dhcp',
                'dhcp': False,  # Not found in dhcp file
                'ssh_status': False,
                'swarming': False,
                'doc': False,
                'pool': None,
                'peers': {},
                'chromeos': True
            }

        device_data[hostname]['peers'][peer] = peer_dict


def update_swarming_data(device_data, swarming_data):
    """ update device data with swarming data """

    for h, v in swarming_data.items():
        if 'chromeos3' in h:
            logging.debug('Igonring chaos device %s in chromeos3', h)
            continue

        if v['pool'] in POOLS_TO_IGNORE:
            logging.debug(' %s is in ignored pool %s', h, v['pool'])
            continue

        if h not in device_data:
            logging.error(
                'host %s in swarming but not in dhcp. This should never happen',
                h)
            device_data[h] = {
                'ignore': False,  # ignore hosts unless it is a wificell
                'ignore_reason':
                'wificell host not ignored in update_swarming',
                'dhcp': False,  # Not Found in dhcp file
                'ssh_status': False,
                'swarming': True,
                'doc': False,
                'pool': None,
                'peers': {},
                'chromeos': True
            }
        else:
            device_data[h]['ignore'] = False
            device_data[h][
                'ignore_reason'] = 'wificell host not ignored in update_swarming',
            device_data[h]['swarming'] = True

        device_data[h]['pool'] = v['pool']
        device_data[h]['swarming_data'] = v

        # update status of peer devices
        # wificell devices always have these peers
        # except bt_grover pool
        if v['pool'] != 'bt_groamer':
            expected_peers = _make_peers(h, WIFI_PEERS)

        # some pools have attenuator
        if v['pool'] in ATTENUATOR_POOLS:
            for peer in _make_peers(h, ['attenuator']):
                expected_peers.append(peer)

        # number of btpeers vary. Get the number from swarming
        expected_peers.extend(_make_peers(h, BT_PEERS[:len(v['bt_peers'])]))

        # check only servo v3
        if v['servo']:
            expected_peers.append(servo)

        logging.debug('Expected peers for host %s is %s', h, expected_peers)

        for peer in expected_peers:
            if peer not in device_data[h]['peers']:
                # Peer indicated in swarming data but not in dhcp
                logging.debug('Peer %s not in dhcp but in swarming', peer)
                device_data[h]['peers'][peer] = {
                    'ignore': False,  # ignore hosts unless it is a wificell
                    'ignore_reason':
                    'peer of wificell host not ignored in update_swarming',
                    'dhcp': False,  # Not found in dhcp file
                    'ssh_status': False,
                    'swarming': True,
                    'doc': False
                }
            else:
                device_data[h]['peers'][peer]['swarming'] = True
                device_data[h]['peers'][peer]['ignore'] = False
                device_data[h]['peers'][peer][
                    'ignore_reason'] = 'peer of wificell host not ignored in update_swarming'


def update_conn_doc_data(device_data, conn_doc_data):
    """ update device data using go/cros_conn_device_lifecyle data"""
    for h, v in conn_doc_data.items():
        if h not in device_data:
            logging.debug(
                'host %s not in swarming or dhcp but in go/cros_conn_device_lifecycle',
                h)
            device_data[h] = {
                'ignore': False,  # All DUT in doc is important
                'ignore_reason': 'device found in conn_doc',
                'dhcp': False,  # not found in dhcp file
                'ssh_status': False,
                'swarming': False,  # not found in swarming
                'pool': None,
                'doc': True,
                'peers': {},
                'chromeos': True
            }
        else:
            device_data[h]['doc'] = True
            device_data[h]['ignore'] = False

        device_data[h]['doc_data'] = v

        # Ignore this host and peers
        # Used for test bed until construction
        ignore_test_bed = False

        if device_data[h]['pool'] is None:
            if v['pool'] in POOLS_TO_IGNORE:
                logging.debug(
                    'device %s doc data has pool %s which is to be ignored', h,
                    v['pool'])
                device_data[h]['ignore'] = True
                device_data[h]['ignore_reason'] = 'pool ignored'
                ignore_test_bed = True
        if v['model'] == '':
            logging.debug('Empty model. Ignoring %s', h)
            device_data[h]['ignore'] = True
            device_data[h]['ignore_reason'] = 'empty model ignored'
            ignore_test_bed = True

        if '[wip]' in _parse_doc_model_name(v['model']):
            logging.debug('WIP  Ignoring %s', h)
            device_data[h]['ignore'] = True
            device_data[h]['ignore_reason'] = 'WIP device ignored'
            ignore_test_bed = True

        # update status of peers
        documented_peers = []
        for i in v['btpeers']:
            documented_peers.append(h + '-' + i)
        # bt_groamer doesn't have wifi peersx
        if 'wificell' in v['labels'] and v['pool'] != 'bt_groamer':
            for i in WIFI_PEERS:
                documented_peers.append(h + '-' + i)
        logging.debug('documented peers for %s is %s', h, documented_peers)
        if v['pool'] in ATTENUATOR_POOLS:
            documented_peers.extend(_make_peers(h, ['attenuator']))

        for peer in documented_peers:
            if peer not in device_data[h]['peers']:
                logging.debug('%s in doc data but not swarming', peer)
                device_data[h]['peers'][peer] = {
                    'ignore':
                    ignore_test_bed,  # ignore hosts unless it is a wificell
                    'ignore_reason':
                    'peer if dut with ignore_test_bed %s ' % ignore_test_bed,
                    'dhcp': False,  # Not found in dhcp file
                    'ssh_status': False,
                    'swarming': False,  # Found in swarming
                    'doc': True,
                    'chromeos': False
                }
            else:
                device_data[h]['peers'][peer]['doc'] = True
                device_data[h]['peers'][peer]['ignore'] = ignore_test_bed


def check_connectivity(device_data, recheck=False):
    """ check if device is pingable and sshable"""

    def _add_to_result(result_dict, rhost, result):
        logging.debug('Adding to result %s %s', rhost, result)
        if rhost in result_dict:
            logging.error('rhost %s already present in result', rhost)
            logging.error('This should not happen###')
            raise ValueError

        result_dict[rhost] = result

    devices_to_check = {
        'hosts': [],
        'peers': {},
    }
    # Only check devices which are present in DHCP data
    for host, host_value in device_data.items():
        if not host_value['ignore'] and host_value['dhcp']:
            # On  recheck, check devices which is not up
            if not recheck or host_value['ssh_status'] != HOST_UP:
                devices_to_check['hosts'].append(host)
            for peer, peer_value in host_value['peers'].items():
                if not peer_value['ignore'] and peer_value['dhcp']:
                    if not recheck or peer_value['ssh_status'] != HOST_UP:
                        devices_to_check['peers'][peer] = host

    device_list = devices_to_check['hosts'][:]
    device_list.extend(list(devices_to_check['peers'].keys()))

    #
    # GetHostStatus function is called in separate process for each dut
    # Each of these process put the result in a queue
    # THe main process get results from queue and joins the processes
    # The processes was getting hung probably since the queue was growing large
    # Adding code to remove items from the queue resolved the issue
    #

    q = Queue(32000)
    result_dict = {}
    process_list = []
    count = 0
    for host in device_list:
        p = Process(target=getHostStatus, args=(q, host))
        p.start()
        process_list.append((p, host))
        logging.debug('starting check %s %s', host, count)
        count += 1

        try:
            (rhost, result) = q.get(block=False)
            _add_to_result(result_dict, rhost, result)
        except queue.Empty:
            pass

    while process_list != []:
        logging.info('{} processes remaining '.format(len(process_list)))
        logging.debug(' process list %s result %s queue size %s ',
                      len(process_list), len(result_dict), q.qsize())
        for (p, host) in process_list:
            # empty queue to prevent the proceess from hanging
            try:
                (rhost, result) = q.get(block=False)
                _add_to_result(result_dict, rhost, result)
            except queue.Empty:
                pass

            if not p.is_alive():
                logging.info('{} process has ended'.format(host))
                p.join()
                process_list.remove((p, host))
            else:
                logging.info('{} process pending'.format(host))
        logging.debug('sleeping for 3 seconds')
        time.sleep(3)

    while not q.empty():
        (rhost, result) = q.get(timeout=2)
        _add_to_result(result_dict, rhost, result)

    if len(result_dict) != len(device_list):
        logging.error(
            'Length of result %s is not equal to length'
            'of device list %s', len(result_dict), len(device_list))
        for h in result_dict:
            if h not in device_list:
                logging.error('%s not in device_list', h)
        for h in device_list:
            if h not in result_dict:
                logging.error('%s not in result', h)

        raise ValueError

    _pretty_print(result_dict, 'result_dict')

    for h in devices_to_check['hosts']:
        device_data[h]['ssh_status'] = result_dict[h]

    for p, h in devices_to_check['peers'].items():
        device_data[h]['peers'][p]['ssh_status'] = result_dict[p]


# error conditions
IGNORED = 'IGNORED'
IMPOSSIBLE = 'ERROR'  # Impossible combination like device not in DHCP but ssh-able
NOT_DOCUMENTED = 'NOT DOCUMENTED'
NOT_IN_DHCP = 'NOT IN DHCP BUT DOCUMENTED'
NOT_IN_SWARMING = 'NOT IN SWARMING BUT IN DHCP'
NOT_REACHABLE = 'NOT PINGABLE OR SSH-ABLE'
IN_SWARMING_NOT_IN_DHCP = 'IN SWARMING BUT NOT IN DHCP FILE '
ONLINE_BUT_NOT_IN_DHCP = 'DEVICE IS UP BUT NOT IN DHCP FILE!'
ALL_OK = 'UP'

BAD_STATES = [
    NOT_REACHABLE, NOT_IN_SWARMING, NOT_DOCUMENTED, IMPOSSIBLE, NOT_IN_DHCP,
    IN_SWARMING_NOT_IN_DHCP, ONLINE_BUT_NOT_IN_DHCP
]

#              ignore, dhcp,  ssh   swarming, doc : result
error_dict = {
    (False, False, False, False, False): IMPOSSIBLE,
    (False, False, False, False, True): NOT_IN_DHCP,
    (False, False, False, True, False): IN_SWARMING_NOT_IN_DHCP,
    (False, False, False, True, True): IN_SWARMING_NOT_IN_DHCP,
    (False, False, True, False, False): ONLINE_BUT_NOT_IN_DHCP,
    (False, False, True, False, True): ONLINE_BUT_NOT_IN_DHCP,
    (False, False, True, True, False): IN_SWARMING_NOT_IN_DHCP,
    (False, False, True, True, True): IN_SWARMING_NOT_IN_DHCP,
    (False, True, False, False, False): NOT_REACHABLE,
    (False, True, False, False, True): NOT_REACHABLE,
    (False, True, False, True, False): NOT_REACHABLE,
    (False, True, False, True, True): NOT_REACHABLE,
    (False, True, True, False, False): NOT_IN_SWARMING,
    (False, True, True, False, True): NOT_IN_SWARMING,
    (False, True, True, True, False): NOT_DOCUMENTED,
    (False, True, True, True, True): ALL_OK,
    (True, False, False, False, False): IGNORED,
    (True, False, False, False, True): IGNORED,
    (True, False, False, True, False): IGNORED,
    (True, False, False, True, True): IGNORED,
    (True, False, True, False, False): IGNORED,
    (True, False, True, False, True): IGNORED,
    (True, False, True, True, False): IGNORED,
    (True, False, True, True, True): IGNORED,
    (True, True, False, False, False): IGNORED,
    (True, True, False, False, True): IGNORED,
    (True, True, False, True, False): IGNORED,
    (True, True, False, True, True): IGNORED,
    (True, True, True, False, False): IGNORED,
    (True, True, True, False, True): IGNORED,
    (True, True, True, True, False): IGNORED,
    (True, True, True, True, True): IGNORED,
}


def generate_dashboard(device_data):
    """ Analyses device_data and prepare result to be populated in dashboard"""

    for host, hv in device_data.items():
        logging.debug(host)
        _pretty_print(hv)

        peer_error_found = False  # Unreachable peer which should be flagged in main dashboard
        issue_found = False  # Any other issue which is displayed in secondary dashboard

        hv['device_status'] = error_dict[(hv['ignore'], hv['dhcp'],
                                          not (hv['ssh_status'] == HOST_DOWN),
                                          hv['swarming'], hv['doc'])]
        logging.debug(
            'ignore %s dhcp %s swarming %s ssh_status %s not ssh_status == HOST_DOWN %s doc %s status %s',
            hv['ignore'], hv['dhcp'], hv['swarming'], hv['ssh_status'],
            not (hv['ssh_status'] == HOST_DOWN), hv['doc'],
            hv['device_status'])
        logging.debug(error_dict[(False, True, True, False, True)])

        # main dashboard need not show status of DUT since there is a separate dashboard for that.
        if hv['device_status'] != IGNORED and hv['device_status'] in BAD_STATES:
            issue_found = True

        logging.debug('device status is %s', hv['device_status'])

        if 'peers' in hv.keys():
            for peer, pv in hv['peers'].items():
                logging.debug(peer)
                logging.debug(pv)
                pv['device_status'] = error_dict[(
                    pv['ignore'], pv['dhcp'],
                    not (pv['ssh_status'] == HOST_DOWN), pv['swarming'],
                    pv['doc'])]
                logging.debug(
                    'ignore %s dhcp %s swarming %s ssh_status %s not(ssh_status == HOST_DOWN) %s doc %s',
                    pv['ignore'], pv['dhcp'], pv['swarming'], pv['ssh_status'],
                    not (pv['ssh_status'] == HOST_DOWN), pv['doc'])

                # If the host is ignored then do not show it in the dashboard
                if hv['device_status'] == IGNORED:
                    logging.debug('device status is %s ignoring %s',
                                  hv['device_status'], host)
                    issue_found = issue_found or pv[
                        'device_status'] in BAD_STATES
                else:
                    peer_error_found = peer_error_found or pv[
                        'device_status'] == NOT_REACHABLE
                logging.debug('device status is %s', pv['device_status'])

        # Documentation errors
        hv['documentation_errors'] = []
        # check only chromeos devices and avoid ignored devices
        if hv['device_status'] != IGNORED and hv['chromeos']:
            # model/boards of host in go/conn-device-lifecycle is different from swarming
            if hv['swarming'] and hv['doc']:
                if hv['swarming_data']['model'] not in _parse_doc_model_name(
                        hv['doc_data']['model']):
                    hv['documentation_errors'].append(
                        'model in swarming "%s" differs from model in doc "%s"'
                        % (hv['swarming_data']['model'],
                           hv['doc_data']['model']))
                if hv['swarming_data']['board'] != hv['doc_data'][
                        'board'].strip():
                    hv['documentation_errors'].append(
                        'board in swarming "%s" differs from board in doc "%s"'
                        % (hv['swarming_data']['board'],
                           hv['doc_data']['board']))
            # Pool differs
            if hv['swarming'] and hv['doc']:
                if hv['swarming_data']['pool'] != hv['doc_data']['pool']:
                    hv['documentation_errors'].append(
                        'pool in swarming "%s" differs from pool in doc "%s"' %
                        (hv['swarming_data']['pool'], hv['doc_data']['pool']))
            # wificell / conductive label differ
            if hv['swarming'] and hv['doc']:
                if hv['swarming_data']['wificell'] != (
                        'wificell' in hv['doc_data']['labels']):
                    hv['documentation_errors'].append(
                        'label:wificell differs between doc and swarming')
                    _pretty_print(hv)
                    logging.debug('label wificell discrepencise %s %s',
                                  hv['swarming_data']['wificell'],
                                  'wificell' in hv['doc_data']['labels'])
            # bluetooth label not found
            if hv['swarming'] and not hv['swarming_data']['bluetooth_label']:
                hv['documentation_errors'].append('Bluetooth label not found')

        if hv['documentation_errors'] != []:
            logging.debug(hv['documentation_errors'])

        hv['peer_error_found'] = peer_error_found
        hv['issue_found'] = issue_found
    _pretty_print(device_data)

    logging.debug('## IGNORED devices')
    for host, hv in device_data.items():
        if hv['device_status'] == IGNORED:
            logging.debug('IGNORED DEVICE %s', (host))
            _pretty_print(hv)
    logging.debug('## IGNORED devices END')

    logging.debug('## IMPOSSIBLE devices')
    for host, hv in device_data.items():
        if hv['device_status'] == IMPOSSIBLE:
            logging.debug('IMPOSSIBLE DEVICE %s', (host))
            _pretty_print(hv)
    logging.debug('## IMPOSSIBLE devices END')


def populate_dashboard(spreadsheet_name, device_data):
    def _find_header(d):
        """ given list of dicts,find all keys"""
        header = [
            'pool',
            'host',
            'model',
            'host_status',
        ]
        peer_header = []
        for _, v in d.items():
            if 'peers' in v:
                for p, pv in v['peers'].items():
                    if pv['ignore']:
                        continue
                    logging.debug(p)
                    peer_suffix = p.split('-')[4]
                    if peer_suffix not in peer_header:
                        peer_header.append(peer_suffix)
        peer_header.sort()
        header.extend(peer_header)
        logging.debug('header is %s', header)
        return header

    def _populate_document_sheet(wsheet, msgs, header, data):
        row_count = 1
        for i, m in enumerate(msgs):
            wsheet.insert_row(m.split(' '), i + row_count)
            logging.debug('Writing %s at %s', m, i + row_count)

        row_count += len(msgs)
        wsheet.insert_row([h.upper() for h in header], row_count)
        logging.debug('writing header at %s', row_count)
        wsheet.format(
            'A%s:S%s' % (row_count, row_count),
            {'backgroundColor': {
                'red': 0.0,
                'green': 0.5,
                'blue': 0.5
            }})

        row_count += 1

        row_length = 12

        cell_start_index = row_count
        cell_end_index = cell_start_index + len(data)
        range_label = 'A%s:%s%s' % (cell_start_index,
                                    '-ABCDEFGHIJKLMNOPQR' [row_length],
                                    cell_end_index)
        logging.debug('range_label %s', range_label)
        cell_list = wsheet.range(range_label)
        logging.debug('cell_list Info: %s', (cell_list))
        cell_list_index = 0

        host_list = list(data.keys())
        host_list.sort()
        for host in host_list:
            hv = data[host]
            if hv['documentation_errors'] == []:
                continue
            logging.debug('%s %s', host, hv['documentation_errors'])
            _pretty_print(hv)
            cell_list[cell_list_index].value = hv['pool']
            cell_list_index += 1
            cell_list[cell_list_index].value = host
            cell_list_index += 1
            cell_list[cell_list_index].value = hv['swarming_data'][
                'model'] if hv['swarming'] else '--'
            cell_list_index += 1

            logging.debug(
                '%s %s %s %s', hv['pool'], host,
                hv['swarming_data']['model'] if hv['swarming'] else '--',
                hv['documentation_errors'])
            for e in hv['documentation_errors']:
                cell_list[cell_list_index].value = e
                cell_list_index += 1
            for i in range(3 + len(hv['documentation_errors']), row_length):
                cell_list[cell_list_index].value = ''
                cell_list_index += 1
        wsheet.update_cells(cell_list)

    def _populate_lab_sheet(wsheet,
                            msgs,
                            header,
                            data,
                            error_field='peer_error_found'):
        row_count = 1
        for i, m in enumerate(msgs):
            wsheet.insert_row(m.split(' '), i + row_count)
            logging.debug('Writing %s at %s', m, i + row_count)

        row_count += len(msgs)

        wsheet.insert_row([h.upper() for h in header], row_count)
        logging.debug('writing header at %s', row_count)
        wsheet.format(
            'A%s:S%s' % (row_count, row_count),
            {'backgroundColor': {
                'red': 0.0,
                'green': 0.5,
                'blue': 0.5
            }})
        row_count += 1

        cell_start_index = row_count
        cell_end_index = cell_start_index + len(data)
        range_label = 'A%s:%s%s' % (cell_start_index,
                                    '-ABCDEFGHIJKLMNOPQR' [len(header)],
                                    cell_end_index)
        logging.debug('range_label %s', range_label)
        cell_list = wsheet.range(range_label)
        logging.debug('cell_list Info: %s', (cell_list))
        cell_list_index = 0

        host_list = list(data.keys())
        host_list.sort()
        for host in host_list:
            hv = data[host]
            if not hv[error_field]:
                continue
            if 'rpm' in host:
                print('error found')
                logging.debug('%s %s', host, hv['device_status'])
            logging.debug('%s %s', host, hv['device_status'])
            _pretty_print(hv)
            cell_list[cell_list_index].value = hv['pool']
            cell_list_index += 1
            cell_list[cell_list_index].value = host
            cell_list_index += 1
            cell_list[cell_list_index].value = hv['swarming_data'][
                'model'] if hv['swarming'] and 'swarming_data' in hv else '--'
            cell_list_index += 1
            cell_list[cell_list_index].value = hv['ssh_status'] if hv[
                'device_status'] == NOT_REACHABLE else hv['device_status']
            cell_list_index += 1
            logging.debug('%s %s %s', hv['pool'], host, hv['device_status'])

            for suffix in header[4:]:
                peername = host + '-' + suffix
                if 'peers' in hv and peername in hv['peers']:
                    cell_list[cell_list_index].value = hv['peers'][peername][
                        'ssh_status'] if hv['peers'][peername][
                            'device_status'] == NOT_REACHABLE else hv['peers'][
                                peername]['device_status']
                    logging.debug('%s %s', peername,
                                  hv['peers'][peername]['device_status'])
                else:
                    cell_list[cell_list_index].value = '--'
                    logging.debug('peername not found %s', peername)
                cell_list_index += 1

        wsheet.update_cells(cell_list)

    """ Display the data in the dashboard"""
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        json_keyfile, scope)
    gc = gspread.authorize(credentials)
    spreadsheet = gc.open(spreadsheet_name)

    worksheet = 'DOWN PEERS'
    wsheet1 = spreadsheet.worksheet(worksheet)
    wsheet1.clear()
    wsheet1.format(
        'A1:S1000',
        {'backgroundColor': {
            'red': 1.0,
            'green': 1.0,
            'blue': 1.0
        }})

    worksheet = 'DOCUMENTATION ERRORS'
    wsheet2 = spreadsheet.worksheet(worksheet)
    wsheet2.clear()
    wsheet2.format(
        'A1:S1000',
        {'backgroundColor': {
            'red': 1.0,
            'green': 1.0,
            'blue': 1.0
        }})

    worksheet = 'OTHER ERRORS'
    wsheet3 = spreadsheet.worksheet(worksheet)
    wsheet3.clear()
    wsheet3.format(
        'A1:S1000',
        {'backgroundColor': {
            'red': 1.0,
            'green': 1.0,
            'blue': 1.0
        }})

    lab_issues, documentation_issues, other_issues = False, False, False
    lab_messages = []
    doc_messages = []
    other_messages = []

    for k, v in device_data.items():
        if v['peer_error_found']:
            lab_issues = True
        if v['documentation_errors'] != []:
            documentation_issues = True
        if v['issue_found']:
            other_issues = True
        if lab_issues and documentation_issues and other_issues:
            break

    if not lab_issues:
        lab_messages = ['No Issues Found. Check other tabs']
    if not documentation_issues:
        doc_messages = ['No Issues Found. Check other tabs']
    if not other_issues:
        other_messages = ['No Issues Found. Check other tabs']

    messages = [
        'LAST_UPDATED_AT %s' % str(datetime.datetime.now()),
        'NEXT_UPDATE_WILL_BE_AT %s' %
        (str(datetime.datetime.now() +
             datetime.timedelta(seconds=DASHBOARD_REFRESH_INTERVAL)))
    ]

    lab_messages.extend(messages)
    _pretty_print(lab_messages)
    doc_messages.extend(messages)
    _pretty_print(doc_messages)
    other_messages.extend(messages)
    _pretty_print(other_messages)

    logging.debug('writing the lab sheet')
    header = _find_header(device_data)
    _populate_lab_sheet(wsheet1, lab_messages, header, device_data)

    logging.debug('writing the other sheet')
    header = _find_header(device_data)
    _populate_lab_sheet(wsheet3,
                        lab_messages,
                        header,
                        device_data,
                        error_field='issue_found')

    logging.debug('writing the document sheet')
    header = ['pool', 'host', 'model', 'Documentation errors']
    _populate_document_sheet(wsheet2, doc_messages, header, device_data)
    logging.debug('populate_dashboard_complete')


def dict_diff(s1, s2):
    if type(s1) == dict and type(s2) == dict:
        for k in s1:
            if k not in s2:
                print('key %s missing in second' % k)
        for k in s2:
            if k not in s1:
                print('key %s missing in first' % k)

        for k, v1 in s1.items():
            if k in s2:
                if type(v1) == dict:
                    dict_diff(v1, s2[k])
                elif v1 != s2[k]:
                    logging.debug('value %s %s differs', v1, s2[k])


def debug_main():
    """ Debug version of Main function  """

    device_data = {}

    #Read the list of rpms to check
    rpm_list = get_rpm_list()
    update_rpm_data(device_data, rpm_list)

    # Get dhcp data and update device data
    (hosts, peer_devices, other_devices) = get_dhcp_data.get_data()
    update_dhcp_data(device_data, hosts, peer_devices, other_devices)
    logging.debug("After update_dhcp_data")
    _pretty_print(device_data)
    input()

    # use this to debug the script without getting swarming data everytime
    with open('/tmp/skylab_hosts.json') as json_file:
        swarming_data = json.load(json_file)
    _pretty_print(swarming_data)

    # Get swarming data and update device_data
    #swarming_data = get_wificell_data.get_data()
    #_pretty_print(swarming_data)

    update_swarming_data(device_data, swarming_data)
    _pretty_print(device_data)
    logging.debug("After update_swarming_data")
    input()

    # Get data from g/cros_conn_device_lifecycle and updat device data
    conn_doc_data = get_wifisheet_data.get_wifisheet_data()
    update_conn_doc_data(device_data, conn_doc_data)
    _pretty_print(device_data)
    logging.debug("After update_conn_data")
    input()

    with open('data.txt', 'w') as outfile:
        json.dump(device_data, outfile)

    with open('data.txt') as json_file:
        device_data = json.load(json_file)

    check_connectivity(device_data)
    logging.debug("After check_connectivity")
    input()
    logging.info('Waiting for 2 seconds before checking connectivity again')
    time.sleep(2)
    check_connectivity(device_data, recheck=True)
    logging.debug("After check_connectivity recheck")
    input()

    with open('data2.txt', 'w') as outfile:
        json.dump(device_data, outfile)

    with open('data2.txt') as json_file:
        device_data = json.load(json_file)

    _pretty_print(device_data)
    generate_dashboard(device_data)
    logging.debug("After generate_dashboard")
    input()
    populate_dashboard(SPREADSHEET_ALL, device_data)
    logging.debug("After populate_dashboard")
    input()


def main():
    """ Main function  """

    device_data = {}

    #Read the list of rpms to check
    rpm_list = get_rpm_list()
    update_rpm_data(device_data, rpm_list)

    # Get dhcp data and update device data
    (hosts, peer_devices, other_devices) = get_dhcp_data.get_data()
    update_dhcp_data(device_data, hosts, peer_devices, other_devices)

    # Get swarming data and update device_data
    swarming_data = get_wificell_data.get_data()
    update_swarming_data(device_data, swarming_data)

    # Get data from g/cros_conn_device_lifecycle and updat device data
    conn_doc_data = get_wifisheet_data.get_wifisheet_data()
    update_conn_doc_data(device_data, conn_doc_data)

    # Check connectivity of devices
    check_connectivity(device_data)
    logging.info('Waiting for %s seconds before checking connectivity again',
                 CONNECTIVITY_RETEST_INTERVAL)
    time.sleep(CONNECTIVITY_RETEST_INTERVAL)
    check_connectivity(device_data, recheck=True)

    generate_dashboard(device_data)
    populate_dashboard(SPREADSHEET_ALL, device_data)

    _pretty_print(device_data)


if __name__ == '__main__':
    if int(sys.version.split(' ')[0].split('.')[0]) != 3:
        print('Please invoke with python3')
        sys.exit()
    while True:
        try:
            logging.debug('Ctrl-C to stop')
            main()
            #debug_main()
            logging.debug('Sleeping for %s seconds',
                          DASHBOARD_REFRESH_INTERVAL)
            time.sleep(DASHBOARD_REFRESH_INTERVAL)
        except KeyboardInterrupt:
            sys.exit()
        except Exception as e:
            logging.error(
                'Exception %s while running script. Press any key to continue',
                str(e))
            input()
            logging.debug('Sleeping for %s seconds',
                          DASHBOARD_REFRESH_INTERVAL)
            time.sleep(DASHBOARD_REFRESH_INTERVAL)
