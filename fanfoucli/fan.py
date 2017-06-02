#!/usr/bin/env python3
# coding=utf-8
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
from http.server import BaseHTTPRequestHandler, HTTPServer

import arrow
import requests
from requests_oauthlib import OAuth1Session

from . import cstring, cprint, get_input, open_in_browser, clear_screen


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
                    cprint('[x] 网络请求失败', color='red')
                    sys.exit(1)
                time.sleep(1)
            j = result.json()
            if result.status_code == 200:
                return True, j
            return False, j['error']

        return wrapper

    return decorator


class API:
    def __init__(self, consumer_key, consumer_secret, api_url, access_token):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.api_url = api_url
        self.session = OAuth1Session(consumer_key, consumer_secret)
        self.session._populate_attributes(self.access_token)

    @api('GET', 'account', 'verify_credentials')
    def verify_credentials(self, **params):
        """验证用户名密码是否正确（验证当前授权是否有效）"""
        return params, None, None

    @api('GET', 'account', 'rate_limit_status')
    def rate_limit_stats(self, **params):
        return params, None, None

    @api('GET', 'account', 'notification')
    def account_notification(self, **params):
        """返回未读的mentions, direct message 以及关注请求数量"""
        return params, None, None

    @api('GET', 'account', 'update_profile')
    def update_profile(self, **data):
        """通过API更新用户资料
        url, location, description, name, email
        """
        return None, data, None

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
        file = {'photo': ('photo', photo_data, 'application/octet-stream'),
                'status': ('', data.get('status', ''), 'text/plain')}
        return None, None, file

    @api('GET', 'users', 'show')
    def users_show(self, **params):
        """返回好友或未设置隐私用户的信息"""
        return params, None, None

    @api('GET', 'users', 'friends')
    def users_friends(self, **params):
        """返回最近登录的好友"""
        return params, None, None

    @api('POST', 'friendships', 'create')
    def friendships_create(self, **data):
        if 'id' in data:
            return None, data, None

    @api('POST', 'friendships', 'destroy')
    def friendships_destroy(self, **data):
        if 'id' in data:
            return None, data, None

    def lock(self, lock, cookie):

        """设置：需要我批准才能查看我的消息"""
        url = 'http://fanfou.com/settings/privacy'
        sess = requests.session()
        # al 自动登录cookie，有效期一个月
        sess.cookies['al'] = cookie

        # 如果cookie失效，会返回登录页面，而不是redirect
        resp = sess.get(url)
        if '<title>登录_饭否</title>' in resp.text:
            return 'cookie_expired'

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
            return 'success'
        else:
            return 'failure'


# noinspection PyTupleAssignmentBalance
class Fan:
    def __init__(self, cfg):
        self.cfg = cfg
        self.api = API(cfg.consumer_key,
                       cfg.consumer_secret,
                       cfg.API_URL,
                       cfg.access_token)
        if self.cfg.current_username == self.cfg.UNDEFINED_USERNAME:
            s, me = self.api.users_show()
            if s:
                self.cfg.current_username = me['id']

    def me(self):
        s, me = self.api.users_show()
        if s:
            self.display_user(me)
            return True
        else:
            cprint('[x] ' + me, 'red')

    def update_status(self, status, **params):
        s, r = self.api.statuses_update(status=status, mode='lite', **params)
        if s:
            print(cstring('[-] 发布成功:', color='green'), self.process_status_text(r['text']))
            return True
        else:
            cprint('[x] 发布失败: %s' % r, color='red')

    def revert(self):
        s, latest = self.api.user_timeline(count=1)
        error = latest
        if s:
            id = latest[0]['id']
            s, info = self.api.statuses_destroy(id=id)
            if s:
                cprint('[-] 撤回成功: %s' % info['text'], color='green')
                return True
            error = info
        cprint('[x] 撤回失败: %s' % error, color='red')

    @classmethod
    def display_user(cls, user):
        screen_name = user['screen_name']
        id = user['id']
        gender = user['gender']
        location = user['location']
        description = user['description']
        url = user['url']

        created_at = arrow.get(user['created_at'], 'ddd MMM DD HH:mm:ss Z YYYY')
        created_days = (arrow.now(tz='+08:00') - created_at).days + 1
        followers_count = user['followers_count']
        friends_count = user['friends_count']
        statuses_count = user['statuses_count']
        count_per_day = math.ceil(statuses_count / created_days)

        template = ('{name} @ {id}\n' +
                    cstring('创建于: ', 'blue') + '{created_at}\n' +
                    '{gender}' +
                    cstring('位置: ', 'blue') + '{location}\n' +
                    cstring('描述: ', 'blue') + '{description}\n' +
                    cstring('主页: ', 'blue') + '{url}\n' +
                    cstring('总消息: ', 'blue') + '{statuses} (每天{count_per_day}饭)\n' +
                    cstring('关注者: ', 'blue') + '{followers}\n' +
                    cstring('正在关注: ', 'blue') + '{friends}')

        print(template.format(
            name=cstring(screen_name, 'green'),
            id=cstring(id, 'blue'),
            gender=cstring('性别: ', 'blue') + gender + '\n' if gender else '',
            location=location,
            description=description,
            url=url,
            created_at=created_at.humanize(locale='zh'),
            statuses=statuses_count,
            followers=followers_count,
            friends=friends_count,
            count_per_day=cstring(str(count_per_day), 'magenta')
        ))

    @classmethod
    def process_status_text(cls, text):
        at_re = re.compile(r'@<a.*?>(.*?)</a>', re.I)
        topic_re = re.compile(r'#<a.*?>(.*?)</a>#', re.I)
        link_re = re.compile(r'<a.*?rel="nofollow" target="_blank">(.*)</a>', re.I)
        text = at_re.sub(cstring(r'@\1', color='blue'), text)
        text = topic_re.sub(cstring(r'#\1#', color='cyan'), text)
        text = link_re.sub(cstring(r'\1', 'cyan'), text)
        return text

    def display_statuses(self, timeline):
        statuses = []

        for i, status in enumerate(timeline):
            name = cstring(status['user']['name'], 'green')
            id = ('@' + cstring(status['user']['id'], 'blue')) if self.cfg.show_id else ''
            text = self.process_status_text(status['text'])
            created_at = arrow.get(status['created_at'], 'ddd MMM DD HH:mm:ss Z YYYY').humanize(locale='zh')
            photo = cstring('[图]', 'green') if 'photo' in status else ''
            truncated = cstring('$', 'magenta') if status['truncated'] else ''
            time_tag = cstring('(' + created_at + ')', 'white') if self.cfg.show_time_tag else ''
            statuses.append(
                '[{seq}] [{name}{id}] {text} {photo} {truncated} {time_tag}'.format(
                    seq=i,
                    name=name,
                    id=id,
                    text=text,
                    photo=photo,
                    truncated=truncated,
                    time_tag=time_tag))
        print('\n'.join(statuses))

    def view(self):
        """浏览模式"""

        def get_input():
            prompt = cstring('[-] 输入命令(h显示帮助)>', 'cyan')
            try:
                key = input(prompt).strip()
                if key in ('j', 'q', 'h', 'x'):
                    return key, None, None
                else:
                    keys = key.split(' ')
                    command, number, *content = keys
                    number = int(number)
                    if not (0 <= number <= len(timeline)):
                        raise ValueError
                    content = ' '.join(content)
                    return command, number, content
            except EOFError:
                return 'q', None, None
            except ValueError:
                # cprint('[x] 输入格式有误，退出中...', 'red')
                return None, None, None

        max_id = None
        while True:
            s, timeline = self.api.home_timeline(count=self.cfg.timeline_count, max_id=max_id, format='html',
                                                 mode='lite')
            if not s:
                cprint('[x] ' + timeline, 'red')
                break
            max_id = timeline[-1]['id']
            self.display_statuses(timeline)

            while True:
                command, number, content = get_input()
                if command == 'j':
                    if self.cfg.auto_clear:
                        clear_screen()
                    break
                elif command == 'h':
                    print(cstring('<j>', 'cyan') + ' 下一页\n' +
                          cstring('<x>', 'cyan') + ' 刷新\n' +
                          cstring('<c 序号 xxx>', 'cyan') + ' 评论\n' +
                          cstring('<r 序号 xxx>', 'cyan') + ' 转发\n' +
                          cstring('<f 序号>', 'cyan') + ' 关注原PO\n' +
                          cstring('<u 序号>', 'cyan') + ' 取消关注\n' +
                          cstring('<q>', 'cyan') + ' 退出')
                elif command == 'x':
                    if self.cfg.auto_clear:
                        clear_screen()
                    max_id = None
                    break
                elif command == 'c':
                    status = timeline[number]
                    text = '@' + status['user']['screen_name'] + ' ' + content
                    reply_to_user_id = status['user']['id']
                    reply_to_status_id = status['id']
                    self.update_status(status=text, in_reply_to_user_id=reply_to_user_id,
                                       in_reply_to_status_id=reply_to_status_id, format='html')
                elif command == 'r':
                    # 去掉返回消息中的HTML标记，因为上传的时候服务器会根据@,##等标记自动生成
                    status = timeline[number]
                    text = re.sub(r'<a.*?>(.*?)</a>', r'\1', status['text'])
                    text = content + '「' + text + '」'
                    repost_status_id = status['id']
                    self.update_status(status=text, repost_status_id=repost_status_id, format='html')
                elif command == 'f':
                    # 关注原PO
                    status = timeline[number]
                    if 'repost_user_id' in status:
                        user_id = status['repost_user_id']
                        user_name = status['repost_screen_name']
                        s, r = self.api.friendships_create(id=user_id)
                        if s:
                            cprint('[-] 关注 [{}] 成功'.format(user_name), 'green')
                        else:
                            cprint('[x] ' + r, 'red')
                elif command == 'u':
                    status = timeline[number]
                    user_id = status['user']['id']
                    user_name = status['user']['screen_name']
                    s, r = self.api.friendships_destroy(id=user_id, format='html')
                    if s:
                        cprint('[-] 取消关注 [{}] 成功'.format(user_name), 'green')
                    else:
                        cprint('[x] ' + r, 'red')
                elif command == 'q':
                    sys.exit(0)
                else:
                    cprint('[x] 输入有误，请重新输入', 'red')

    def random_view(self):
        s, timeline = self.api.public_timeline(count=self.cfg.timeline_count)
        if s:
            self.display_statuses(timeline)
        else:
            cprint('[x] ' + timeline, 'red')

    def dump(self, filename):
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
            # todo 做成进度条
            logging.info('Got %s', len(statuses))

            for status in statuses:
                del status['user']
                if 'repost_status' in status:
                    del status['repost_status']['user']

            # 返回空数组时退出
            if not statuses:
                fp.write(']')
                print('备份完成！，请查看\'{}\'文件'.format(filename))
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
                resp = requests.get(url)
                resp.raise_for_status()
                if not resp.headers.get('Content-Type', '').lower().startswith('image/'):
                    cprint('[x] 提供的URL不是图片URL', 'red')
                    return False
                data = io.BytesIO(resp.content)
                s, r = self.api.photo_upload(data, status=status)
            except requests.RequestException as e:
                cprint('[x] 获取网络图片出错', 'red')
                return False
        if s:
            print(cstring('[-] 发布成功: ', 'cyan') + r['text'] + '\n' + cstring('[-] 图片地址: ', 'cyan') + r['photo']['url'])
            return True
        else:
            cprint('[x] 发布失败: %s' % r, 'red')

    def lock(self, lock):
        cookie = self.cfg.cookie
        while True:
            if cookie:
                s = self.api.lock(lock, cookie)
                if s == 'success':
                    cprint('[-] {}成功'.format('上锁' if lock else '解锁'), 'green')
                    return True
                elif s == 'cookie_expired':
                    pass
                else:
                    cprint('[x] 失败'.format('上锁' if lock else  '解锁'), 'red')
                    break

            cookie = self.cfg.cookie
