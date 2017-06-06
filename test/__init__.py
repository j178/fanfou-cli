from new.fanfoucli.config import cfg
from new.fanfoucli.fan import Fan
import sys
import logging

logging.basicConfig(level=logging.DEBUG)


def test_auth():
    f = Fan(cfg)
    f.view()


def test_main():
    sys.argv[1:] = ['-V']
    from new.fanfoucli.cli import main
    main()


def test_switch():
    fan = Fan(cfg)
    fan.switch_account()


def test_login():
    fan = Fan(cfg)
    fan.login()


if __name__ == '__main__':
    test_auth()
    # test_config()
    # test_main()
    # test_switch()
    # test_login()
