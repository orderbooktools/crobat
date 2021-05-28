import json_saver_class as jsc
import asyncio, time
from datetime import datetime
import copra.rest
from copra.websocket import Channel, Client

class input_args(object):
    def __init__(self, currency_pair='ETH-USD', position_range=5, recording_duration=5):
        self.currency_pair = currency_pair
        self.position_range = position_range
        self.recording_duration = recording_duration

def main():
    
    settings_1 = input_args(recording_duration=60)
    
    loop = asyncio.get_event_loop()
    
    channel1 = Channel('ticker', settings_1.currency_pair) 
    #channel2 = Channel('ticker', settings_1.currency_pair)

    ws_1 = jsc.Ticker(loop, channel1, settings_1)
    #ws_1.subscribe(channel2)

    #count = 0
    
    timestart=datetime.utcnow()

    try:     
       loop.run_forever()


    except KeyboardInterrupt:
        loop.run_until_complete(ws_1.close())
        #loop.run_until_complete(ws_2.close())
        loop.close()

if __name__ == '__main__':
    main()