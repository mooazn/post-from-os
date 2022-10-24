import sys
sys.path.append('../')
from datetime import datetime, timedelta, time as t  # noqa: E402
from imap_tools import MailBox  # noqa: E402
from log_utils import send_mail  # noqa: E402
import os  # noqa: E402
import smtplib  # noqa: E402
import ssl  # noqa: E402
import time  # noqa: E402


class _LogReceiver:
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
        self._parse_log_email_creds_file()
        self._read_emails_and_create_report()

    def _parse_log_email_creds_file(self):
        if not os.path.exists(os.getcwd() + '/' + self.__log_email_creds_file):
            raise Exception('The email credentials file must exist inside Logs/ and be named '
                            '\'log_receiver_creds.txt\'.')
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
        while True:
            now = datetime.now()
            tomorrow = now + timedelta(days=1)
            seconds_left = (datetime.combine(tomorrow, t(1)) - now).total_seconds()
            print(f"Time right now: {datetime.now().strftime('%m-%d-%Y %H:%M:%S')}.\nTime until 1 AM: {seconds_left}")
            time.sleep(seconds_left)
            with MailBox(self.__smtp_server).login(self.__from, self.__password) as mailbox:
                log_file_info = []
                for msg in mailbox.fetch():
                    if msg.from_ == self.__received_from:
                        num_info = 0
                        num_error = 0
                        num_fatal = 0
                        for att in msg.attachments:
                            with open(self.__temp_storage, 'wb') as f:
                                f.write(att.payload)
                            with open(self.__temp_storage, 'r') as f:
                                for line in f:
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
                                log_file_info.append([f'{msg.subject}: {att.filename}', num_info, num_error, num_fatal])
            self._write_summary_and_send_report(log_file_info)

    def _write_summary_and_send_report(self, log_report_numbers):  # very basic for now
        email_subject = f"Log Report for {(datetime.now() - timedelta(days=1)).strftime('%m/%d/%Y')}"
        email_body = 'Each array consists of [BASIC INFO, INFO_COUNT, ERROR_COUNT, FATAL_COUNT]\n\n'
        for log_report in log_report_numbers:
            email_body += str(log_report) + '\n'
        send_mail(self.__from, self.__password, self.__to, self.__smtp_server, self.__port, None, email_subject,
                  email_body)
        os.remove(self.__temp_storage)


lr = _LogReceiver()
