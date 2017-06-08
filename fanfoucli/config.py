#!/usr/bin/env python3
# coding=utf-8
# Author: John Jiang
# Date  : 2016/8/29
import json
import os
import atexit
from .util import cprint, cstring, get_input

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
    'preferences': {'show_id': False,
                    'show_time_tag': False,
                    'auto_clear': False,
                    'auto_auth': True,
                    'timeline_count': 10,
                    'show_image': False,
                    'image_width': '15%',
                    'xauth': False,
                    'quote_repost': True
                    }
}


class Config:
    """Maintain configurations"""

    def __init__(self):
        self.args = None  # command line arguments
        self.config = DEFAULT_CONFIG
        cache = self.load()
        # update only configs defined in default configs
        self.config.update((k, cache[k]) for k in self.config.keys() & cache.keys())

        atexit.register(self.dump)

    def __getattr__(self, item):
        # command line arguments take precedence
        if getattr(self.args, item, None) is not None:
            return getattr(self.args, item)
        if self.config.get(item) is not None:
            return self.config.get(item)
        return self.config['preferences'].get(item)

    @property
    def user(self):
        # handy method for accessing current user's information
        if self.config['current_user'] is None:
            self.config['accounts'].append({})
            self.config['current_user'] = 0
        return self.config['accounts'][self.config['current_user']]

    def load(self):
        if os.path.isfile(self.config_file):
            with open(self.config_file, encoding='utf8') as f:
                cache = json.load(f)
                return cache
        return {}

    def dump(self):
        with open(self.config_file, 'w', encoding='utf8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2, sort_keys=True)

    def configure(self):
        config = {}
        for option, value in self.config['preferences'].items():
            text = get_input('[-] {} ({})>'.format(cstring(option, 'cyan'), cstring(value, 'white')))
            if text == '':
                continue
            if isinstance(value, bool):
                config[option] = True if text.lower() == 'true' else False
            else:
                config[option] = type(value)(text)
        self.config.update(config)


cfg = Config()
