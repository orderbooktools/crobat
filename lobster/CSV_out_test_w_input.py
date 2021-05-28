import recorder_full as rec
import asyncio, time
from datetime import datetime
import copra.rest
from copra.websocket import Channel, Client
import argparse

class input_args(object):
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

def check_input(input_str, reference_var):
    


def main():
    currency_pair = input("Please state your currency pair:")
    recording_duration = input("Please state your recording_duration:")
    position_range = input("Please state your position range:")
    sides = input("Please state your sides separted by ',':")
    filetype = input("Please state desired output filetypes separted by ',':")

    recording_duration = float(recording_duration)
    position_range = int(position_range)
    sides.replace(" ", "")
    sides = sides.split(",")
    filetype.replace(" ", "")
    filetype = filetype.split(",")

    #print(currency_pair, recording_duration, position_range, sides, filetype)
    settings_1 = input_args(currency_pair=currency_pair,
                            position_range=position_range,
                            recording_duration=recording_duration,
                            sides=sides,
                            filetype=filetype)
    
    loop = asyncio.get_event_loop()
    
    channel1 = Channel('level2', settings_1.currency_pair) 
    #channel2 = Channel('ticker', settings_1.currency_pair)

    ws_1 = rec.L2_Update(loop, channel1, settings_1)
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