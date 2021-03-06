#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
To add a new test case, write a class "TestSomething" and add it to the
list "test_cases" in the function "init_test_cases".
NOTE! All times in this script is in seconds.
"""
import os
import time
import subprocess
import traceback
import signal
import re
import configparser
import shutil
import logging

HTTP_LOG_FILE = '/tmp/cosycar_http_log_file.log'
CONFIG_FILE_TEMPLATE = '.config/cosycar_template.cfg'
CONFIG_FILE = '.config/cosycar.cfg'
CONFIG_FILE_BKP = '.config/cosycar.cfg_bkp'
HTTP_PORT = 8085
# All time used in this file is in seconds, but to make things more
# readable we use minutes in instance constants of test cases and
# then convert them into seconds with SECONDS_PER_MINUTE.
# SECONDS_PER_MINUTE can be used to shorten the execution time of the
# tests. For example by setting the value to 60/30 the total execution
# time of the tests will be 30 times faster than when the "real" value
# of 60 is used.
SECONDS_PER_MINUTE = 60

log = logging.getLogger(__name__)

def init_test_cases():
    test_cases = [TestGivenTimeToLeave()]
    return test_cases


class TestGivenTimeToLeave():
    name = 'Given time to leave'
    block_heater_zwave_id = 21
    comp_heater_zwave_id = 14
    leave_in = 35 * SECONDS_PER_MINUTE
    total_time_to_run = 50 * SECONDS_PER_MINUTE
    cosycar_check_period = 2 * SECONDS_PER_MINUTE
    block_heater_expected_start_time = 5 * SECONDS_PER_MINUTE
    block_heater_expected_stop_time = 45 * SECONDS_PER_MINUTE
    comp_heater_expected_start_time = 20 * SECONDS_PER_MINUTE
    comp_heater_expected_stop_time = 45 * SECONDS_PER_MINUTE

    def __init__(self):
        block_heater = Heater(self.block_heater_zwave_id,
                              self.block_heater_expected_start_time,
                              self.block_heater_expected_stop_time)
        comp_heater = Heater(self.comp_heater_zwave_id,
                             self.comp_heater_expected_start_time,
                             self.comp_heater_expected_stop_time)
        self.heaters = [block_heater, comp_heater]

    def run(self):
        #execute = 'cosycar --leave_in_seconds {} >/dev/null 2>&1'
        execute = 'cosycar --leave_in_seconds {}'
        os.system(execute.format(int(self.leave_in)))
        log.debug("Cosycar leave in {} seconds".format(self.leave_in))
        test_engine = TestEngine(self)
        test_engine.run()


def main():
    logging.basicConfig(filename='/tmp/integration.log',
                        level='DEBUG',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log.debug("Integration started... 1")
    test_cases = init_test_cases()
    for test_case in test_cases:
        setup()
        log.debug("Setup done...")
        try:
            log.debug("Will run {}".format(test_case.name))
            test_case.run()
        except TestFailure as e:
            teardown()
            error_text = 'Test case: "{}" failed!'
            raise TestFailure(error_text.format(test_case.name)) from e
        except Exception:
            teardown()
            raise Exception(traceback.format_exc())
        teardown()

def setup():
    clean_up_files()
    install_integration_cfg_file()
    log.debug("Starting http process")
    start_http_listen_process()
    modify_cfg_file_for_testing()


def teardown():
    kill_http_listen_process()
    restore_cfg_file()
    clean_up_files()


def install_integration_cfg_file():
    home_dir = os.environ['HOME']
    cfg_file_template = os.path.join(home_dir, CONFIG_FILE_TEMPLATE)
    cfg_file_bkp = os.path.join(home_dir, CONFIG_FILE_BKP)
    cfg_file = os.path.join(home_dir, CONFIG_FILE)
    try:
        shutil.copyfile(cfg_file, cfg_file_bkp)
    except:
        pass
    shutil.copyfile(cfg_file_template, cfg_file)


def start_http_listen_process():
    cmd = ['/home/mats/.virtualenvs/cosytest/bin/python',
           'tests/reflect.py',
           '-p {}'.format(HTTP_PORT)]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,)
    SetupParams.reflect_process = process
    log.debug("Started reflect: {}".format(process))


def modify_cfg_file_for_testing():
    home_dir = os.environ['HOME']
    cfg_file = os.path.join(home_dir, CONFIG_FILE)
    config = save_current_cfg_file_settings(cfg_file)
    config['ZWAVE_CONTROLLER']['ip_address'] = 'localhost'
    config['ZWAVE_CONTROLLER']['port'] = str(HTTP_PORT)
    config['EMAIL']['check_email'] = 'False'
    with open(cfg_file, 'w') as configfile:
        config.write(configfile)


def save_current_cfg_file_settings(cfg_file):
    config = configparser.ConfigParser()
    config.read(cfg_file)
    ip_address = config['ZWAVE_CONTROLLER']['ip_address']
    port = config['ZWAVE_CONTROLLER']['port']
    use_email = config['EMAIL']['check_email']
    SetupParams.cfg_file = cfg_file
    SetupParams.ip_address = ip_address
    SetupParams.port = port
    SetupParams.use_email = use_email
    return config


def kill_http_listen_process():
    os.kill(SetupParams.reflect_process.pid, signal.SIGTERM)


def restore_cfg_file():
    config = configparser.ConfigParser()
    cfg_file = SetupParams.cfg_file
    config.read(cfg_file)
    config['ZWAVE_CONTROLLER']['ip_address'] = str(SetupParams.ip_address)
    config['ZWAVE_CONTROLLER']['port'] = str(SetupParams.port)
    config['EMAIL']['check_email'] = str(SetupParams.use_email)
    with open(cfg_file, 'w') as configfile:
        config.write(configfile)


def clean_up_files():
    try:
        os.remove(HTTP_LOG_FILE)
        home_dir = os.environ['HOME']
        cfg_file = os.path.join(home_dir, CONFIG_FILE)
        cfg_file_bkp = os.path.join(home_dir, CONFIG_FILE_BKP)
        shutil.copyfile(cfg_file_bkp, cfg_file)
    except:
        pass


class SetupParams():
    cfg_file = None
    reflect_process = None
    ip_address = None
    port = None
    use_email = None


class Heater():
    def __init__(self, zwave_id, start_time, stop_time):
        self.zwave_id = zwave_id
        self.start_time = start_time
        self.stop_time = stop_time
        self.touched = False

    def check_status(self, now, is_actually_on_now):
        log.debug("Checking heater status")
        is_expected_to_be_on = self._should_heater_be_on(now)
        current_status = self._decode_status(is_actually_on_now)
        expected_status = self._decode_status(is_expected_to_be_on)
        log.debug("{}, {}".format(current_status, expected_status))
        if current_status != expected_status:
            error_text = 'Heater with id {} is {}, but is expected to be {}'
            error_text += ', time is now {}'
            raise TestFailure(
                error_text.format(self.zwave_id, current_status,
                                  expected_status, now))

    def _decode_status(self, status):
        if status:
            return 'ON'
        else:
            return 'OFF'

    def _should_heater_be_on(self, now):
        if (now >= self.start_time) and (now < self.stop_time):
            return True
        else:
            return False


class TestEngine():
    def __init__(self, test_case):
        self._test_case = test_case

    def run(self):
        test_case_start_time = time.time()
        now = 0
        next_cosycar_check = now
        while now < self._test_case.total_time_to_run:
            if now >= next_cosycar_check:
                #os.system('cosycar --check_heaters >/dev/null 2>&1')
                os.system('cosycar --check_heaters')
                log.debug("Checking heaters...")
                self._check_heater_statuses(now)
                next_cosycar_check += self._test_case.cosycar_check_period
            now = time.time() - test_case_start_time
        self._have_heaters_been_touched(self._test_case.heaters)

    def _check_heater_statuses(self, now):
        heater_statuses = self._check_current_heater_statuses()
        for heater in self._test_case.heaters:
            try:
                heater.check_status(now, heater_statuses[heater.zwave_id])
                heater.touched = True
            except KeyError:
                pass

    def _check_current_heater_statuses(self):
        try:
            heater_statuses = {}
            with open(HTTP_LOG_FILE, 'r') as log_file:
                for line in log_file:
                    log.debug("Looking in HTTP log")
                    device_id = self._extract_device_id(line)
                    device_state = self._extract_device_state(line)
                    if device_id and device_state:
                        log_text = "Found id: {} in state: {}"
                        log.debug(log_text.format(device_id, device_state))
                        heater_statuses['device_id'] = device_state
        except (FileNotFoundError, FileExistsError):
            pass
        return heater_statuses

    def _extract_device_id(self, line):
        device_id = self._extract_info_number('DeviceNum', line)
        return device_id

    def _extract_device_state(self, line):
        target_value = self._extract_info_number('TargetValue', line)
        if target_value:
            return True
        else:
            return False

    def _extract_info_number(self, text, line):
        info_with_text = re.findall(text + '\d+', line)
        info_number = None
        if info_with_text:
            number = re.findall('\d+', str(info_with_text[0]))
            if number:
                info_number = str(number[0])
        return info_number

    def _have_heaters_been_touched(self, heaters):
        for heater in heaters:
            if not heater.touched:
                error_text = 'Heater with zwave ID {} has not been switched '
                error_text += 'during the test.'
                raise TestFailure(error_text.format(heater.zwave_id))


class TestFailure(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


if __name__ == "__main__":
    main()

