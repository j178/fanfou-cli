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
from . import config as cfg
from .fan import Fan


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--new', metavar='X', nargs='*', help='发布新的状态')
    parser.add_argument('-i', '--image', help='添加图片')
    parser.add_argument('-r', '--revert', action='store_true', help='撤回前一条消息')
    parser.add_argument('-m', '--me', action='store_true', help='查看个人信息')
    parser.add_argument('-u', '--user', help='查看他人信息')
    parser.add_argument('-v', '--view', action='store_true', help='浏览模式')
    parser.add_argument('-d', '--random', action='store_true', help='随便看看')
    parser.add_argument('--dump', metavar='FILENAME', nargs='?', const='timeline.json',
                        help='备份所有状态为JSON格式,输入保存文件名')
    parser.add_argument('--lock', metavar='0/1', type=int, help='需要我批准才能查看我的消息(1表示上锁，0表示解锁)')
    parser.add_argument('--verbose', action='store_true', help='打印日志')
    parser.add_argument('--id', action='store_true', help='显示用户ID')
    parser.add_argument('--time', action='store_true', help='显示时间标签')
    parser.add_argument('--clear', action='store_true', help='浏览完成后自动清屏')
    parser.add_argument('-V', '--version', action='store_true', help='显示版本号')
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
    if cfg.AUTO_CLEAR:
        clear_screen()


def main():
    signal.signal(signal.SIGINT, handler)
    atexit.register(clear_screen_handler)

    args, unknown = parse_args()
    level = logging.DEBUG if args.verbose  else logging.INFO
    logging.basicConfig(level=level,
                        format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    cfg.SHOW_ID = args.id
    cfg.SHOW_TIME_TAG = args.time
    cfg.AUTO_CLEAR = args.clear
    fan = Fan()

    if args.dump:
        fan.dump(args.save_all_statuses)
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
