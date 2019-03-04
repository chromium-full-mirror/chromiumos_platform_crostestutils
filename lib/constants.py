# -*- coding: utf-8 -*-
# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module containing contants to be used across crostestutils."""

from __future__ import print_function

import os

_TEST_LIB_PATH = os.path.dirname(os.path.realpath(__file__))

CROSTESTUTILS_DIR = os.path.dirname(_TEST_LIB_PATH)

CROS_PLATFORM_ROOT = os.path.join(CROSTESTUTILS_DIR, '..')

DEFAULT_CHROOT_DIR = 'chroot'

SOURCE_ROOT = os.path.realpath(os.path.join(
    _TEST_LIB_PATH, '..', '..', '..', '..'))

CROSUTILS_DIR = os.path.join(SOURCE_ROOT, 'src', 'scripts')

MAX_TIMEOUT_SECONDS = 4800
