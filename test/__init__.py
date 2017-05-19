from fanfoucli.fan import Fan

fan = Fan()
try:
    fan.view()
except KeyboardInterrupt:
    print('keyboard interrupt')
