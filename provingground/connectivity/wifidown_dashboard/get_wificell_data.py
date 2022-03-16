# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import subprocess
import json
import sys
import logging

from constants import SWARMING_PATH

#
# Execute this script to download swarming info
#

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


def _get_wificell_data():
    cmd = "python3  {}swarming.py query --swarming https://chromeos-swarming.appspot.com 'bots/list?dimensions=pool%3AChromeOSSkylab&dimensions=label-wificell%3ATrue&quarantined=FALSE&limit=1000'".format(
        SWARMING_PATH)
    print("executing %s" % cmd)
    output = json.loads(subprocess.check_output(cmd, shell=True))
    # keys (['death_timeout', 'items', 'now']
    return output['items']


def parse_swarming_entry(i):
    try:
        is_bt = False
        is_bt_new = []
        b = None
        m = None
        name = None
        p = None
        deleted = i['deleted']
        is_dead = i['is_dead']
        bluetooth_label = None
        wifichip = None
        conductive = False
        hw_phase = None
        servo_v3 = False
        wificell = False
        for j in i['dimensions']:
            if j['key'] == 'label-wificell':
                wificell = j['value'][0] == 'True'
            if j['key'] == 'label-pool':
                p = j['value'][0]
            if j['key'] == 'label-board':
                b = j['value'][0]
            if j['key'] == 'label-bluetooth':
                bluetooth_label = True
            if j['key'] == 'label-model':
                m = j['value'][0]
            if j['key'] == 'dut_name':
                name = j['value'][0]
            if j['key'] == 'label-chameleon_type':
                is_bt = 'CHAMELEON_TYPE_BT_PEER' in j['value']
            if j['key'] == 'label-working_bluetooth_btpeer':
                is_bt_new.extend(j['value'])
            if j['key'] == 'label-wifi_chip':
                wifichip = j['value'][0]
            if j['key'] == 'dut_state':
                dut_state = j['value'][0]
            if j['key'] == 'label-conductive':
                conductive = True
            if j['key'] == 'label-phase':
                hw_phase = j['value'][0]
            if j['key'] == 'servo_type':
                servo_v3 = j['value'][0] == 'servo_v3'

        res = {
            'host': name,
            'board': b,
            'model': m.lower(),
            'bt_label': is_bt,
            'bt_peers': is_bt_new[:],
            'pool': p,
            'is_dead': is_dead,
            'deleted': deleted,
            'bluetooth_label': bluetooth_label,
            'wifichip': wifichip,
            'conductive': conductive,
            'hw_phase': hw_phase,
            'missing': False,
            'wificell': wificell,
            'servo': servo_v3
        }
        if name is None:
            logging.debug(i)
            logging.debug(res)
            return None
        return res
    except Exception as e:
        logging.error("exception in parse_swarming entry '%s'", str(e))
        return None


def parse_raw_data(raw_data):
    d = {}
    for k, v in raw_data.items():
        if k != 'dimensions':
            d[k] = v
    for l in raw_data['dimensions']:
        k = l['key']
        v = l['value']
        if k in d:
            logging.debug("key %s already present" % k)
        d[k] = v
    logging.debug(d)
    return d


def get_data():
    raw_data = _get_wificell_data()
    data = {}
    for rd in raw_data:
        d = parse_swarming_entry(rd)
        if d is None:
            continue
        if d['is_dead']:
            logging.debug('igoring dead dut %s' % d)
            continue
        host = d['host']
        data[host] = d
    return data


def main():
    if int(sys.version.split(' ')[0].split('.')[0]) != 3:
        print("Please invoke with python3")
        sys.exit()
    data = get_data()
    for i in data.items():
        print(i)
    # Save host info to a file for debugging purpose
    with open('/tmp/skylab_hosts.json', 'w') as fp:
        json.dump(data, fp)


if __name__ == '__main__':
    main()
