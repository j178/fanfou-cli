#!/usr/bin/env python3
# coding=utf-8
# Author: John Jiang
# Date  : 2016/8/29

import argparse
import atexit
import logging
import os
import signal
import sys

from .util import clear_screen, open_in_browser
from .config import cfg
from .fan import Fan


def parse_args():
    parser = argparse.ArgumentParser()
    command_parser = parser.add_argument_group('命令')
    command_parser.add_argument('-n', '--new', metavar='X', nargs='*', help='发布新的状态')
    command_parser.add_argument('-i', '--image', help='添加图片')
    command_parser.add_argument('-r', '--revert', action='store_true', help='撤回前一条消息')
    command_parser.add_argument('-m', '--me', action='store_true', help='查看个人信息')
    command_parser.add_argument('-u', '--user', metavar='ID', help='查看他人信息，参数为用户ID')
    command_parser.add_argument('-v', '--view', action='store_true', help='浏览模式')
    command_parser.add_argument('-d', '--random', action='store_true', help='随便看看')
    command_parser.add_argument('--config', action='store_true', help='修改默认配置')
    command_parser.add_argument('--login', action='store_true', help='登陆新的账号')
    command_parser.add_argument('--switch', action='store_true', help='切换账号')
    command_parser.add_argument('--dump', metavar='FILE', nargs='?', const='fanfou-archive.json',
                                help='备份所有状态，保存到 FILE 文件中(JSON格式)')
    command_parser.add_argument('--lock', metavar='0/1', type=int, help='需要我批准才能查看我的消息(1表示上锁，0表示解锁)')
    command_parser.add_argument('-V', '--version', action='store_true', help='显示版本号')

    option_parser = parser.add_argument_group('选项')
    option_parser.add_argument('--verbose', action='store_true', help='打印日志')
    option_parser.add_argument('--show-id', dest='show_id', action='store_true', help='显示用户ID')
    option_parser.add_argument('--show-time', dest='show_time_tag', action='store_true', help='显示时间标签')
    option_parser.add_argument('--clear', dest='auto_clear', action='store_true', help='浏览完成后自动清屏')
    option_parser.add_argument('--auto-auth', dest='auto_auth', action='store_true', help='自动验证')
    option_parser.add_argument('--count', dest='timeline_count', type=int, help='时间线显示消息的数量')
    option_parser.add_argument('--show-image', dest='show_image', action='store_true', help='显示图片')
    option_parser.add_argument('--xauth', action='store_true', help='使用xauth验证方式')
    return parser.parse_known_args()


def exit_handler(signal, frame):
    print('\nBye!')
    sys.exit(0)


def read_from_stdin():
    try:
        return sys.stdin.buffer.read().decode('utf8')
    except UnicodeDecodeError:
        logging.error('[x] 当前内容不是UTF-8编码，解码错误！')
        sys.exit(1)


@atexit.register
def clear_screen_handler():
    if cfg.auto_clear:
        clear_screen()


def main():
    signal.signal(signal.SIGINT, exit_handler)

    args, unknown = parse_args()
    level = logging.DEBUG if args.verbose  else logging.INFO
    logging.basicConfig(level=level,
                        format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    cfg.args = args

    if args.version:
        import fanfoucli
        print(fanfoucli.__version__)
        return
    if len(sys.argv) == 1:
        open_in_browser('http://fanfou.com')
        return

    fan = Fan(cfg)

    if args.config:
        cfg.configure()
    elif args.dump:
        fan.dump(args.dump)
    elif args.login:
        fan.login()
    elif args.switch:
        fan.switch_account()
    elif args.revert:
        fan.revert()
    elif args.lock is not None:
        fan.lock(bool(args.lock))
    elif args.me:
        fan.me()
    elif args.user:
        s, user = fan.api.users_show(id=args.user)
        if s:
            fan.display_user(user)
    elif args.view:
        fan.view()
    elif args.random:
        fan.random_view()
    else:
        status = ''
        # fan -
        # echo something | fan
        if (len(sys.argv) == 2 and sys.argv[1] == '-') \
                or (len(sys.argv) == 1 and hasattr(sys.stdin, 'fileno') and not os.isatty(sys.stdin.fileno())):
            # sys.stdin.read默认使用sys.stdin.encoding解码，而sys.stdin.encoding是根据终端来设置，所以cat xx | fan会导致编码错误
            # 这里改用从底层读取二进制流，然后手动按照utf8解析，如果文件不是utf8格式的话，仍然会出错
            logging.debug('stdin encoding %s', sys.stdin.encoding)
            status = read_from_stdin()

        elif args.new:  # fan -n something
            status = ' '.join(args.new)
        elif unknown:  # fan anything
            status = ' '.join(unknown)

        # 发图片
        if args.image:
            fan.upload_photos(status, args.image)
        else:
            fan.update_status(status)


if __name__ == '__main__':
    main()
