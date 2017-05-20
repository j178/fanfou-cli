#! /usr/bin/env python3
# Author: John Jiang
# Date  : 2016/8/29
import io
import json
import logging
import math
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta

import requests
from requests_oauthlib import OAuth1Session

from . import config as cfg


def api(method, category, action):
    def decorator(f):
        def wrapper(self, *args, **kwargs):
            url = self.api_url.format(category, action)
            params, data, files = f(self, *args, **kwargs)
            failure = 0
            while True:
                try:
                    result = self.session.request(method, url, params=params, data=data, files=files, timeout=5)
                except ValueError as e:
                    print(e)
                    sys.exit(1)
                except requests.RequestException:
                    failure += 1
                else:
                    break
                if failure >= 3:
                    print('网络请求失败')
                    sys.exit(1)
            j = result.json()
            if result.status_code == 200:
                return True, j
            return False, j['error']

        return wrapper

    return decorator


class API:
    def __init__(self, consumer_key, consumer_secret, access_token=None, **urls):
        self.api_url = urls.pop('api_url')
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.session = OAuth1Session(consumer_key, consumer_secret)
        self.access_token = access_token or self.auth(**urls)
        self.session._populate_attributes(self.access_token)

    def auth(self, request_token_url, authorize_url, access_token_url, callback_uri):
        self.session.fetch_request_token(request_token_url)
        authorization_url = self.session.authorization_url(authorize_url, callback_uri=callback_uri)
        print('请在浏览器中打开此网址:', authorization_url)
        redirect_resp = input('请将跳转后的网站粘贴到这里: ').strip()
        self.session.parse_authorization_response(redirect_resp)
        # requests-oauthlib换取access token时verifier是必须的，而饭否再上一步是不返回verifier的，所以必须手动设置
        access_token = self.session.fetch_access_token(access_token_url, verifier='123')
        print('授权完成，可以愉快地发饭啦！')
        return access_token

    @api('GET', 'account', 'verify_credentials')
    def verify_credentials(self, **params):
        """验证用户名密码是否正确（验证当前授权是否有效）"""
        return params, None, None

    @api('GET', 'account', 'rate_limit_status')
    def rate_limit_stats(self, **params):
        return params, None, None

    @api('GET', 'account', 'update_profile')
    def update_profile(self, **data):
        """通过API更新用户资料
        url, location, description, name, email
        """
        return None, data, None

    @api('GET', 'account', 'notification')
    def notification(self, **params):
        """返回未读的mentions, direct message 以及关注请求数量"""
        return params, None, None

    @api('POST', 'statuses', 'update')
    def statuses_update(self, **data):
        """发布一条状态"""
        if 'status' in data:
            return None, data, None

    @api('POST', 'statuses', 'destroy')
    def statuses_destroy(self, **data):
        """删除一条状态"""
        return None, data, None

    @api('GET', 'statuses', 'home_timeline')
    def home_timeline(self, **params):
        """获取指定用户的时间线(用户及其关注好友的状态)，该用户为当前登录用户或者未设置隐私"""
        return params, None, None

    @api('GET', 'statuses', 'user_timeline')
    def user_timeline(self, **params):
        """获取某个用户已发送的状态"""
        return params, None, None

    @api('GET', 'statuses', 'public_timeline')
    def public_timeline(self, **params):
        """显示20条随便看看的消息(未设置隐私用户的消息)"""
        return params, None, None

    @api('POST', 'photos', 'upload')
    def photo_upload(self, photo_data, **data):
        """发布带图片状态"""
        # {name : (filename, filedata, content_type, {headers})}
        file = {'photo': ('photo-from-fanfou-cli.png', photo_data)}
        return None, data, file

    @api('GET', 'users', 'show')
    def users_show(self, **params):
        """返回好友或未设置隐私用户的信息"""
        return params, None, None

    @api('GET', 'users', 'friends')
    def users_friends(self, **params):
        """返回最近登录的好友"""
        return params, None, None

    def protect(self, lock, cookie):

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
            'action': 'settings.privacy',
            'token': token
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
            with open(cfg.CACHE_FILE, encoding='utf8') as f:
                return json.load(f)

    def save_cache(self):
        with open(cfg.CACHE_FILE, 'w', encoding='utf8') as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2, sort_keys=True)

    def me(self):
        s, me = self.api.users_show()
        if s:
            self._cache['my_latest_status'] = me.pop('status')
            self._cache['me'] = me
            self.save_cache()

            self.display_user(me)

    def update_status(self, status):
        s, r = self.api.statuses_update(status=status)
        if s:
            self._cache['me'] = r.pop('user')
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
    def display_user(user):
        screen_name = user['screen_name']
        id = user['id']
        gender = user['gender']
        location = user['location']
        description = user['description']
        url = user['url']

        created_at = datetime.strptime(user['created_at'], '%a %b %d %H:%M:%S %z %Y')
        now = datetime.now(tz=timezone(timedelta(hours=8)))
        created_days = (now - created_at).days
        followers_count = user['followers_count']
        friends_count = user['friends_count']
        statuses_count = user['statuses_count']
        count_per_day = math.ceil(statuses_count / created_days)

        template = ('{name} @{id}\n'
                    '创建于 {created_at}\n'
                    '{gender}'
                    '位置: {location}\n'
                    '描述: {description}\n'
                    '主页: {url}\n'
                    '总消息: {statuses} (每天{count_per_day}条)\n'
                    '关注者: {followers}\n'
                    '正在关注: {friends}')

        print(template.format(name=screen_name, id=id,
                              gender='性别: ' + gender + '\n' if gender else '',
                              location=location,
                              description=description,
                              url=url,
                              created_at=created_at.strftime('%x %X'),
                              statuses=statuses_count,
                              followers=followers_count,
                              friends=friends_count,
                              count_per_day=count_per_day
                              ))

    @staticmethod
    def display_statuses(statuses):
        text = []
        for i, status in enumerate(statuses, start=1):
            photo = '[图片]' if 'photo' in status else ''
            truncated = '$' if status['truncated'] else ''

            text.append('[{:2}] [{}] @{}: {} {} {}'.format(i,
                                                           status['user']['name'],
                                                           status['user']['id'],
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

    def save_all_statuses(self, filename):
        """
        备份全部饭否消息

         since_id: since_id 指的是返回消息中的 id 属性, 是一个奇怪的字符串, 而不是raw_id(应该是饭否数据库中auto increment的主键值)
         max_id: 只返回消息 id 小于等于 max_id 的消息
         count: 1-60
         page: 指定返回结果的页码, 不知道怎么用
         mode: default|lite 没有区别
        """

        def save(fp, statuses):

            # open的 mode 的说明: http://stackoverflow.com/questions/1466000/python-open-built-in-function-difference
            # -between
            # -modes-a-a-w-w-and-r

            # r.text 本来就是字符串类型, 如果使用json.dump的话, 就会保存为json中的字符串形式, 非法的字符都会被转义
            # json.dump(r.text, fp)
            # old = json.load(fp)  # 这里的开销要怎么避免
            # statuses.extend(old)
            # # 回到文件开头
            # fp.seek(0)
            # # 开始覆盖地写入
            # json.dump(statuses, fp, ensure_ascii=False, indent=2)
            # # Resize the stream to the given size in bytes (or the current position if size is not specified).
            # fp.truncate()

            text = json.dumps(statuses, ensure_ascii=False, indent=2, sort_keys=True)
            start = text.index('[') + 1
            end = text.rindex(']')
            fp.write(text[start:end])

        max_id = None
        fp = open(filename, 'a+', encoding='utf8')
        fp.write('[')

        first = True
        while True:
            s, statuses = self.api.user_timeline(max_id=max_id, count=60, mode='lite')
            if not s:
                logging.error(statuses)
                break
            logging.info('Got %s', len(statuses))

            for status in statuses:
                del status['user']
                if 'repost_status' in status:
                    del status['repost_status']['user']

            # 返回空数组时退出
            if not statuses:
                fp.write(']')
                break
            elif not first:
                fp.write(',')

            first = False
            save(fp, statuses)

            # 每次获取最新的状态, 找到其中最老的id作为下一次获取时的max_id
            max_id = statuses[-1]['id']
            time.sleep(1)
        fp.close()

    def upload_photos(self, status, image):
        if os.path.isfile(image):
            with open(image, 'rb') as f:
                s, r = self.api.photo_upload(f, status=status)
        else:
            try:
                url = image.strip('\'').strip('"')
                data = io.BytesIO(requests.get(url).content)
                s, r = self.api.photo_upload(data, status=status)
            except requests.RequestException as e:
                print('获取网络图片出错')
                return
        if s:
            print('发布成功: {}\n图片地址: {}'.format(r['text'], r['photo']['url']))
        else:
            print('发布失败: ', r)
