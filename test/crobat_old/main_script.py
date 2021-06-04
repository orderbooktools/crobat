import asyncio, time
#from datetime import datetime
import copra.rest
from copra.websocket import Channel, Client
from . import recorder_full as rec
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

class input_args(object):
    """
    class containing input arguments and settings for the main script.        ||
    
    Attributes
    ----------
    currency_pair : str 
        default 'ETH-USD'
        currency pair from coinbase exchange see
        ????? for the current list of approved currency pairs
    
    position_range : int default 5
        default 'ETH-USD'
        ordinal position range that the order book will log to.
    
    recording_duration : int 
        default 5
        number of seconds (can be float64) that the main script will record before
        closing the connection. 
    
    sides : list of str
        default ['bid', 'ask', 'signed']
        sides of interest in saving can be:
        ['bid', 'ask', 'signed'] or an omission for those members only. 
    
    filetype : list of str
        default ['xlsx']
        the file type the script will save as; can be:
        ['xlsx', 'csv', 'pkl'] or an omission of those members only.
    
    Methods
    -------
        None
    """
    def __init__(self, currency_pair='ETH-USD',
                       position_range=5,
                       recording_duration=5,
                       sides=['bid, ask', 'signed'],
                       filetype=['xlsx']):
    
        self.currency_pair = currency_pair
        self.position_range = position_range
        self.recording_duration = recording_duration
        self.sides = sides
        self.filetype = filetype

def main():
    """
    main script; passes settings from an instance of the class input_args() 
    to the instances of the classes Channel, and L2_Update.
    
    Parameters
    ----------
        None
    
    Returns
    -------
        None
        Outputs a files if settings are correct
    
    Raises
    ------
        Needs testing
    """
    settings = input_args()
    loop = asyncio.get_event_loop()
    channel = Channel('level2', settings.currency_pair) 
    channel2 = Channel('ticker', settings.currency_pair)
    ws = rec.L2_Update(loop, channel, settings)
    ws.subscribe(channel2)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(ws.close())
        loop.close()

if __name__ == '__main__':
    main()