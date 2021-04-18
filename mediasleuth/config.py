# builtin
import os
import configparser

# internal
import ext.systools as systools

from mediasleuth.platform import config_directory


class MediaSleuthConfig:
    def __init__(self):
        self.config = ""
        self.read_config()

    def __dict__(self, key):
        return self.config[key]

    def read_config(self):
        """
        This tries to read a config in app data, and if it can't find one, makes one
        """
        config_filepath = os.path.join(config_directory("config"), "config.ini")
        if os.path.isfile(config_filepath):
            config = configparser.ConfigParser()
            config.read(config_filepath)
        else:
            systools.mkdir(config_directory("config"))
            systools.cp('resource\\config.ini', config_directory("config"))
            config = configparser.ConfigParser()
            config.read(config_filepath)
        self.config = config


