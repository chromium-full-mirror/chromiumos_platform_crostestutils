# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import gspread
import sys
from oauth2client.service_account import ServiceAccountCredentials
from credentials import json_keyfile

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

#
# Read data from go/conn-device-life-cycle
#

SHEETS_LIST = [
    'Row1 & 2 (Conductive/PerBuild)',
    'Row4 (OTA)',
    'Row5 (BT perbuild)',
    'Row7',
    'Row8',
    'Row8-metro',
    'Row9',
    'Row3 (Grover)',
    'Row3 (Pre-Cq)',
    'Row4 (Pre-Cq)',
    'Row6(Pre-Cq)',
]


def read_wifi_device_sheet():
    """ Read data from go/conn-device-lifecycle sheet"""
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        json_keyfile, scope)
    gc = gspread.authorize(credentials)
    # go/conn-device-life-cycle
    spreadsheet = gc.open_by_key(
        '1DhwNaPSbdXudWIrjBJpiLViOPOjrmBGy7BpIYZr9TqQ')
    data = []
    for sheet in spreadsheet.worksheets():
        if sheet.title not in SHEETS_LIST:
            logging.info("ignoring sheet |%s|", sheet.title)
            continue
        logging.debug("Reading sheet %s !!!!", sheet.title)
        values = sheet.get_all_records()
        for i in values:
            logging.debug(i)
            if 'Hostname' not in i or i['Hostname'] != '':
                data.append(i)
            else:
                logging.debug("ignoring %s", i)
    return data


def process_data(raw_data):
    """ Get required columns"""

    def _get_pool(p):
        try:
            for i in p.split(','):
                if 'pool' in i:
                    return i.split(':')[1].strip(' ').lower()
            return None
        except:
            logging.error("error parsing pool string %s", p)
            return None

    def _get_labels(p):
        return [i.strip() for i in p.split(',')]

    data = {}
    for i in raw_data:
        try:
            logging.debug(i)
            hostname = i['Hostname'].lower()
            if hostname[:8] != 'chromeos':
                logging.debug("Igorning %s", hostname)
                continue
            model = i['Model'].lower()
            board = i['Board'].lower()
            pool = _get_pool(i['Atest Labels'])
            labels = _get_labels(i['Atest Labels'])

            if 'Pi (btpeer hostname)' in i:
                num_btpeers = i['Pi (btpeer hostname)']
            else:
                num_btpeers = 0

            if hostname in data:
                logging.error("Duplicate entry for %s", hostname)

            data[hostname] = {}
            if model == '' or model == 'empty cell':
                data[hostname]['model'] = ''
            else:
                data[hostname]['model'] = model

            if board == '' or board == 'empty cell':
                data[hostname]['board'] = ''
            else:
                data[hostname]['board'] = board

            data[hostname]['pool'] = pool

            btpeers = []

            if num_btpeers in ['', 'no']:
                pass
            else:
                try:
                    btpeers.extend([
                        'btpeer' + str(i)
                        for i in range(1,
                                       int(num_btpeers) + 1)
                    ])
                except:
                    logging.error("Exception while parsing num_btpeers %s",
                                  num_btpeers)

            data[hostname]['btpeers'] = btpeers

            data[hostname]['labels'] = labels
            logging.debug("Adding %s %s" % (hostname, data[hostname]))
        except Exception as e:
            logging.debug(sys.exc_info())
            logging.debug("Exception %s while processing %s %s" %
                          (e, i, sys.exc_info()))
    return data


def get_wifisheet_data():
    raw_data = read_wifi_device_sheet()
    #logging.debug(raw_data)
    data = process_data(raw_data)
    #logging.debug(data)
    for i in data:
        print(i)
    return data


if __name__ == '__main__':
    for i, v in get_wifisheet_data().items():
        print(i)
        print(v)
