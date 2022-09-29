# Firmware EngProd Tools

* fw_dut_info: Used to gather device-under-test information during firmware testing
  issue preparation (in a format expected by the firmware bug template
  referenced in the [firmware test manual](https://chromium.googlesource.com/chromiumos/docs/+/master/firmware_test_manual.md).
* fw_e2e_coverage_summarizer: Used to generate firmware coverage reports (if demonstrating sufficient value, this utility will eventually be generalized to other, non-firmware test areas).
* fw_lab_triage_helper: Used to surface information that is useful for isolating problems during triage of firmware lab test results.
* corrupt_dut_cbi: Replaces the CBI contents on a DUT with garbage. Used in conjunction with Paris CBI Repair to test breaking and fixing CBI on our lab DUTs. See go/cbi-auto-recovery-dd for full background.

Maintainers contact: cros-fw-te@google.com
