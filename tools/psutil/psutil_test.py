import psutil
import time

def processcheck(seekitem):
    plist = psutil.process_iter()
    for p in plist:
        cpu = 0
        try:
            cpu = p.cpu_percent(interval=0.1)
        except:
            continue

        if cpu > 0:
            print(p.name(), cpu)
            print(p)

processcheck("node")