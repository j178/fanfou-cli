#!/usr/bin/env python3
# coding=utf-8
# Author: John Jiang
# Date  : 2016/8/29
import os

CONSUMER_KEY = 'b55d535f350dcc59c3f10e9cf43c1749'
CONSUMER_SECRET = 'e9d72893b188b6340ad35f15b6aa7837'

CACHE_FILE = os.path.join(os.path.expanduser('~'), '.fancache')

OAUTH_URL = 'http://fanfou.com/oauth/'
REQUEST_TOKEN_URL = OAUTH_URL + 'request_token'
AUTHORIZE_URL = OAUTH_URL + 'authorize'
ACCESS_TOKEN_URL = OAUTH_URL + 'access_token'

REDIRECT_URI = 'http://localhost:8000/callback'

API_URL = 'http://api.fanfou.com/{}/{}.json'

SHOW_ID = False
SHOW_TIME_TAG = False
AUTO_CLEAR = False
