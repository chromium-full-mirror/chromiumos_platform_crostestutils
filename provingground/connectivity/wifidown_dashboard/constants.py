# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys

USERNAME = os.environ['USER']
SWARMING_PATH = '/usr/local/google/home/%s/depot_tools/infra/luci/client/' % USERNAME
DHCP_PATH = '/usr/local/google/home/%s/chromiumos/chromeos-admin/puppet/modules/lab/files/dhcp-server/dhcpd.conf' % USERNAME


def main():
    if int(sys.version.split(' ')[0].split('.')[0]) != 3:
        print("Please invoke with python3")
        sys.exit()
    print('SWARMING PATH is %s' % SWARMING_PATH)
    print('DHCP_PATH is %s' % DHCP_PATH)


if __name__ == '__main__':
    main()
