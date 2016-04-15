#!/usr/bin/env python
# -*- coding: utf-8 -*-




import email
import email.header

import dns.resolver
import logging
import smtplib

from tornado import gen
from pyisemail import is_email
from functools import reduce

logger = logging.getLogger('hedwig.nest')

class Worker:

    def brief_mail(self, msg):
        return msg.as_string()

    def decode_header(self, s):
        return reduce(lambda _,x: x[0], email.header.decode_header(s), '')

    @gen.coroutine
    def put(self, data):

        sender, recipients, msg = data

        subject = self.decode_header(msg['subject'])

        for recipient in recipients:
            if not is_email(recipient):
                logger.error('{sender} => {recipient}: "{subject}"'.format(
                    sender=sender, recipient=recipient, subject=subject))
                continue

            logger.info('{sender} => {recipient}: "{subject}"'.format(
                sender=sender, recipient=recipient, subject=subject))

            try:
                domain = recipient.split('@')[-1]
                answer = dns.resolver.query(domain, 'MX')
                server = str(answer[0].exchange)
                logger.debug('MX({recipient}) = {server}'.format(
                    recipient=recipient,
                    server=server
                ))
            except Exception as err:
                logger.error('Query MX({recipient}): {err}'.format(recipient=recipient, err=str(err)))
                continue

            try:
                mta = smtplib.SMTP(host=server, timeout=20)
                mta.sendmail(from_addr=sender, to_addrs=recipient, msg=msg.as_string())
                mta.quit()
            except smtplib.SMTPException as err:
                logger.error(
                    'SMTP Error: {sender} => {recipient}: "{subject}"\nreason: {reason}'.format(
                        sender=sender,
                        recipient=recipient,
                        subject=subject,
                        reason=str(err)
                    )
                )
                logger.debug('============\n{mail}\n============'.format(mail=self.brief_mail(msg)))
            except Exception as err:
                logger.error('System Error: {err}'.format(err=str(err)))
