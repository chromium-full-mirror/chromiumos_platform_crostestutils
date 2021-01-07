# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

BOOTPERF_WRAPPER = /mnt/host/source/src/platform/crostestutils/bootperf-wrapper

all: test_scripts

test_scripts:
	@echo "Preparing test scripts."

install:
	mkdir -p "${DESTDIR}/usr/bin"
	install -m 0755 cros_run_bvt "${DESTDIR}/usr/bin"
	install -m 0755 test_that ${DESTDIR}/usr/bin
	ln -sfT "${BOOTPERF_WRAPPER}" "${DESTDIR}/usr/bin/bootperf"
	ln -sfT "${BOOTPERF_WRAPPER}" "${DESTDIR}/usr/bin/showbootdata"
