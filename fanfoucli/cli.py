#!/usr/bin/env python3
# coding=utf-8
# Author: John Jiang
# Date  : 2016/8/29

import argparse
import atexit
import logging
import signal
import sys

from . import clear_screen, open_in_browser
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
    command_parser.add_argument('--dump', metavar='FILE', nargs='?', const='timeline.json',
                                help='备份所有状态，保存到 FILE 文件中(JSON格式)')
    command_parser.add_argument('--lock', metavar='0/1', type=int, help='需要我批准才能查看我的消息(1表示上锁，0表示解锁)')

    option_parser = parser.add_argument_group('选项')
    option_parser.add_argument('--verbose', action='store_true', help='打印日志')
    option_parser.add_argument('--id', dest='show_id', action='store_true', help='显示用户ID')
    option_parser.add_argument('--time', dest='show_time_tag', action='store_true', help='显示时间标签')
    option_parser.add_argument('--clear', dest='auto_clear', action='store_true', help='浏览完成后自动清屏')
    option_parser.add_argument('--auto-auth', dest='auto_auth', action='store_true', help='自动验证')
    option_parser.add_argument('--count', dest='timeline_count', type=int, help='时间线显示消息的数量')
    option_parser.add_argument('-V', '--version', action='store_true', help='显示版本号')
    return parser.parse_known_args()


def handler(signal, frame):
    print('\nBye!')
    sys.exit(0)


def read_from_stdin():
    try:
        return sys.stdin.buffer.read().decode('utf8')
    except UnicodeDecodeError:
        logging.error('[x] 当前内容不是UTF-8编码，解码错误！')
        sys.exit(1)


def clear_screen_handler():
    if cfg.auto_clear:
        clear_screen()


def populate_cfg(args):
    cfg.show_id = args.show_id if args.show_id is not None else cfg.show_id
    cfg.show_time_tag = args.show_time_tag if args.show_time_tag is not None else cfg.show_time_tag
    cfg.auto_clear = args.auto_clear if args.auto_clear is not None else cfg.auto_clear
    cfg.auto_auth = args.auto_auth if args.auto_auth is not None else cfg.auto_auth
    cfg.timeline_count = args.timeline_count if args.timeline_count is not None else cfg.timeline_count


def main():
    signal.signal(signal.SIGINT, handler)
    atexit.register(clear_screen_handler)

    args, unknown = parse_args()
    level = logging.DEBUG if args.verbose  else logging.INFO
    logging.basicConfig(level=level,
                        format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    populate_cfg(args)
    fan = Fan(cfg)

    if args.dump:
        fan.dump(args.dump)
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
    elif args.version:
        import fanfoucli
        print(fanfoucli.__version__)
    else:
        status = ''
        unknown_str = ''
        if unknown:
            unknown_str = ''.join(unknown).strip()
        if unknown_str == '-':  # fan - read status from stdin
            # sys.stdin.read默认使用sys.stdin.encoding解码，而sys.stdin.encoding是根据终端来设置，所以cat xx | fan会导致编码错误
            # 这里改用从底层读取二进制流，然后手动按照utf8解析，如果文件不是utf8格式的话，仍然会出错
            logging.debug('stdin encoding %s', sys.stdin.encoding)
            status = read_from_stdin()
        elif args.new:  # fan -n something
            status = ' '.join(args.new)
        elif not sys.stdin.isatty() and not args.image:  # echo something | fan
            logging.debug('stdin encoding %s', sys.stdin.encoding)
            status = read_from_stdin()
        elif unknown:  # fan anything
            status = ' '.join(unknown)
        elif not args.image:
            open_in_browser('http://fanfou.com')
            return
        # 发图片
        if args.image:
            fan.upload_photos(status, args.image)
        else:
            fan.update_status(status)


if __name__ == '__main__':
    main()
