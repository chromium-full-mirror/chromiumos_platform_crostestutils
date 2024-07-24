# Base OS Eng Prod Tools

**WARNING** These tools are experimental, largely untested, and to be used only for exploratory testing, debugging and prototyping efforts. The [Base OS Eng Prod](go/cros-bosep) team makes no guarantee as to the reliability and functionality of these tools. If you wish to seriously use one of these tools, we highly recommend you reach out to us first at cros-base-os-ep@google.com

* dut_info: Takes in the hostname of a DUT (or IP address of a local DUT) and prints to the console information about its hardware and firmware components, such as Model, Memory size, CPU Architecture, EC Version, and more.
* fw_e2e_coverage_summarizer: Used to generate firmware coverage reports (if demonstrating sufficient value, this utility will eventually be generalized to other, non-firmware test areas).
* fw_lab_triage_helper: Used to surface information that is useful for isolating problems during triage of firmware lab test results.
* corrupt_dut_cbi: Replaces the CBI contents on a DUT with garbage. Used in conjunction with Paris CBI Repair to test breaking and fixing CBI on our lab DUTs. See go/cbi-auto-recovery-dd for full background.
