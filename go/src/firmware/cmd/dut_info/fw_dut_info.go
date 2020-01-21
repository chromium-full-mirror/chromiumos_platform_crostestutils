// Copyright 2020 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"firmware/internal/pkg/dutio"
	"fmt"
	"log"
)

func main() {
	fmt.Println("This utility is undergoing incremental development.  Please use crostestutils/provingground/firmware/dut.sh for now.")
	// TODO(kmshelton): Accept DUT hostname as an argument and expose the same functionality as
	// crostestutils/provingground/firmware/dut.sh.  This is only a temporary command to support
	// incremental development.  The functionality in dut.sh is determining properties of the
	// DUT like various firmware versions, which will be added here.
	out, err := dutio.SendSSHCommand("chromeos1-row1-rack8-host2.cros.corp.google.com", "ls")
	if err != nil {
		log.Fatalf(err.Error())
	}
	log.Print(out)
}
