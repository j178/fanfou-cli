# Author: John Jiang
# Date  : 2016/8/17
import os

CONSUMER_KEY = 'b55d535f350dcc59c3f10e9cf43c1749'
CONSUMER_SECRET = 'e9d72893b188b6340ad35f15b6aa7837'

CACHE_FILE = os.path.join(os.path.expanduser('~'), '.fancache')

OAUTH_URL = 'http://fanfou.com/oauth/'
REQUEST_TOKEN_URL = OAUTH_URL + 'request_token'
AUTHORIZE_URL = OAUTH_URL + 'authorize'
ACCESS_TOKEN_URL = OAUTH_URL + 'access_token'

REDIRECT_URI = 'https://my.nigel.top/callback'

API_URL = 'http://api.fanfou.com/{}/{}.json'

