#!/usr/bin/env python

import yaml
import pyspeedtest
import datetime
from time import sleep
from twython import Twython
from multiprocessing import Process, Queue

class ConfigError(Exception):
    def __init__(self, msg = None):
        if not msg:
            self.message = 'Could not get configuration values. Fill out config.yaml'
        else:
            self.message = msg

class SpeedQuality(object):
    def __init__(self):
        try:
            with open('config.yaml', 'r') as fptr:
                configs = yaml.load(fptr.read())
            self.paid_up = configs['Speed']['paid']['up']
            self.paid_down = configs['Speed']['paid']['down']
            self.angry_up = configs['Speed']['angry']['up']
            self.angry_down = configs['Speed']['angry']['down']
        except:
            raise ConfigError

        for i in [self.paid_up, self.paid_down, self.angry_up, self.angry_down]:
            try:
                assert isinstance(i, float)
            except:
                try:
                    i = float(i)
                except:
                    msg = 'Cannot parse SpeedQuality config value: "{}"'.format(i)
                    raise ConfigError(msg)

        self.actual_up_str = ''
        self.actual_up = 0.0
        self.actual_down_str = ''
        self.actual_down = 0.0
        self.speedtest = pyspeedtest.SpeedTest()


    def judge(self):
        self.__get_up__()
        self.__get_down__()
        do_complain = False
        if self.actual_up < self.paid_up and self.actual_up < self.angry_up:
            do_complain = True
        if self.actual_down < self.paid_down and self.actual_down < self.angry_down:
            do_complain = True
        if do_complain:
            msg = "{down_str}mb/{up_str}mb but I'm paying for {paid_down}mb/{paid_up}mb"
            msg = msg.format(down_str = self.actual_down,
                             up_str = self.actual_up,
                             paid_down = self.paid_down,
                             paid_up = self.paid_up)
            return msg

    def __get_up__(self):
        self.actual_up_str = pyspeedtest.pretty_speed(self.speedtest.upload())
        self.actual_up, _ = self.actual_up_str.split()
        self.actual_up = int(round(float(self.actual_up)))

    def __get_down__(self):
        self.actual_down_str = pyspeedtest.pretty_speed(self.speedtest.download())
        self.actual_down, _ = self.actual_down_str.split()
        self.actual_down = int(round(float(self.actual_down)))

    def get_speeds(self):
        return self.actual_down_str, self.actual_up_str

class Tester(object):
    def __init__(self):
        try:
            with open('config.yaml', 'r') as fptr:
                configs = yaml.load(fptr.read())
            c_key = configs['Twython']['consumer']['key']
            c_secret = configs['Twython']['consumer']['secret']
            a_key = configs['Twython']['access']['key']
            a_secret = configs['Twython']['access']['secret']
            self.location = configs['location']
            self.sleep = configs['timer'] # assuming seconds for now
        except:
            raise ConfigError
        self.twitter = Twython(c_key, c_secret, a_key, a_secret)
        self.msg_format = 'Hey @Comcast, why is my internet speed {} in {}? @ComcastCares @xfinity #comcast #speedtest'
        self.quality = SpeedQuality()

    def run(self):
        while True:
            complain = self.quality.judge()
            if complain:
                msg = self.msg_format.format(complain, self.location)
                print msg
                print 'len(msg): {}'.format(len(msg))
                self.twitter.update_status(status = msg)
            else:
                print 'Speeds are acceptable: {}'.format(self.quality.get_speeds())
            sleep(self.sleep)
