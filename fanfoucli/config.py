#!/usr/bin/env python3
# coding=utf-8
# Author: John Jiang
# Date  : 2016/8/29
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from requests_oauthlib.oauth1_session import TokenRequestDenied, OAuth1Session

from . import cprint, cstring, get_input, open_in_browser

CALLBACK_REQUEST = None


class TokenHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global CALLBACK_REQUEST
        if 'callback?oauth_token=' in self.path:
            CALLBACK_REQUEST = cfg.REDIRECT_URI + self.path
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write("<h1>授权成功</h1>".encode('utf8'))
            self.wfile.write('<p>快去刷饭吧~</p>'.encode('utf8'))
        else:
            self.send_response(403)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.wfile.write('<h1>参数错误！</h1>'.encode('utf8'))


def start_token_server():
    global CALLBACK_REQUEST
    netloc = urlparse(cfg.REDIRECT_URI).netloc
    hostname, port = netloc.split(':')
    try:
        port = int(port)
    except TypeError:
        port = 80
    except ValueError:
        cprint('[x] 不合法的回调地址: %s' % cfg.REDIRECT_URI)
        sys.exit(1)
    httpd = HTTPServer((hostname, port), TokenHandler)
    sa = httpd.socket.getsockname()
    serve_message = cstring("[-] 已在本地启动HTTP服务器，等待饭否君的到来 (http://{host}:{port}/) ...", 'cyan')
    print(serve_message.format(host=sa[0], port=sa[1]))
    try:
        httpd.handle_request()
        # todo 10s后线程自动退出
        # server = threading.Thread(target=httpd.handle_request)
        # server.start()
        # server.join()

    except KeyboardInterrupt:
        print("\nKeyboard interrupt received, exiting.")
        sys.exit(0)
    httpd.server_close()

    if not CALLBACK_REQUEST:
        cprint('[x] 服务器没有收到请求', 'red')
        callback = get_input(cstring('[-] 请手动粘贴跳转后的链接>', 'cyan'))
        CALLBACK_REQUEST = callback


def auth(request_token_url, authorize_url, access_token_url, callback_uri):
    global CALLBACK_REQUEST
    session = OAuth1Session(cfg.consumer_key, cfg.consumer_secret)
    try:
        session.fetch_request_token(request_token_url)
        authorization_url = session.authorization_url(authorize_url, callback_uri=callback_uri)

        cprint('[-] 初次使用，此工具需要你的授权才能工作/_\\', 'cyan')
        if get_input(cstring('[-] 是否自动在浏览器中打开授权链接(y/n)>', 'cyan')) == 'y':
            open_in_browser(authorization_url)
        else:
            cprint('[-] 请在浏览器中打开此链接: ', 'cyan')
            print(authorization_url)

        if cfg.auto_auth:
            start_token_server()
        else:
            CALLBACK_REQUEST = get_input(cstring('[-] 请手动粘贴跳转后的链接>', 'cyan'))

        if CALLBACK_REQUEST:
            session.parse_authorization_response(CALLBACK_REQUEST)
            # requests-oauthlib换取access token时verifier是必须的，而饭否再上一步是不返回verifier的，所以必须手动设置
            access_token = session.fetch_access_token(access_token_url, verifier='123')
            cprint('[+] 授权完成，可以愉快地发饭啦！', color='green')
            return access_token
        else:
            cprint('[x] 授权失败!', 'red')
            sys.exit(1)
    except TokenRequestDenied:
        cprint('[x] 授权失败，请检查本地时间与网络时间是否同步', color='red')
        sys.exit(1)


class Config:
    _CONSUMER_KEY = 'b55d535f350dcc59c3f10e9cf43c1749'
    _CONSUMER_SECRET = 'e9d72893b188b6340ad35f15b6aa7837'
    REDIRECT_URI = 'http://localhost:8000/callback'
    REQUEST_TOKEN_URL = 'http://fanfou.com/oauth/request_token'
    AUTHORIZE_URL = 'http://fanfou.com/oauth/authorize'
    ACCESS_TOKEN_URL = 'http://fanfou.com/oauth/access_token'
    API_URL = 'http://api.fanfou.com/{}/{}.json'
    UNDEFINED_USERNAME = ''

    def __init__(self):
        self.cache_file = os.path.join(os.path.expanduser('~'), '.fancache')
        self._cache = cache = self.load()
        self._current_username = cache.setdefault('current_username', '')
        self.accounts = cache.setdefault('accounts', {})
        self.current_user = self.accounts.setdefault(self.current_username, {})
        self.consumer_key = self.current_user.setdefault('consumer_key', self._CONSUMER_KEY)
        self.consumer_secret = self.current_user.setdefault('consumer_secret', self._CONSUMER_SECRET)

        # Add custom option here
        # format: self.option_name=cache.setdefault('option_name',default_value)
        self.show_id = cache.setdefault('show_id', False)
        self.show_time_tag = cache.setdefault('show_time_tag', False)
        self.auto_clear = cache.setdefault('auto_clear', False)
        self.auto_auth = cache.setdefault('auto_auth', True)
        self.timeline_count = cache.setdefault('timeline_count', 10)

        self.dump()

    @property
    def access_token(self):
        token = self.current_user.get('access_token')
        if not token:
            token = auth(self.REQUEST_TOKEN_URL,
                         self.AUTHORIZE_URL,
                         self.ACCESS_TOKEN_URL,
                         self.REDIRECT_URI)
            self.current_user['access_token'] = token
            self.dump()
        return token

    @property
    def cookie(self):
        cookie = self.current_user.get('cookie')
        if not cookie:
            cprint('[x] Cookie不存在或已失效', 'red')
            cookie = get_input(cstring('[+] 请重新输入>', 'cyan')).strip('"')
            self.current_user['cookie'] = cookie
            self.dump()
        return cookie

    @property
    def current_username(self):
        return self._current_username

    @current_username.setter
    def current_username(self, v):
        user = self.accounts.pop(self._current_username)
        self._current_username = self._cache['current_username'] = v
        self.accounts[self._current_username] = user
        self.dump()

    def load(self):
        if os.path.isfile(self.cache_file):
            with open(self.cache_file, encoding='utf8') as f:
                cache = json.load(f)
                return cache
        return {}

    def dump(self):
        with open(self.cache_file, 'w', encoding='utf8') as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2, sort_keys=True)


cfg = Config()
