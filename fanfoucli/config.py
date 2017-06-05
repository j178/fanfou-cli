#!/usr/bin/env python3
# coding=utf-8
# Author: John Jiang
# Date  : 2016/8/29
import json
import os
import atexit

DEFAULT_CONFIG = {
    'config_file': os.path.join(os.path.expanduser('~'), '.fancache'),
    'current_user': None,
    'accounts': [],
    'consumer_key': 'b55d535f350dcc59c3f10e9cf43c1749',
    'consumer_secret': 'e9d72893b188b6340ad35f15b6aa7837',
    'redirect_uri': 'http://localhost:8000/callback',
    # API related urls
    'request_token_url': 'http://fanfou.com/oauth/request_token',
    'authorize_url': 'http://fanfou.com/oauth/authorize',
    'access_token_url': 'http://fanfou.com/oauth/access_token',
    'api_url': 'http://api.fanfou.com/{}/{}.json',
    # Preferences
    'show_id': False,
    'show_time_tag': False,
    'auto_clear': False,
    'auto_auth': True,
    'timeline_count': 10,
    'show_image': True,
    'image_width': '15%'
}


class Config:
    """Maintain configurations"""

    def __init__(self):
        self.args = None  # command line arguments
        self.config = DEFAULT_CONFIG
        self.config.update(self.load())
        atexit.register(self.dump)

    def __getattr__(self, item):
        # command line arguments take precedence
        if hasattr(self.args, item):
            return getattr(self.args, item)
        return self.config.get(item)

    @property
    def user(self):
        if self.config['current_user'] is None:
            self.config['accounts'].append({})
            self.config['current_user'] = 0
        return self.config['accounts'][self.current_user]

    def load(self):
        if os.path.isfile(self.config_file):
            with open(self.config_file, encoding='utf8') as f:
                cache = json.load(f)
                return cache
        return {}

    def dump(self):
        with open(self.config_file, 'w', encoding='utf8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2, sort_keys=True)


cfg = Config()
