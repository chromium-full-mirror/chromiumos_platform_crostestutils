# `labtunnel`
The `labtunnel` bash script provides a CLI for commonly preformed tunneling
related commands necessary for accessing and testing with lab devices. Are you
tired of having to make ssh tunnels to DUTs so that you can run `tast`? Do you
want to remote desktop into a DUT but do not want to manage all that is
necessary to do that yourself every time? Use `labtunnel` today to do all that
and more with a simple single command!

## Configuration
The `labtunnel` command is meant to be run on the workstation that you want to
give access to lab devices to, and not inside a chroot. You can either run the
bash script, `./labtunnel.sh` directly or add it to your path. The
`./install_labtunnel.sh` bash script can be run to install it so that it may be
run as a regular command, `labtunnel`.

### install_labtunnel.sh help
```text
$ bash ~/chromiumos/src/platform/crostestutils/provingground/labtunnel/install_labtunnel.sh help
Usage: install_labtunnel.sh [options]

Options:
 --dir|-d <path>    Path to directory where labtunnel is to be installed, which
                    should be in your $PATH (default = '~/lib/depot_tools').
```

## Usage
Run `labtunnel --help` to print its usage.

## Examples
The following examples show the normal usage for each supported tunnel operation.
Once the tunneling is complete the expected behavior is that you keep the process
running until you no longer need the tunnels. Each example process is stopped by
sending SIGINT with ^C (ctr+c/cmd+c) to the terminal.

### wificell
```text
$ labtunnel wificell chromeos1-dev-host1
Creating SSH tunnel DUT: localhost:2200 -> chromeos1-dev-host1 -> localhost:22...
Creating SSH tunnel router: localhost:2201 -> chromeos1-dev-host1-router -> localhost:22...
Creating SSH tunnel pcap: localhost:2202 -> chromeos1-dev-host1-pcap -> localhost:22...
Successfully created tunnels
 DUT: localhost:2200 -> chromeos1-dev-host1 -> localhost:22
 router: localhost:2201 -> chromeos1-dev-host1-router -> localhost:22
 pcap: localhost:2202 -> chromeos1-dev-host1-pcap -> localhost:22

Example tast call (in chroot):
tast run -var=router=localhost:2201 -var=pcap=localhost:2202 localhost:2200 <test>

To shut down tunnels and sub-processes, exit this process (pid=218974) with SIGHUP, SIGINT, or SIGQUIT
^C
Closing labtunnel...
Killing child processes...
```

### callbox
```text
$ labtunnel --callbox chromeos1-donutlab-callbox1.cros callbox chromeos1-donutlab-callbox1-host1
Creating SSH tunnel DUT: localhost:2200 -> chromeos1-donutlab-callbox1-host1 -> localhost:22...
Creating SSH tunnel callboxManager: localhost:2201 -> access@chromeos1-proxy -> localhost:5000...
Creating SSH tunnel callbox: localhost:5025 -> access@chromeos1-proxy -> chromeos1-donutlab-callbox1.cros:5025...
Successfully created tunnels
 DUT: localhost:2200 -> chromeos1-donutlab-callbox1-host1 -> localhost:22
 callboxManager: localhost:2201 -> access@chromeos1-proxy -> localhost:5000
 callbox: localhost:5025 -> access@chromeos1-proxy -> chromeos1-donutlab-callbox1.cros:5025

Example tast call (in chroot):
tast run -var=callbox=chromeos1-donutlab-callbox1.cros -var=callboxManager=localhost:2201 localhost:2200 <test>

To shut down tunnels and sub-processes, exit this process (pid=219782) with SIGHUP, SIGINT, or SIGQUIT
^C
Closing labtunnel...
Killing child processes...
```

### dut
```text
$ labtunnel dut chromeos1-dev-host1
Creating SSH tunnel DUT: localhost:2200 -> chromeos1-dev-host1 -> localhost:22...
Successfully created tunnels
 DUT: localhost:2200 -> chromeos1-dev-host1 -> localhost:22

To shut down tunnels and sub-processes, exit this process (pid=220249) with SIGHUP, SIGINT, or SIGQUIT
^C
Closing labtunnel...
Killing child processes...
```

```text
$ labtunnel dut crossk-chromeos1-dev-host1
Creating SSH tunnel DUT: localhost:2200 -> chromeos1-dev-host1 -> localhost:22...
Successfully created tunnels
 DUT: localhost:2200 -> chromeos1-dev-host1 -> localhost:22

To shut down tunnels and sub-processes, exit this process (pid=220579) with SIGHUP, SIGINT, or SIGQUIT
^C
Closing labtunnel...
Killing child processes...
```

### dutvnc
```text
$ labtunnel dutvnc chromeos1-dev-host1
Creating SSH tunnel DUT_VNC: localhost:5900 -> chromeos1-dev-host1 -> localhost:5900...
Successfully created tunnels
 DUT_VNC: localhost:5900 -> chromeos1-dev-host1 -> localhost:5900
Starting kmsvnc on dut...
Running 'kmsvnc' on 'chromeos1-dev-host1' in local tmux session 'labtunnel_tmux_ssh_1646703196'...
Launching TigerVNC...

To shut down tunnels and sub-processes, exit this process (pid=221658) with SIGHUP, SIGINT, or SIGQUIT

TigerVNC Viewer 64-bit v1.11.0
Built on: 2021-04-17 08:22
Copyright (C) 1999-2020 TigerVNC Team and many others (see README.rst)
See https://www.tigervnc.org for information on TigerVNC.
^C
Closing labtunnel...
Closing tmux session 'labtunnel_tmux_ssh_1646703196'...
Killing child processes...
```

```text
$ labtunnel --do-not-open-vnc dutvnc chromeos1-dev-host1
Creating SSH tunnel DUT_VNC: localhost:5900 -> chromeos1-dev-host1 -> localhost:5900...
Successfully created tunnels
 DUT_VNC: localhost:5900 -> chromeos1-dev-host1 -> localhost:5900
Starting kmsvnc on dut...
Running 'kmsvnc' on 'chromeos1-dev-host1' in local tmux session 'labtunnel_tmux_ssh_1646703939'...
DUT VNC available at localhost:5900

To shut down tunnels and sub-processes, exit this process (pid=225379) with SIGHUP, SIGINT, or SIGQUIT
^C
Closing labtunnel...
Closing tmux session 'labtunnel_tmux_ssh_1646703939'...
Killing child processes...
```


## Debugging
The script is designed to clean itself up if something goes wrong in most cases,
though there may be a few things can still go wrong.

### Address in use from previous labtunnel call
Normally when you stop labtunnel it shuts down any tunnels it created so subsequent
can re-use ports, though if the process was killed its possible cleanup was not
preformed. To fix this, find the running ssh tunnel processes (`ps -aux | grep ssh`)
and kill them.

### TigerVNC not installed
The `dutvnc` tunnel operation uses the `xtigervncviewer` command provided by TigerVNC
to open a local VNC client to the VNC server on the DUT. You can either install this
or add the `--do-not-open-vnc` option and use your own client to connect to the
hostname labtunnel prints out for use.

If you chose to install TigerVNC and are on gLinux, you can install it like so:
```text
sudo apt install tigervnc-viewer'
```
