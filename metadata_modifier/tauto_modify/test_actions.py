# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for actions."""

import os
import unittest

import actions
import cf_parse

TEST_DATA_DIR = 'test_data/'

class TestActions(unittest.TestCase):
    """Tests for actions."""
    def test_remove_contacts(self):
        delete_me = 'removable@google.com'
        action = actions.remove_contacts([delete_me])
        test_file = os.path.join(TEST_DATA_DIR, 'control.actions')
        cf = cf_parse.ControlFile(test_file)

        self.assertTrue('contacts' in cf.metadata)
        self.assertTrue(delete_me in cf.metadata['contacts'])
        modified = action(cf)
        self.assertTrue(modified)
        self.assertTrue('contacts' in cf.metadata)
        self.assertFalse(delete_me in cf.metadata['contacts'])

        modified = action(cf)
        self.assertFalse(modified)

if __name__ == '__main__':
    unittest.main()
