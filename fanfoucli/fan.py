#! /usr/bin/env python3
# Author: John Jiang
# Date  : 2016/8/29

import json
import logging
import os
import re

import requests
from requests_oauthlib import OAuth1Session

from . import config as cfg

level = logging.WARN
logging.basicConfig(level=level,
                    format='%(asctime)s [%(module)14s] [line:%(lineno)4d] [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


def api(category, action):
    def decorator(f):
        def wrapper(self, *args, **kwargs):
            url = self.api_url.format(category, action)
            result = f(self, url, *args, **kwargs)
            j = result.json()
            if result.status_code == 200:
                return True, j
            return False, j['error']

        return wrapper

    return decorator


class API:
    def __init__(self, consumer_key, consumer_secret, access_token=None, **urls):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.session = OAuth1Session(consumer_key, consumer_secret)
        self.access_token = access_token or self.auth(**urls)
        self.session._populate_attributes(self.access_token)
        self.api_url = urls['api_url']

    def auth(self, request_token_url, authorize_url, access_token_url, callback_uri):
        self.session.fetch_request_token(request_token_url)
        authorization_url = self.session.authorization_url(authorize_url, callback_uri=callback_uri)
        print('Please go here:', authorization_url)
        redirect_resp = input('Paste the full redirect URL here: ').strip()
        self.session.parse_authorization_response(redirect_resp)
        # requests-oauthlib换取access token时verifier是必须的，而饭否再上一步是不返回verifier的，所以必须手动设置
        access_token = self.session.fetch_access_token(access_token_url, verifier='123')
        return access_token

    @api('account', 'verify_credentials')
    def verify_credentials(self, url, **params):
        """验证用户名密码是否正确（验证当前授权是否有效）"""
        return self.session.get(url, params=params)

    @api('account', 'rate_limit_status')
    def rate_limit_stats(self, url, **params):
        return self.session.get(url, params=params)

    @api('account', 'update_profile')
    def update_profile(self, url, **data):
        """通过API更新用户资料
        url, location, description, name, email
        """
        return self.session.post(url, data=data)

    @api('account', 'notification')
    def notification(self, url, **params):
        """返回未读的mentions, direct message 以及关注请求数量"""
        return self.session.get(url, params=params)

    @api('statuses', 'update')
    def statuses_update(self, url, **data):
        """发布一条状态"""
        if 'status' in data:
            return self.session.post(url, data=data)

    @api('statuses', 'destroy')
    def statuses_destroy(self, url, **data):
        """删除一条状态"""
        return self.session.post(url, data=data)

    @api('statuses', 'home_timeline')
    def home_timeline(self, url, **params):
        """获取指定用户的时间线(用户及其关注好友的状态)，该用户为当前登录用户或者未设置隐私"""
        return self.session.get(url, params=params)

    @api('statuses', 'user_timeline')
    def user_timeline(self, url, **params):
        """获取某个用户已发送的状态"""
        return self.session.get(url, params=params)

    @api('statuses', 'public_timeline')
    def public_timeline(self, url, **params):
        """显示20条随便看看的消息(未设置隐私用户的消息)"""
        return self.session.get(url, params=params)

    @api('photo', 'upload')
    def photo_upload(self, url, photo_path, **data):
        """发布带图片状态"""
        filename = os.path.basename(photo_path)
        # {name : (filename, filedata, content_type, {headers})}
        file = {'photo': (filename, open(photo_path, 'rb'))}
        return self.session.post(url, data=data, files=file)
        # print(json.dumps(r.json(), ensure_ascii=False, indent=2, sort_keys=True))

    @api('users', 'show')
    def users_show(self, url, **params):
        """返回好友或未设置隐私用户的信息"""
        return self.session.get(url, params=params)

    @api('users', 'friends')
    def users_friends(self):
        """返回最近登录的好友"""

    def set_privacy(self, lock, cookie):
        """设置：需要我批准才能查看我的消息"""
        url = 'http://fanfou.com/settings/privacy'
        sess = requests.session()
        # al 自动登录cookie，有效期一个月
        sess.cookies['al'] = cookie

        # 如果cookie失效，会返回登录页面，而不是redirect
        resp = sess.get(url)
        if '<title>登录_饭否</title>' in resp.text:
            print('设置失败：Cookie 已失效')
            return

        token = re.search(r'<input type="hidden" name="token" value="(.+?)"', resp.text).group(1)
        data = {
            'attrfindme': 'On',
            'action'    : 'settings.privacy',
            'token'     : token
        }
        if lock:
            data['status'] = 'On'

        resp = sess.post(url, data=data, allow_redirects=False)
        if resp.status_code == 302:
            print('设置成功')
        else:
            print('设置失败')


class Fan:
    def __init__(self):
        self._cache = self.load_cache(cfg.CACHE_FILE) or {}

        access_token = self._cache.get('access_token')
        self.api = API(cfg.CONSUMER_KEY, cfg.CONSUMER_SECRET, access_token,
                       request_token_url=cfg.REQUEST_TOKEN_URL,
                       authorize_url=cfg.AUTHORIZE_URL,
                       access_token_url=cfg.ACCESS_TOKEN_URL,
                       callback_uri='http://u.nigel.top',
                       api_url=cfg.API_URL)
        self._cache['access_token'] = self.api.access_token
        self.save_cache()

    @staticmethod
    def load_cache(cache_file):
        if os.path.isfile(cache_file):
            with open(cfg.CACHE_FILE) as f:
                return json.load(f)

    def save_cache(self):
        with open(cfg.CACHE_FILE, 'w') as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2, sort_keys=True)

    @property
    def since_id(self):
        return self._cache.get('since_id', None)

    @since_id.setter
    def since_id(self, since_id):
        self._cache['since_id'] = since_id

    def me(self):
        s, me = self.api.users_show()
        if s:
            self._cache['my_latest_status'] = me['status']
            del me['status']
            self._cache['me'] = me
            self.save_cache()

        return json.dumps(me, ensure_ascii=False, indent=2, sort_keys=True)

    def update_status(self, status):
        s, r = self.api.statuses_update(status=status)
        if s:
            self._cache['me'] = r['user']
            del r['user']
            self._cache['my_latest_status'] = r
            self.save_cache()
            print('发布成功: ', r['text'])
        else:
            print('发布失败: ', r)

    def revert(self):
        s, latest = self.api.user_timeline(count=1)
        error = latest
        if s:
            id = latest[0]['id']
            s, info = self.api.statuses_destroy(id=id)
            self._cache['me'] = info['user']
            self.save_cache()
            if s:
                print('撤回成功: ', info['text'])
                return
            error = info
        print('撤回失败:', error)

    @staticmethod
    def display_statuses(statuses):
        text = []
        for i, status in enumerate(statuses, start=1):
            photo = '[图片]' if 'photo' in status else ''
            truncated = '$' if status['truncated'] else ''

            text.append('[{:2}] [{}]: {} {} {}'.format(i,
                                                       status['user']['name'],
                                                       status['text'],
                                                       photo,
                                                       truncated))
        print('\n'.join(text))

    def view(self):
        """浏览模式"""
        max_id = None
        while True:
            s, timeline = self.api.home_timeline(count=10, max_id=max_id)
            if not s:
                print(s)
                break
            max_id = timeline[-1]['id']
            self.display_statuses(timeline)

            key = input('Enter <j> to next page, any other key to exit >').strip()
            if key != 'j':
                break

    def random_view(self):
        s, timeline = self.api.public_timeline(count=20)
        if s:
            self.display_statuses(timeline)
        else:
            print(timeline)

    def save_all_statuses(self, since_id=None, max_id=None, count=60, page=None, mode='lite'):
        """
        定时备份饭否消息

        :param since_id: since_id 指的是返回消息中的 id 属性, 是一个奇怪的字符串, 而不是raw_id(应该是饭否数据库中auto increment的主键值)
        :param max_id: 只返回消息 id 小于等于 max_id 的消息
        :param count: 1-60
        :param page: 指定返回结果的页码, 不知道怎么用
        :param str mode: default|lite 没有区别
        """

        def save_timeline(statuses):
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

        since_id = since_id or self.since_id
        params = dict(since_id=since_id, max_id=max_id, count=count, page=page, mode=mode)

        statuses = []
        first = True

        while True:
            r = self.api.user_timeline(params=params)
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

        save_timeline(statuses)
