from new.fanfoucli.fan import Fan

fan = Fan()
try:
    fan.upload_photos('test',
                      'htt://photo2.fanfou.com/v1/mss_3d027b52ec5a4d589e68050845611e68/ff/n0/0e/0d/n2_258918.jpg@100w_100h_1l.jpg')
except KeyboardInterrupt:
    print('keyboard interrupt')
