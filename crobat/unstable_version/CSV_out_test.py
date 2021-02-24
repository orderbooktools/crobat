import recorder_full as rec
import asyncio, time
from datetime import datetime
import copra.rest
from copra.websocket import Channel, Client
import argparse

preamble_currency_pair = "Select from the available currency pairs  on coinbase.com or try ETH-USD"
preamble_recording_duration = "State to the nearest second how long you would like record for"
preamble_position_range = "State how many positions from the best bid/ask you would like to examine"

parser  = argparse.ArgumentParser()
parser.add_argument("currency_pair", type=str, help=preamble_currency_pair)
parser.add_argument("recording_duration", type=int, help=preamble_recording_duration)
parser.add_argument("position_range", type=int, help=preamble_position_range)
args = parser.parse_args()


class input_args(object):
    def __init__(self, currency_pair='ETH-USD', position_range=5, recording_duration=5):
        self.currency_pair = currency_pair
        self.position_range = position_range
        self.recording_duration = recording_duration

def main():
    if args.currency_pair:
        print("currency_pair selected is {}.".format(args.currency_pair))
    else:
        print("The default currency_pair, ETH-USD, will be used.")
    if args.recording_duration:
        print("This session will record for {} seconds".format(args.recording_duration))
    else:
        print("The defaul session length of 5 seconds will be used")
    if args.position_range:
        print("The position_range is set to {} positions from the best bid/ask".format(args.position_range))
    else:
        print("The default position range of 5 will be used.")

    settings_1 = input_args(currency_pair=args.currency_pair,
                            position_range=args.position_range,
                            recording_duration=args.recording_duration)
    
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