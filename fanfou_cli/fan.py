#! /usr/bin/env python3
# Author: John Jiang
# Date  : 2016/8/29

import json
import os
import sys

from fanfou_cli import config as cfg
from requests_oauthlib import OAuth1Session
from requests_oauthlib.oauth1_session import TokenMissing


# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(module)14s] [line:%(lineno)4d] [%(levelname)s] %('
#                                                 'message)s', datefmt='%Y-%m-%d %H:%M:%S')


class Fan:
    def __init__(self):
        self._session = OAuth1Session(cfg.CONSUMER_KEY, cfg.CONSUMER_SECRET)
        self._cache = {}
        try:
            if os.path.isfile(cfg.CACHE_FILE):
                with open(cfg.CACHE_FILE) as f:
                    self._cache = json.load(f)
                self._session._populate_attributes(self._cache)
            else:
                raise TokenMissing('Token not found', cfg.CACHE_FILE)
        except TokenMissing:
            self._oauth1()
            self.save_cache()

    @property
    def since_id(self):
        return self._cache.get('since_id', None)

    @since_id.setter
    def since_id(self, since_id):
        if isinstance(since_id, str) and since_id:
            self._cache['since_id'] = since_id

    def save_cache(self):
        with open(cfg.CACHE_FILE) as f:
            json.dump(self._cache, f)

    def _oauth1(self):
        fetch_response = self._session.fetch_request_token(cfg.REQUEST_TOKEN_URL)

        print('Please go here:',
              self._session.authorization_url(cfg.AUTHORIZE_URL, callback_uri='http://my.nigel.top'))
        redirect_resp = input('Paste the full redirect URL here: ').strip()

        oauth_resp = self._session.parse_authorization_response(redirect_resp)

        # requests-oauthlib换取access token时verifier是必须的，而饭否再上一步是不返回verifier的，所以必须手动设置
        oauth_tokens = self._session.fetch_access_token(cfg.ACCESS_TOKEN_URL, verifier='123')

        self._cache.update(oauth_tokens)

    def _save_timeline(self, statuses):
        # open的 mode 的说明: http://stackoverflow.com/questions/1466000/python-open-built-in-function-difference
        # -between
        # -modes-a-a-w-w-and-r
        with open('timeline.json', 'r+') as fp:
            # r.text 本来就是字符串类型, 如果使用json.dump的话, 就会保存为json中的字符串形式, 非法的字符都会被转义
            # json.dump(r.text, fp)
            old = json.load(fp)  # 这里的开销要怎么避免
            statuses.extend(old)
            # 回到文件开头
            fp.seek(0)
            # 开始覆盖地写入
            json.dump(statuses, fp)
            # Resize the stream to the given size in bytes (or the current position if size is not specified).
            fp.truncate()

    def backup(self, since_id=None, max_id=None, count=60, page=None, mode='lite'):
        """
        定时备份饭否消息

        :param since_id: since_id 指的是返回消息中的 id 属性, 是一个奇怪的字符串, 而不是raw_id(应该是饭否数据库中auto increment的主键值)
        :param max_id: 只返回消息 id 小于等于 max_id 的消息
        :param count: 1-60
        :param page: 指定返回结果的页码, 不知道怎么用
        :param str mode: default|lite 没有区别
        :return:
        """
        since_id = since_id or self.since_id
        url = cfg.API_URL.format(catagory='statuses', action='user_timeline')
        # 把 locals() 赋给 params, 则params变量也包含在locals中了
        # locals() 不可写, 后续的更改不影响已返回的值
        params = dict(since_id=since_id, max_id=max_id, count=count, page=page, mode=mode)

        statuses = []
        first = True

        while True:
            r = self._session.get(url, params=params)
            j = r.json()
            # 返回空数组时退出
            if not j:
                break
            if first:
                self.since_id = j[0].get('id', '')
                first = False

            for status in j:
                del status['user']
            # 每次获取最新的状态, 找到其中最老的id作为下一次获取时的max_id
            max_id = j[-1].get('id')
            statuses.extend(j)

            params['max_id'] = max_id

        self._save_timeline(statuses)

    def update_status(self, status):
        url = cfg.API_URL.format(catagory='statuses', action='update')
        data = {'status': status}

        r = self._session.post(url, data=data)
        if r.status_code == 200:
            return True, r.json()
        return False, r.json()