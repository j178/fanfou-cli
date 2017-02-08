import os
os.putenv('DEBUG', 'true')

from fanfou.new.fanfoucli.fan import Fan


fan = Fan()
fan.view()