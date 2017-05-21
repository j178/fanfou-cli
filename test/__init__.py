from new.fanfoucli.fan import Fan

fan = Fan()
try:
    print(fan.lock(0))
except KeyboardInterrupt:
    print('keyboard interrupt')
