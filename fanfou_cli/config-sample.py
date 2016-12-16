# Author: John Jiang
# Date  : 2016/8/17
import os

CONSUMER_KEY = 'xxxx'
CONSUMER_SECRET = 'xxxx'

CACHE_FILE = os.path.join(os.path.dirname(__file__), 'cache.json')

OAUTH_URL = 'http://fanfou.com/oauth/'
REQUEST_TOKEN_URL = OAUTH_URL + 'request_token'
AUTHORIZE_URL = OAUTH_URL + 'authorize'
ACCESS_TOKEN_URL = OAUTH_URL + 'access_token'

REDIRECT_URI = 'https://my.nigel.top/callback'

API_URL = 'http://api.fanfou.com/{catagory}/{action}.json'
