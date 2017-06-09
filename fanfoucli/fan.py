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
import getpass
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import arrow
import requests

from requests_oauthlib.oauth1_session import TokenRequestDenied, OAuth1Session
from oauthlib.oauth1 import Client as OAuth1Client
from oauthlib.oauth1.rfc5849 import utils

# patch utils.filter_params
utils.filter_oauth_params = lambda t: t

from .util import *

# Flag set when callback was called
CALLBACK_REQUEST = None


class CookieExpired(Exception):
    pass


class UnknownException(Exception):
    pass


class AuthFailed(Exception):
    pass


class OAuthTokenHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global CALLBACK_REQUEST
        if 'callback?oauth_token=' in self.path:
            CALLBACK_REQUEST = self.path
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write("<h1>授权成功</h1>".encode('utf8'))
            self.wfile.write('<p>快去刷饭吧~</p>'.encode('utf8'))
        else:
            self.send_response(403)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.wfile.write('<h1>参数错误！</h1>'.encode('utf8'))
            raise AuthFailed


def start_oauth_server(redirect_uri):
    global CALLBACK_REQUEST
    netloc = urlparse(redirect_uri).netloc
    hostname, port = netloc.split(':')
    try:
        port = int(port)
    except TypeError:
        port = 80
    except ValueError:
        cprint('[x] 不合法的回调地址: %s' % redirect_uri)
        sys.exit(1)
    httpd = HTTPServer((hostname, port), OAuthTokenHandler)
    sa = httpd.socket.getsockname()
    serve_message = cstring("[-] 已在本地启动HTTP服务器，等待饭否君的到来 (http://{host}:{port}/) ...", 'cyan')
    print(serve_message.format(host=sa[0], port=sa[1]))
    try:
        httpd.handle_request()
    except KeyboardInterrupt:
        cprint("[-] 服务器退出中...", 'cyan')
        raise AuthFailed
    httpd.server_close()

    if not CALLBACK_REQUEST:
        cprint('[x] 服务器没有收到请求', 'red')
        callback = get_input(cstring('[-] 请手动粘贴跳转后的链接>', 'cyan'))
        CALLBACK_REQUEST = callback


def api(method, category, action):
    def decorator(f):
        def wrapper(self, *args, **kwargs):
            url = self.api_url.format(category, action)
            params, data, files = f(self, *args, **kwargs)
            for failure in range(3):
                try:
                    result = self.session.request(method, url, params=params, data=data, files=files, timeout=5)
                except ValueError as e:
                    cprint(e, 'red')
                    sys.exit(1)
                except requests.RequestException:
                    pass
                else:
                    break
                time.sleep(1)
            else:
                cprint('[x] 网络请求失败', color='red')
                sys.exit(1)
            j = result.json()
            if result.status_code == 200:
                return True, j
            return False, j['error']

        return wrapper

    return decorator


class API:
    def __init__(self, cfg):
        self.cfg = cfg
        self.api_url = cfg.api_url
        self.session = OAuth1Session(self.cfg.consumer_key, self.cfg.consumer_secret)
        self.access_token = self.cfg.user.get('access_token')
        if not self.access_token:
            if self.cfg.xauth:
                self.access_token = self.xauth()
            else:
                self.access_token = self.oauth()
        self.session._populate_attributes(self.access_token)
        self.cfg.user['access_token'] = self.access_token

    def oauth(self):
        global CALLBACK_REQUEST
        try:
            self.session.fetch_request_token(self.cfg.request_token_url)
            authorization_url = self.session.authorization_url(self.cfg.authorize_url,
                                                               callback_uri=self.cfg.callback_uri)

            cprint('[-] 初次使用，此工具需要你的授权才能工作/_\\', 'cyan')
            if get_input(cstring('[-] 是否自动在浏览器中打开授权链接(y/n)>', 'cyan')) == 'y':
                open_in_browser(authorization_url)
            else:
                cprint('[-] 请在浏览器中打开此链接: ', 'cyan')
                print(authorization_url)

            if self.cfg.auto_auth:
                start_oauth_server(self.cfg.redirect_uri)
            else:
                CALLBACK_REQUEST = get_input(cstring('[-] 请手动粘贴跳转后的链接>', 'cyan'))

            if CALLBACK_REQUEST:
                try:
                    self.session.parse_authorization_response(self.cfg.redirect_uri + CALLBACK_REQUEST)
                    # requests-oauthlib换取access token时verifier是必须的，而饭否在上一步是不返回verifier的，所以必须手动设置
                    access_token = self.session.fetch_access_token(self.cfg.access_token_url, verifier='123')
                    cprint('[+] 授权完成，可以愉快地发饭啦！', color='green')
                except ValueError:
                    raise AuthFailed
                return access_token
            else:
                cprint('[x] 授权失败!', 'red')
                raise AuthFailed
        except TokenRequestDenied:
            cprint('[x] 授权失败，请检查本地时间与网络时间是否同步', color='red')
            raise AuthFailed

    def xauth(self):
        # 1. form base request args
        # 2. generate signature, add to base args
        # 3. generate Authorization header from base args

        username = get_input(cstring('[-]请输入用户名或邮箱>', 'cyan'))
        password = getpass.getpass(cstring('[-]请输入密码>', 'cyan'))
        # 这些实际上并不是url params，但是他们与其他url params一样参与签名，最终成为Authorization header的值
        args = [
            ('x_auth_username', username),
            ('x_auth_password', password),
            ('x_auth_mode', 'client_auth')
        ]

        class OAuth1ClientPatch(OAuth1Client):
            """Patch oauthlib.oauth1.Client for xauth"""

            def get_oauth_params(self, request):
                params = super().get_oauth_params(request)
                params.extend(args)
                return params

        sess = OAuth1Session(self.cfg.consumer_key, self.cfg.consumer_secret, client_class=OAuth1ClientPatch)
        access_token = sess.fetch_access_token(self.cfg.access_token_url, verifier='123')
        return access_token

    @api('GET', 'account', 'verify_credentials')
    def verify_credentials(self, **params):
        """验证用户名密码是否正确（验证当前授权是否有效）"""
        return params, None, None

    @api('GET', 'account', 'rate_limit_status')
    def rate_limit_status(self, **params):
        return params, None, None

    @api('GET', 'account', 'notification')
    def notifications(self, **params):
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

    @api('GET', 'statuses', 'mentions')
    def mentions(self, **params):
        return params, None, None

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
        """
        :param .config.Config cfg: Config Object
        """
        self.cfg = cfg
        try:
            self.api = API(cfg)
        except AuthFailed:
            cprint('[x] 授权失败！', 'red')
            sys.exit(1)
        s, me = self.api.users_show()
        if s:
            self.cfg.user['user'] = me

    def me(self):
        s, me = self.api.users_show()
        if s:
            self.display_user(me)

            s, notifications = self.api.notifications()
            notif_trans = {
                'direct_message': '私信',
                'friend_requests': '好友请求',
                'mentions': '@提到你的'
            }
            if s:
                for name, count in notifications.items():
                    if count > 0:
                        print(cstring(notif_trans[name], 'cyan'), str(count), end='   ')
            return True
            # todo
            # 显示最近的几条消息
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
        for i, status in enumerate(timeline):
            name = cstring(status['user']['name'], 'green')
            id = ('@' + cstring(status['user']['id'], 'blue')) if self.cfg.show_id else ''
            text = self.process_status_text(status['text'])
            created_at = arrow.get(status['created_at'], 'ddd MMM DD HH:mm:ss Z YYYY').humanize(locale='zh')
            photo = cstring('[图]', 'green') if ('photo' in status and not self.cfg.show_image) else ''
            truncated = cstring('$', 'magenta') if status['truncated'] else ''
            time_tag = cstring('(' + created_at + ')', 'white') if self.cfg.show_time_tag else ''
            print('[{seq}] [{name}{id}] {text} {photo} {truncated} {time_tag}'.format(
                seq=i,
                name=name,
                id=id,
                text=text,
                photo=photo,
                truncated=truncated,
                time_tag=time_tag))
            if self.cfg.show_image and photo:
                imgcat(status['imageurl'], self.cfg.image_width)

    def view(self):
        """浏览模式"""

        def get_input():
            prompt = cstring('[-] 输入命令(h显示帮助)>', 'cyan')
            try:
                key = input(prompt).strip()
                if key in ('j', 'q', 'h', 'z'):
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
                          cstring('<z>', 'cyan') + ' 刷新Timeline\n' +
                          cstring('<c 序号 xxx>', 'cyan') + ' 评论\n' +
                          cstring('<r 序号 xxx>', 'cyan') + ' 转发\n' +
                          cstring('<f 序号>', 'cyan') + ' 关注原PO\n' +
                          cstring('<u 序号>', 'cyan') + ' 取消关注\n' +
                          cstring('<q>', 'cyan') + ' 退出')
                elif command == 'z':
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
                    origin = re.sub(r'<a.*?>(.*?)</a>', r'\1', status['text'])
                    text = '{repost}{repost_style_left}@{name} {origin}{repost_style_right}'.format(
                        repost=content,
                        name=status['user']['screen_name'],
                        origin=origin,
                        repost_style_left=self.cfg.repost_style_left,
                        repost_style_right=self.cfg.repost_style_right)
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
        fp = open(filename, 'w', encoding='utf8')
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
        cookie = self.cfg.user['cookie']
        while True:
            if cookie:
                try:
                    self.api.lock(lock, cookie)
                except CookieExpired:
                    pass
                except UnknownException:
                    cprint('[x] 失败'.format('上锁' if lock else  '解锁'), 'red')
                    break
                else:
                    self.cfg.user['cookie'] = cookie
                    cprint('[-] {}成功'.format('上锁' if lock else '解锁'), 'green')
                    return True

            cprint('[x] Cookie不存在或已失效', 'red')
            cookie = get_input(cstring('[+] 请重新输入>', 'cyan')).strip('"')

    def switch_account(self):
        text = []
        for i, account in enumerate(self.cfg.accounts):
            current = ''
            if i == self.cfg.current_user:
                current = cstring('(current)', 'yellow')
            text.append('[{seq}] {name} @ {id} {current}'.format(
                seq=i,
                name=cstring(account['user']['screen_name'], 'green'),
                id=cstring(account['user']['id'], 'cyan'),
                current=current
            ))
        print('\n'.join(text))
        num = get_input(cstring('[-] 请选择账号>', 'cyan'))
        try:
            num = int(num)
            if 0 <= num < len(self.cfg.accounts):
                self.cfg.config['current_user'] = num
            else:
                raise ValueError
        except ValueError:
            cprint('[x] 切换失败', 'red')

    def login(self):
        if not self.cfg.xauth:
            cprint('[-] 即将使用OAuth验证方式，请首先在浏览器中切换到将要授权的账号', 'cyan')
            get_input(cstring('[-] 任意键继续>', 'cyan'))
        new_user_index = len(self.cfg.accounts)
        origin_user = self.cfg.current_user
        used_tokens = (a['access_token'] for a in self.cfg.accounts)

        self.cfg.config['current_user'] = new_user_index
        self.cfg.accounts.append({})
        try:
            api = API(self.cfg)
            s, me = api.users_show()
            if s:
                self.cfg.user['user'] = me
        except AuthFailed:
            cprint('[x] 授权失败！', 'red')
            return
        if api.access_token in used_tokens:
            self.cfg.accounts.pop()
            self.cfg.config['current_user'] = origin_user
