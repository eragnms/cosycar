# -*- coding: utf-8 -*-
import unittest
import logging
from unittest.mock import patch
import configparser
import datetime

from cosycar.constants import Constants
from cosycar.weather import CosyWeather, CosyWeatherError

CFG_FILE = 'tests/data/cosycar_template.cfg'


class WeatherTests(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(
            filename='tests/data/cosycar.log',
            level='DEBUG',
            format=Constants.log_format)
        self._config = configparser.ConfigParser()
        self._config.read(CFG_FILE)
        self._weather_interval = 10
        self._weather_file = "/tmp/test_weather_file"

    def tearDown(self):
        pass

    @patch('os.path.isfile')
    @patch('configparser.ConfigParser.options')
    @patch('configparser.ConfigParser.read')
    @patch('cosycar.weather.CosyWeather._fetch_wunder_weather')
    @patch('configparser.ConfigParser.get')
    def test_fetch_from_file(self, get_mock, fetch_mock, read_mock,
                             options_mock, is_file_mock):
        now = datetime.datetime.now()
        timestamp = now - datetime.timedelta(
            minutes=self._weather_interval - 1)
        timestamp = timestamp.strftime('%Y,%m,%d,%H,%M')
        get_mock.return_value = timestamp
        is_file_mock.return_value = True
        weather = CosyWeather("Country", "City", "mykey", self._weather_file,
                              self._weather_interval)
        weather.get_weather()
        self.assertTrue(read_mock.call_count == 2)

    @patch('cosycar.weather.CosyWeather._save_weather')
    @patch('cosycar.weather.CosyWeather._check_weather_data')
    @patch('cosycar.weather.CosyWeather._decode_deserialize')
    @patch('configparser.ConfigParser.options')
    @patch('configparser.ConfigParser.read')
    @patch('cosycar.weather.CosyWeather._fetch_wunder_weather')
    @patch('configparser.ConfigParser.get')
    def test_fetch_from_wunder(self, get_mock, fetch_mock, read_mock,
                               options_mock, decode_mock, check_mock,
                               save_mock):
        now = datetime.datetime.now()
        timestamp = now - datetime.timedelta(
            minutes=self._weather_interval + 1)
        timestamp = timestamp.strftime('%Y,%m,%d,%H,%M')
        get_mock.return_value = timestamp
        weather = CosyWeather("Country", "City", "mykey", self._weather_file,
                              self._weather_interval)
        weather_json = {'current_observation': {'temp_c': 10, 'wind_kph': 5}}
        decode_mock.return_value = weather_json
        weather.get_weather()
        self.assertTrue(fetch_mock.call_count == 1)


    @patch('os.path.isfile')
    @patch('cosycar.weather.CosyWeather._save_weather')
    @patch('cosycar.weather.CosyWeather._check_weather_data')
    @patch('cosycar.weather.CosyWeather._decode_deserialize')
    @patch('configparser.ConfigParser.options')
    @patch('configparser.ConfigParser.read')
    @patch('cosycar.weather.CosyWeather._fetch_wunder_weather')
    @patch('configparser.ConfigParser.get')
    def test_fetch_from_wunder_fail_no_file(self, get_mock, fetch_mock,
                                            read_mock, options_mock,
                                            decode_mock, check_mock,
                                            save_mock, isfile_mock,):
        isfile_mock.return_value = False
        now = datetime.datetime.now()
        timestamp = now - datetime.timedelta(
            minutes=self._weather_interval + 1)
        timestamp = timestamp.strftime('%Y,%m,%d,%H,%M')
        get_mock.return_value = timestamp
        weather = CosyWeather("Country", "City", "mykey", self._weather_file,
                              self._weather_interval)
        fetch_mock.side_effect = CosyWeatherError('Error')
        weather_data = weather.get_weather()
        all_ok = (weather_data['temperature'] == 0)
        all_ok = all_ok and (weather_data['wind_speed'] == 0)
        self.assertTrue(all_ok)

    @patch('os.path.isfile')
    @patch('cosycar.weather.CosyWeather._should_fetch_from_wunder')
    @patch('cosycar.weather.CosyWeather._fetch_wunder_weather')
    def test_json_decode_bug(self, fetch_mock, should_fetch_mock, isfile_mock):
        should_fetch_mock.return_value = True
        fetch_mock.return_value = None
        isfile_mock.return_value = False
        weather = CosyWeather("Country", "City", "mykey", self._weather_file,
                              self._weather_interval)
        weather_data = weather.get_weather()
        all_ok = (weather_data['temperature'] == 0)
        all_ok = all_ok and (weather_data['wind_speed'] == 0)
        self.assertTrue(all_ok)
    

if __name__ == '__main__':
    unittest.main()
