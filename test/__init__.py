from new.fanfoucli.fan import Fan

fan = Fan()
try:
    fan.me()
except KeyboardInterrupt:
    print('keyboard interrupt')
