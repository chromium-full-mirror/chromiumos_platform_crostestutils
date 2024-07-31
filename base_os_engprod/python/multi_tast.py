#!/usr/bin/env python3
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script to run multiple tast instances multiple times.

This script can be used to gather multiple results from different tast runs
multiple times.
"""

import argparse
import atexit
import glob
import json
import logging
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

logger = logging.getLogger(__name__)
OUT_FILENAME = "multi_tast.out"
HELP_DESCRIPTION = """Run multiple powerhtl tasts multiple times.

Config file is json with list of following structures:
{
  "test_name": <tast name>,
  "repeats": <number of tast repeats>,
  "options": ["option1", "option2", ..., "optionN"]
}

Example config file that runs two tasts twice:
[
  {
    "test_name": "meta.PowerServodWrapper.manual",
    "repeats": 2,
    "options": ["meta.PowerServodWrapper.interval=30",
                "subtest=power.Idle.tracing_display_on_bt_on_ash",
                "servo=localhost:2201"]
  },
  {
    "test_name": "power.ChargeDischargeBattery.customization_prep",
    "repeats": 2,
    "options": ["min_charge_percent=76", "max_charge_percent=80"]
  }
]
"""


class TastRun:
    """Simple representation of tast run config"""

    def __init__(self, test_name, repeats, options):
        self.test_name = test_name
        self.repeats = repeats
        self.options = options

    def __str__(self):
        return f"{self.test_name}, {self.repeats}, {self.options}"

    def __repr__(self):
        return f"({self.test_name}, {self.repeats}, {self.options})"


def build_parser():
    """Creates input parser with correct arguments."""
    parser = argparse.ArgumentParser(
        prog="MultiTast",
        description=HELP_DESCRIPTION,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "target",
        help=(
            "The target is an SSH connection spec of the form "
            '"[user]@[host]:[port]".'
        ),
    )
    parser.add_argument("config", help="Configuration file path.")
    parser.add_argument(
        "-trace_path",
        help=(
            "Path for storing traces. If none given, it will be "
            "stored in current directory."
        ),
        default=".",
    )
    return parser


def run_tast(target, test_name, var):
    """Runs tast with specified target, test_name and additional arguments."""
    input_args = (
        ["tast", "run"] + ["-var=" + v for v in var] + [target, test_name]
    )
    logger.info("Running tasts with command: %s", " ".join(input_args))
    temp_filename = None
    with tempfile.NamedTemporaryFile(
        delete=False, mode="w", encoding="utf-8"
    ) as outfile:
        temp_filename = outfile.name
        atexit.register(remove_outfile, temp_filename)
        logger.info("Writing output to temporary file %s", temp_filename)
        subprocess.run(input_args, stdout=outfile, stderr=outfile, check=False)
    with open(OUT_FILENAME, "a+", encoding="utf-8") as outfile, open(
              temp_filename, "r", encoding="utf-8") as infile:
        outfile.write(infile.read())
    logger.info("Execution finished, processing output")
    return temp_filename


def process_output(temp_filename):
    """Processes output from tast command to get result directory."""
    with open(temp_filename, "r", encoding="utf-8") as infile:
        lines = [line.rstrip() for line in infile]
        for line in reversed(lines):
            if "Results saved to" in line:
                result_dir = line.rstrip().split(" ")[-1]
                logger.info("Found results saved in %s", result_dir)
                return result_dir
    logger.warning(
        "Could not find path to saved tast results, check %s to see tast"
        " output",
        OUT_FILENAME,
    )
    return None


def gather_results(log_path, save_dir, iteration_ident):
    """Copies tast result trace and power logs to specified directory."""
    dir_path = os.path.join(save_dir, iteration_ident)
    pathlib.Path(dir_path).mkdir(parents=True, exist_ok=True)
    result_ident = os.path.basename(os.path.normpath(log_path))

    trace_path = glob.glob(
        os.path.join(log_path, "**/*.perfetto-trace"), recursive=True
    )

    if trace_path:
        for trace in trace_path:
            trace_destination_path = os.path.join(
                dir_path, result_ident + "_" + os.path.basename(trace)
            )
            logger.info("Saving trace to %s", trace_destination_path)
            shutil.copy(trace, trace_destination_path)
    else:
        logger.warning(
            "Could not find trace, test might have failed (check logs"
            " under %s)",
            log_path,
        )

    power_paths = glob.glob(
        os.path.join(log_path, "**/power_log*"), recursive=True
    )
    for p in power_paths:
        destination_path = ""
        if "subtest_results" in p:
            subtest_path = os.path.join(dir_path, "subtest_results")
            pathlib.Path(subtest_path).mkdir(exist_ok=True)
            destination_path = os.path.join(
                subtest_path, result_ident + "_" + os.path.basename(p)
            )
        else:
            destination_path = os.path.join(
                dir_path, result_ident + "_" + os.path.basename(p)
            )
        logger.info("Saving power log to %s", destination_path)
        shutil.copy(p, destination_path)


def parse_config_file(config_path):
    """Function parses config file into individual tasts."""
    settings = []
    with open(config_path, "r", encoding="utf-8") as infile:
        try:
            data = json.load(infile)
            for setting in data:
                settings.append(TastRun(**setting))
        except json.decoder.JSONDecodeError as e:
            logger.error("Incorrect json format: %s\n\n%s", str(e),
                         HELP_DESCRIPTION)
            sys.exit(1)
        except TypeError as e:
            logger.error("Parsing failed: %s\n\n%s", str(e), HELP_DESCRIPTION)
            sys.exit(1)

    return settings


def remove_outfile(filename):
    """Removes given output file if it exists."""
    if filename:
        try:
            os.remove(filename)
        except OSError:
            pass


def main():
    """Main function."""
    logging.basicConfig(
        format="%(asctime)s %(levelname)-4s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    arg_parser = build_parser()
    args = arg_parser.parse_args()
    remove_outfile(OUT_FILENAME)
    print("=========================")
    print(
        "Hint: you may always check current tast output by looking at "
        "latest tmp file."
    )
    print("=========================")
    config_list = parse_config_file(args.config)
    for tast_idx, tast in enumerate(config_list):
        for num_loop in range(tast.repeats):
            logger.info(
                "Gathering trace for tast %s_%d iteration %d",
                tast.test_name,
                tast_idx,
                num_loop + 1,
            )
            temp_file = run_tast(args.target, tast.test_name, tast.options)
            result_path = process_output(temp_file)
            if result_path is not None:
                gather_results(
                    result_path,
                    args.trace_path,
                    f"{tast.test_name}_{tast_idx}_{num_loop+1}",
                )
            else:
                logger.info(
                    "Could not gather trace %d for tast %s, skipping this"
                    " attempt",
                    num_loop + 1,
                    tast.test_name,
                )


if __name__ == "__main__":
    main()
