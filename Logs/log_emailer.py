import sys
sys.path.append('../')
from datetime import datetime, timedelta, time as t  # noqa: E402
from log_utils import send_mail  # noqa: E402
import os  # noqa: E402
from os import listdir  # noqa: E402
from os.path import isfile, join  # noqa: E402
import smtplib  # noqa: E402
import ssl  # noqa: E402
import time  # noqa: E402


class _LogEmailer:
    def __init__(self):
        self.__log_file_directory = 'LogFiles'
        self.__log_email_creds_file = 'log_email_creds.txt'
        self.__from = ''
        self.__password = ''
        self.__to = ''
        self.__smtp_server = 'smtp.gmail.com'
        self.__port = 587
        self.__email_sent = False
        self._parse_log_email_creds_file()
        self._cleanup_logs_and_send_emails()

    def _parse_log_email_creds_file(self):
        if not os.path.exists(os.getcwd() + '/' + self.__log_email_creds_file):
            raise Exception('The email credentials file must exist inside Logs/ and be named \'log_email_creds.txt\'.')
        with open(self.__log_email_creds_file) as creds_file:
            if len(creds_file.readlines()) != 3:
                raise Exception('The email credentials file must be formatted properly.')
        with open(self.__log_email_creds_file) as creds_file:
            self.__from = creds_file.readline().strip()
            self.__password = creds_file.readline().strip()
            self.__to = creds_file.readline().strip()
            with smtplib.SMTP(self.__smtp_server, self.__port) as test_server:
                try:
                    test_server.starttls(context=ssl.create_default_context())
                    test_server.login(self.__from, self.__password)
                except Exception as e:
                    raise Exception(f'The supplied credentials are invalid. {e}')

    def _cleanup_logs_and_send_emails(self):
        path = os.getcwd() + '/' + self.__log_file_directory
        while True:
            now = datetime.now()
            tomorrow = now + timedelta(days=1)
            seconds_left = (datetime.combine(tomorrow, t.min) - now).total_seconds()
            print(f"Time right now: {datetime.now().strftime('%m-%d-%Y %H:%M:%S')}.\nTime until 12 AM: {seconds_left}")
            time.sleep(seconds_left)
            files = [join(path, f) for f in listdir(path) if isfile(join(path, f)) and 'temp' in join(path, f)]
            err = send_mail(self.__from, self.__password, self.__to, self.__smtp_server, self.__port, files)
            if err:
                self.__email_sent = False
                return
            else:
                self.__email_sent = True
                for file in files:
                    with open(join(path, file), 'r+') as log_file:
                        log_file.truncate(0)


le = _LogEmailer()
