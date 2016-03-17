#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncore
import smtpd
import requests
import yaml
import json
import sys
import logging

logger = logging.getLogger('mailman')


class Mailman(smtpd.SMTPServer):
    """
    继承自smtpd.SMTPServer
    用于把邮件发送请求按照 POST 请求发送到 robot.genee.cn
    """

    config = {}

    def __init__(*args, **kwargs):

        try:
            # 加载配置
            with open('config.yml', 'r') as f:
                config = yaml.load(f)
        except FileNotFoundError:
            sys.stderr.write('\nError: Unable to find config.yml\n')
            sys.exit(1)

        logger.info('config: fqdn {fqdn}, key {key}, url: {url}'.format(
            fqdn=config['fqdn'],
            key=config['key'],
            url=config['url'],
        ))

        Mailman.config = config

        # 设定 Logging
        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')

        fh = logging.FileHandler('mailman.log')
        fh.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'))

        logger.addHandler(fh)

        # 判断是否开启 Debug 默认开启
        # 如果通过 CLI 开启了 Debug 或者 config 中配置了 Debug, 那么开启 Debug 模式
        if kwargs['debug'] or config.get('debug', False):
            logger.setLevel(logging.DEBUG)
            logger.debug('Running Debug Mode')
        else:
            logger.setLevel(logging.INFO)

        # kwargs 中多余的 debug 需要进行删除
        del kwargs['debug']

        # 提示服务开启
        logger.info('Running Mailman on port 25')

        # 开启服务
        smtpd.SMTPServer.__init__(*args, **kwargs)

    # 收到邮件发送请求后, 进行邮件发送
    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):

        config = self.config

        logger.debug(
            'from: {f}, to: {t}, data: {d}'.format(
                f=mailfrom,
                t=json.dumps(rcpttos),
                d=json.dumps(data)
            )
        )

        # 尝试递送邮件到 postoffice
        try:
            r = requests.post(
                config.get('url', 'http://robot.genee.cn/'),
                data={
                    'fqdn': config['fqdn'],
                    'key': config['key'],
                    'email': json.dumps({
                        'from': mailfrom,
                        'to': rcpttos,
                        'data': data
                    })
                },
                timeout=config.get('timeout', 5)
            )

            # 不为 OK, raise exception
            if r.status_code != requests.codes.ok:
                raise requests.exceptions.RequestException

        except requests.exceptions.RequestException:
            # http://docs.python-requests.org/zh_CN/latest/user/quickstart.html
            logger.warning(
                '{url} is down'.format(
                    url=config.get('url', 'http://robot.genee.cn')
                )
            )

        return None


def main():

    debug = True if '--deubg' in sys.argv or '-d' in sys.argv else False

    mm = Mailman(('0.0.0.0', 25), None, debug=debug)

    try:
        asyncore.loop()
    except KeyboardInterrupt:
        mm.close()

if __name__ == '__main__':
    main()
