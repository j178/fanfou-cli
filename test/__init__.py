from new.fanfoucli.fan import Fan

fan = Fan()
try:
    print(fan.view())
except KeyboardInterrupt:
    print('keyboard interrupt')
