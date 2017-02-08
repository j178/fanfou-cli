import os
os.putenv('DEBUG', 'true')

from fanfou.new.fanfoucli.fan import Fan


fan = Fan()
fan.me()
fan.update_status('测试一下')
