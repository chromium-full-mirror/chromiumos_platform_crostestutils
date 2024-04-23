# Tools For Measuring Boot Time Performance

Scripts in this directory serve as the wrapper of the tast test
`platform.BootPerf` for developers or partners to verify that a device meets
Chrome OS boot time performance requirements. The wrapper is required to make it
as simple as possible to run the test and display the test results. This
directory contains the following tools:

* `bootperf` runs the test to measure boot time performance of a Chrome OS
  device and stores the test results in the current directory.
* `showbootdata` parses and displays the boot time performance data from
  previous runs of `bootperf`.

See [the document](https://www.chromium.org/chromium-os/developer-library/guides/performance/measuring-boot-time-performance/)
for detailed usage information.
