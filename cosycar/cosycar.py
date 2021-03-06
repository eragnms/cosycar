# -*- coding: utf-8 -*-

import argparse
import logging
import configparser

from cosycar.constants import Constants
from cosycar.car import Car
from cosycar.create_events import CreateEvent

from cosycar.zwave import Switch

# Version numbering scheme, see
# https://packaging.python.org/distributing/#choosing-a-versioning-scheme
# 1.2.0.dev1  # Development release
# 1.2.0a1     # Alpha Release
# 1.2.0b1     # Beta Release
# 1.2.0rc1    # Release Candidate
# 1.2.0       # Final Release
# 1.2.0.post1 # Post Release
__version__ = '1.2.2'


def main():
    config = configparser.ConfigParser()
    config.read(Constants.cfg_file)
    log_file = config.get('GENERAL', 'log_file')
    log_level = config.get('GENERAL', 'log_level')
    logging.basicConfig(
        filename=log_file,
        level=log_level,
        format=Constants.log_format)
    log = logging.getLogger(__name__)
    log.debug("Cosycar: {}".format(__version__))
    description_text = "Cosycar, the script that keeps your car cosy"
    parser = argparse.ArgumentParser(description=description_text)
    parser.add_argument(
        "-c",
        "--check_heaters",
        help="check if any heaters should run",
        action="store_true")
    parser.add_argument(
        "-l", "--leave_in", help="leave in LEAVE_IN minutes", type=int)
    parser.add_argument(
        "-s",
        "--leave_in_seconds",
        help="leave in LEAVE_IN_SECONDS seconds",
        type=int)
    parser.add_argument(
        "-a",
        "--leave_at",
        help="leave at the time LEAVE_AT [hh:mm]",
        type=str)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-v",
        "--version",
        help="print version information",
        action="store_true")
    group.add_argument(
        "-t", "--test", help="various tests", action="store_true")
    args = parser.parse_args()
    if args.check_heaters:
        car = Car(Constants.cfg_file)
        car.check_heaters()
    elif args.leave_in:
        new_event = CreateEvent()
        new_event.leave_in(args.leave_in)
    elif args.leave_in_seconds:
        new_event = CreateEvent()
        new_event.leave_in_seconds(args.leave_in_seconds)
    elif args.leave_at:
        new_event = CreateEvent()
        new_event.leave_at(args.leave_at)
    elif args.test:
        # Just for tests...
        switch = Switch(7)
        switch.turn_off()
    elif args.version:
        print('This is cosycar version: {}'.format(__version__))
    else:
        parser.print_usage()


if __name__ == "__main__":
    main()
