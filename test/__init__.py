# from new.fanfoucli.fan import Fan
#
# fan = Fan()
# try:
#     print(fan.upload_photos('daf',
#                             'http://photo1.fanfou.com/v1/mss_3d027b52ec5a4d589e68050845611e68/ff/n0/0e/10/y1_288259.gif@596w_1l.gif'))
# except KeyboardInterrupt:
#     print('keyboard interrupt')

def test_config():
    from new.fanfoucli.config import cfg
    import sys
    cfg.populate(sys)


def test_auth():
    from new.fanfoucli.fan import Fan
    from new.fanfoucli.config import cfg
    f = Fan(cfg)
    f.view()


if __name__ == '__main__':
    test_auth()
    # test_config()
