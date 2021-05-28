import sys
print(sys.path)

import crobat 
import asyncio, time
#from datetime import datetime
import copra.rest
from copra.websocket import Channel, Client
#import pandas as pd

# how do i want this shit to work

# 1. you import the program
# 2. you intialize the args, with the option to start recording
# 3a. if you choose to start recording
#     i. you can call the class.get_item to see what the last order was
#     ii. you can call a function to get the current picture of the orderbook
#     iii.  you can call a function to  get the running order book images  as dirty or pandas'd
#     iv.  you can call a function to get the last_orders disrt or as pandas
# 3b. if not you have the option of calling the class indiviudually within your own asyncio loop
# 4. error handling ? 

def main():
    settings = rec.input_args()
    loop = asyncio.get_event_loop()
    channel = Channel('level2', settings.currency_pair) 
    channel2 =Channel('ticker', settings.currency_pair)
    ws = rec.L2_Update(loop, channel, settings)
    ws.subscribe(channel2)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(ws.close())
        loop.close()

if __name__ == '__main__':
    main()