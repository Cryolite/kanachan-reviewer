#!/usr/bin/env python3

import re
import datetime
import time
import logging
import email.policy as email_policy
import email.parser as email_parser
from email.message import EmailMessage
from typing import Optional, Dict
import boto3


class YostarLogin:
    def __init__(self, email_address: str, s3_bucket_name: str, s3_key_prefix: str) -> None:
        self.__email_address = email_address
        self.__s3_bucket = boto3.resource('s3').Bucket(s3_bucket_name) # type: ignore
        self.__s3_key_prefix = s3_key_prefix

    def get_email_address(self) -> str:
        return self.__email_address

    def __get_authentication_emails(self) -> Dict[str, EmailMessage]:
        objects = self.__s3_bucket.objects.filter(Prefix=self.__s3_key_prefix)

        parser = email_parser.BytesParser(policy=email_policy.default)
        emails: Dict[str, EmailMessage] = {}
        for obj in objects:
            key = obj.key
            summary = obj.get()
            streaming_body = summary['Body']
            body = streaming_body.read()
            email: EmailMessage = parser.parsebytes(body) # type: ignore
            emails[key] = email

        return emails

    def __delete_s3_bucket_object(self, key: str) -> None:
        obj = self.__s3_bucket.Object(key)
        obj.delete()
        logging.info('Deleted the object `%s`.', key)

    def __get_auth_code(self, *, start_time: datetime.datetime) -> Optional[str]:
        emails = self.__get_authentication_emails()

        target_date = None
        target_content: Optional[str] = None

        for key, email in emails.items():
            if 'Date' not in email:
                self.__delete_s3_bucket_object(key)
                continue
            date = datetime.datetime.strptime(email['Date'], '%a, %d %b %Y %H:%M:%S %z')

            now = datetime.datetime.now(tz=datetime.timezone.utc)
            if date < now - datetime.timedelta(minutes=30):
                # Since the validity period of an authorization code is 30 minutes,
                # any email sent more than 30 minutes ago is deleted unconditionally.
                self.__delete_s3_bucket_object(key)
                continue

            if 'To' not in email:
                self.__delete_s3_bucket_object(key)
                continue
            if email['To'] != self.__email_address:
                # Emails with a different destination may be sent to other fetchers,
                # so ignore them.
                continue

            if date < start_time:
                self.__delete_s3_bucket_object(key)
                continue
            if target_date is not None and date < target_date:
                self.__delete_s3_bucket_object(key)
                continue

            if 'From' not in email:
                self.__delete_s3_bucket_object(key)
                continue
            if email['From'] != 'passport@mail.yostar.co.jp':
                self.__delete_s3_bucket_object(key)
                continue

            if 'Subject' not in email:
                self.__delete_s3_bucket_object(key)
                continue
            if email['Subject'] not in ('Eメールアドレスの確認',):
                self.__delete_s3_bucket_object(key)
                continue

            target_date = date
            body: EmailMessage = email.get_body() # type: ignore
            if body is None:
                continue
            target_content = body.get_content() # type: ignore

            self.__delete_s3_bucket_object(key)

        if target_content is None:
            return None

        match = re.search('>(\\d{6})<', target_content)
        if match is None:
            return None

        return match.group(1)

    def get_auth_code(
            self, start_time: datetime.datetime, timeout: datetime.timedelta) -> Optional[str]:
        deadline = start_time + timeout
        auth_code = None
        while datetime.datetime.now(tz=datetime.timezone.utc) < deadline:
            auth_code = self.__get_auth_code(start_time=start_time)
            if auth_code is not None:
                break
            time.sleep(1)

        return auth_code
