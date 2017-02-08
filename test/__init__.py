import os

os.putenv('DEBUG', 'true')

from fanfou.new.fanfoucli.fan import Fan

fan = Fan()
print(fan.api.rate_limit_stats())
print(fan.api.verify_credentials())
