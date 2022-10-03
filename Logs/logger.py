import atexit
from datetime import datetime
from enum import Enum
import os
from os import listdir
from os.path import isfile, join
from random import randint
import shutil
import signal


class LoggerLevels(Enum):
    INFO = 'LOGGER_LEVEL_INFO'
    WARN = 'LOGGER_LEVEL_WARN'
    ERROR = 'LOGGER_LEVEL_ERROR'
    FATAL = 'LOGGER_LEVEL_FATAL'


def info():
    return LoggerLevels.INFO.value


def warn():
    return LoggerLevels.WARN.value


def error():
    return LoggerLevels.ERROR.value


def fatal():
    return LoggerLevels.FATAL.value


class Logger:
    def __init__(self):
        signal.signal(signal.SIGINT, self._handler)
        signal.signal(signal.SIGTERM, self._handler)
        atexit.register(self._exit_at_close)
        self.__logs_directory = '../Logs'
        self.__log_file_directory = 'LogFiles'
        self.__log_ending = '_log_file.txt'
        self.__log_ending_old = '_old_log_file.txt'
        self.__log_ending_temp = '_temp_log_file.txt'
        self.__log_file_name = ''
        self.__log_file_short_name = ''
        self._init_log_file()
        self.__file = self._open_log_file()
        self.write_log(info(), 'Successfully created log file!')

    def _init_log_file(self):
        cur_dir = os.getcwd()
        os.chdir(self.__logs_directory)
        files = []
        for file in listdir(self.__log_file_directory):
            cur_file = join(self.__log_file_directory, file)
            if isfile(cur_file) and cur_file.endswith(self.__log_ending):
                files.append(file)
        os.chdir(cur_dir)
        valid_digits = []
        try:
            for file_name in files:
                digit = file_name.split(self.__log_ending)[0]
                int(digit)
                valid_digits.append(digit)
        except ValueError:
            pass
        rand_int = randint(1000000, 9999999)
        while rand_int in valid_digits:
            rand_int = randint(1000000, 9999999)
        self.__log_file_name += str(rand_int) + self.__log_ending_temp
        self.__log_file_short_name = str(rand_int)

    def file_name(self):
        return self.__log_file_name

    def _open_log_file(self):
        cur_dir = os.getcwd()
        os.chdir(self.__logs_directory)
        log_file_path = self.__log_file_directory + '/' + self.__log_file_name
        try:
            with open(log_file_path, 'a'):  # testing to see if file name is valid
                pass
        except FileNotFoundError:  # ignore this because duplicate errors in console
            pass
        except OSError:
            raise Exception(f'Error writing to {self.__log_file_name}')
        file = open(log_file_path, 'a')
        os.chdir(cur_dir)
        return file

    def _close_log_file(self):
        self.__file.close()

    def is_open(self):
        return not self.__file.closed

    def _handler(self, *args):
        _ = args  # unused, just wanted to get rid of the annoying message. required for handler method header
        self._close_log_file()
        self._change_file_state(self.__log_file_short_name)
        exit(1)

    def _exit_at_close(self):
        try:
            if type(self.__file) != str and self.is_open():
                self._close_log_file()
                self._change_file_state(self.__log_file_short_name)
        except AttributeError:
            pass

    def _change_file_state(self, to_name):
        cur_dir = os.getcwd()
        os.chdir(self.__logs_directory + '/' + self.__log_file_directory)
        current_log_file_exists = False
        if os.path.exists(to_name + self.__log_ending):  # if current log file exists
            current_log_file_exists = True  # change the flag
            shutil.copyfile(to_name + self.__log_ending, to_name + self.__log_ending_old)  # copy current log file to
            # old log file so that we save the previous log file
        shutil.copyfile(to_name + self.__log_ending_temp, to_name + self.__log_ending)  # copy the temp log file to
        # current log file, saving that as the new log file
        os.remove(to_name + self.__log_ending_temp)  # remove the temp log file, no more use for it
        if os.path.exists(to_name + self.__log_ending_old) and current_log_file_exists:  # if the old log file exists
            # and the current log file also exists, add an extra line to the end of the old log file to signify
            # that it won't be written to anymore
            with open(to_name + self.__log_ending_old, 'a') as old_file:
                old_file.write('!!!Changing the state of this log file. New logs will no longer be written!!!')
        os.chdir(cur_dir)

    def write_log(self, logger_level: LoggerLevels, logger_message: str):
        if self.is_open():
            date_and_time = datetime.now().strftime("%m-%d-%Y %H:%M:%S")
            self.__file.write(f'DateTime - [{date_and_time}] :: LoggerLevel - {logger_level} :: LoggerMessage - '
                              f'{logger_message}\n')

    def rename_log_file(self, to_name):
        self.write_log(info(), 'Renaming the log file...')
        cur_dir = os.getcwd()
        os.chdir(self.__logs_directory + '/' + self.__log_file_directory)
        new_file_name = to_name + self.__log_ending_temp
        os.rename(self.__log_file_name, new_file_name)
        os.chdir(cur_dir)
        self.__log_file_name = new_file_name
        self.__log_file_short_name = to_name
        self.write_log(info(), 'Renamed the log file successfully.')
