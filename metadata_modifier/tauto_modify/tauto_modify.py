# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Helper script to parse autotest control files for data gathering."""

import os
import pathlib

import actions
import cf_parse
import filters


# ChromeOS src/ dir relative to this file.
SRC_DIR = pathlib.Path(__file__).joinpath('../../../../..').resolve()

def modify_control_files(action_func_list, filter_func_list, dry_run):
    # Places to look for control files, relative to SRC_DIR.
    AUTOTEST_DIRS = [
            'third_party/autotest/files/client/site_tests/',
            'third_party/autotest/files/server/site_tests/',
            'third_party/autotest-private/client/site_tests/',
    ]

    for tests_dir in [pathlib.Path(SRC_DIR, d) for d in AUTOTEST_DIRS]:
        for cf_path in tests_dir.glob('*/control*'):
            cf = cf_parse.ControlFile(cf_path)
            if not cf.is_valid:
                continue

            # Skip this control file if it doesn't match all the given filters.
            if not all(filter_func(cf) for filter_func in filter_func_list):
                continue

            # Apply the given actions to this control file.
            if not any(action_func(cf) for action_func in action_func_list):
                continue
            cf.update_contents()

            if dry_run:
                print(f'Will modify {cf_path}:')
                print(cf.contents)
            else:
                print(f'Editing {cf_path}')
                with open(cf.path, 'w', encoding='utf-8') as f:
                    f.write(cf.contents)


def main():
    os.chdir(SRC_DIR)
    action_func = actions.remove_contacts(['notarealemail@google.com'])
    filter_func = filters.all_tests()
    dry_run = True
    modify_control_files([action_func], [filter_func], dry_run)

if __name__ == '__main__':
    main()
