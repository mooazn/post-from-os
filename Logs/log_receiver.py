import sys

sys.path.append('../')
from datetime import datetime, timedelta, time as t  # noqa: E402
from imap_tools import MailBox  # noqa: E402
from logger import Logger, info, error, fatal  # noqa: E402
from log_utils import send_mail  # noqa: E402
from random import randint  # noqa: E402
import os  # noqa: E402
import smtplib  # noqa: E402
import ssl  # noqa: E402
import time  # noqa: E402


class LogReceiver:
    def __init__(self):
        self.__log_file_directory = 'LogFiles'
        self.__log_email_creds_file = 'log_receiver_creds.txt'
        self.__temp_storage = 'temp_file_location.txt'
        self.__received_from = ''
        self.__from = ''
        self.__password = ''
        self.__to = ''
        self.__smtp_server = 'smtp.gmail.com'
        self.__port = 587
        # self.LOGGER = Logger(True)
        # self.LOGGER.rename_log_file(str(randint(1000000, 9999999)) + '_log_receiver')
        self._parse_log_email_creds_file()
        self._read_emails_and_create_report()

    def _parse_log_email_creds_file(self):
        # self.LOGGER.write_log(info(), 'Inside of _parse_log_email_creds_file in _LogReceiver in _log_receiver.py')
        if not os.path.exists(os.getcwd() + '/' + self.__log_email_creds_file):
            invalid_email_credentials_file_location = 'The email credentials file must exist inside Logs/ and be ' \
                                                      'named \'log_receiver_creds.txt\'.'
            # self.LOGGER.write_log(fatal(), invalid_email_credentials_file_location)
            raise Exception(invalid_email_credentials_file_location)
        with open(self.__log_email_creds_file) as creds_file:
            if len(creds_file.readlines()) != 4:
                raise Exception('The email credentials file must be formatted properly.')
        with open(self.__log_email_creds_file) as creds_file:
            self.__received_from = creds_file.readline().strip()
            self.__from = creds_file.readline().strip()
            self.__password = creds_file.readline().strip()
            self.__to = creds_file.readline().strip()
            with smtplib.SMTP(self.__smtp_server, self.__port) as test_server:
                try:
                    test_server.starttls(context=ssl.create_default_context())
                    test_server.login(self.__from, self.__password)
                except Exception as e:
                    raise Exception(f'The supplied credentials are invalid. {e}')

    def _read_emails_and_create_report(self):  # very basic for now
        temp_files = []
        while True:
            today = datetime.now()
            tomorrow = today + timedelta(days=1)
            seconds_left = (datetime.combine(tomorrow, t(1)) - today).total_seconds()
            print(f"Time right now: {datetime.now().strftime('%m-%d-%Y %H:%M:%S')}.\nTime until 1 AM: {seconds_left}",
                  flush=True)
            with MailBox(self.__smtp_server).login(self.__from, self.__password) as mailbox:
                log_file_info = []
                for msg in mailbox.fetch():
                    if msg.from_ == self.__received_from and msg.date.day == today.day and \
                            msg.date.month == today.month and \
                            (msg.date.year == today.year or msg.date.year == today.year - 1):
                        first_word_in_subject = msg.subject.split()[0]
                        subject = first_word_in_subject[1:len(first_word_in_subject) - 5]
                        num_info = 0
                        num_error = 0
                        num_fatal = 0
                        temp_storage_file = subject + '_' + self.__temp_storage
                        temp_files.append(temp_storage_file)
                        for att in msg.attachments:
                            with open(temp_storage_file, 'wb') as f:
                                f.write(att.payload)
                            time.sleep(3)
                            with open(temp_storage_file, 'r') as f:
                                for line in f:
                                    if len(line.strip()) != 0 and line.startswith('DateTime -'):
                                        try:
                                            cur_log_split = line.split('::')
                                            # cur_log_datetime = cur_log_split[0]
                                            cur_log_logger_level = cur_log_split[1]
                                            # cur_log_logger_message = cur_log_split[2]
                                            if 'LOGGER_LEVEL_INFO' in cur_log_logger_level:
                                                num_info += 1
                                            elif 'LOGGER_LEVEL_ERROR' in cur_log_logger_level:
                                                num_error += 1
                                            elif 'LOGGER_LEVEL_FATAL' in cur_log_logger_level:
                                                num_fatal += 1
                                        except IndexError:
                                            continue
                                log_file_info.append([f'{msg.subject}: {att.filename}', num_info, num_error, num_fatal])
            self._write_summary_and_send_report(log_file_info, temp_files)
            time.sleep(seconds_left)

    def _write_summary_and_send_report(self, log_report_numbers, temp_files):  # very basic for now
        email_subject = f"Log Report for {(datetime.now() - timedelta(days=1)).strftime('%m/%d/%Y')}"
        email_body = 'Each array consists of [BASIC INFO, INFO_COUNT, ERROR_COUNT, FATAL_COUNT]\n\n'
        for log_report in log_report_numbers:
            email_body += str(log_report) + '\n'
        send_mail(self.__from, self.__password, self.__to, self.__smtp_server, self.__port, None, email_subject,
                  email_body)
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        print('Successfully sent email from log_receiver', flush=True)


lr = LogReceiver()
