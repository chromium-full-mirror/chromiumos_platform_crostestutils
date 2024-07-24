// Copyright 2020 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package dutio

import (
	"fmt"
	"log"
	"os/exec"
	"strings"
)

const defaultSSHPort = "22"

// ExecuteRemoteCommand ssh's into the DUT, executes the provided command and
// returns the STDOUT and STDERR in string format.
//
// NOTE: executeRemoteCommand opens up a brand new SSH connection on every command
// it runs. This is much slower than maintaining an open connection, but much simpler.
// If speed of execution is ever a requirement, look here first to optimize.
func ExecuteRemoteCommand(hostname string, command string) (string, string) {
	splitHostname := strings.Split(hostname, ":")
	hostname = splitHostname[0]
	port := defaultSSHPort
	if len(splitHostname) == 2 {
		port = splitHostname[1]
	}

	cmd := exec.Command("ssh",
		"-q",                                 // Mute ssh warnings and info messages
		"-o UserKnownHostsFile=/dev/null",    // Avoid referencing any prior known hosts.
		"-o StrictHostKeyChecking=no",        // Sometimes the host keys for DUTs in our lab change. That is okay and should be ignored.
		"-o IdentityFile=~/.ssh/testing_rsa", // go/chromeos-lab-duts-ssh
		fmt.Sprintf("-p %s", port),
		fmt.Sprintf("root@%s", hostname),
		command,
	)
	var outbuf, errbuf strings.Builder
	cmd.Stdout = &outbuf
	cmd.Stderr = &errbuf
	if err := cmd.Run(); err != nil {
		log.Printf("Encountered an error when trying to run a remote command: %v", err)
		log.Printf(
			"Failed to run \"%s\" on host: %s:%s.\nStdout was: %s\nStderr was: %s",
			command,
			hostname,
			port,
			outbuf.String(),
			errbuf.String())
	}

	return outbuf.String(), errbuf.String()
}
