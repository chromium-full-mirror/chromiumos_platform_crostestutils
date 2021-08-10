# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import sys
import re

from constants import DHCP_PATH

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)


def get_data():
    """
    Read the DHCP file and get devices in chromeos15
    @returns (hosts, other_devices) where hosts are anything that matches
             chromeos15-row*-rack*-host* and other_devices are anything that
             are not hosts but starts with chromeos15-
    """
    data = [i.strip() for i in open(DHCP_PATH).read().split('\n')]
    data = [
        i.split(' ')[1] for i in data
        if i != '' and i[0] != '#' and 'chromeos15' in i and i[:5] == 'host '
    ]
    pattern = 'chromeos15-row.*-rack.*-host.*'
    peer_pattern = 'chromeos15-row.*-rack.*-host.*-.*'
    metro_pattern = 'chromeos15-row.*-metro.*-host.*'
    metro_peer_pattern = 'chromeos15-row.*-metro.*-host.*-.*'
    hosts = []
    peer_devices = []
    other_devices = []
    for i in data:
        if re.match(pattern, i) is not None:
            if re.match(peer_pattern, i) is not None:
                peer_devices.append(i)
            else:
                hosts.append(i)
        elif re.match(metro_pattern, i) is not None:
            if re.match(metro_peer_pattern, i) is not None:
                peer_devices.append(i)
            else:
                hosts.append(i)
        else:
            other_devices.append(i)
    return (hosts, peer_devices, other_devices)


def main():
    if int(sys.version.split(' ')[0].split('.')[0]) != 3:
        print("Please invoke with python3")
        sys.exit()
    (hosts, peer_devices, other_devices) = get_data()
    print('hosts')
    for i in hosts:
        print(i)

    print('peer_devices')
    for i in peer_devices:
        print(i)

    print('other devices')
    for i in other_devices:
        print(i)

    print("%s hosts found" % len(hosts))
    print("%s peer_devices found" % len(peer_devices))
    print("%s other_devices found" % len(other_devices))

    #h = 'chromeos15-row8-rack1-host4'
    #if h not in hosts and h not in other_devices and h not in peer_devices:
    #    print("%s not found" % h)
    #else:
    #    print("%s found" % h)


if __name__ == '__main__':
    main()
