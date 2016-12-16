import argparse
import sys

from fanfou_cli.fan import Fan


def parse_args():
    parser = argparse.ArgumentParser()
    # nargs参数的妙用
    # add参数是可选的，但是我也想不加-a时且没有其他参数时也执行这个动作
    # 或者一个nagrs=*的positional，但是也可以不提供
    parser.add_argument('-a', '--add', nargs='*', help='发布新的状态')
    parser.add_argument('-r', '--revert', help='撤回前一条消息')
    parser.add_argument('-b', '--back-up', help='备份所有状态')
    # todo 添加类似git的子命令
    return parser.parse_known_args()


def main():
    fan = Fan()
    args = parse_args()

    if args.back_up:
        fan.backup()

    elif args.add or len(sys.argv) > 1:
        status = ' '.join(args.add or sys.argv[1:])
        b, r = fan.update_status(status)
        if b:
            print('发布成功:', r['text'])
        else:
            print('发布失败:', r['error'])


main()
