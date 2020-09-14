import asyncio, time
from datetime import datetime
import copra.rest
from copra.websocket import Channel, Client
import pandas as pd
import LOB_funcs as LOBf
class L2_Update(Client):
    def __init__(self, loop, channel, input_args):
        self.time_now = datetime.utcnow() #initial start time
        self.hist = LOBf.history()
        #self.currency_pair = input_args.currency_pair
        self.position_range = input_args.position_range
        self.recording_duration = input_args.recording_duration
        super().__init__(loop, channel) # something about a parent class sending attributes to the child class (Ticker)

    def on_open(self):
        print("Let's count the L2 messages!", self.time_now)
        super().on_open() # inheriting things from the parent class who really knows    

    def on_message(self, msg):
        """ PERFORMING OPERATIONS ON self.x"""
        if msg['type'] in ['snapshot']:
            self.snapshot_token = True
            time = self.time_now
            self.hist.snapshot_bid = msg['bids'] #creates the list of [[price, size], ... [price, size]] which is what we'll be working on
            self.hist.snapshot_ask = msg['asks'] 
            self.hist.bid_range = [float(self.hist.snapshot_bid[i][0]) for i in range(len(self.hist.snapshot_bid))]
            self.hist.ask_range = [float(self.hist.snapshot_ask[i][0]) for i in range(len(self.hist.snapshot_ask))] # x_range is the range in prices from our initial observation
            self.hist.bid_volm  = [float(self.hist.snapshot_bid[i][1]) for i in range(len(self.hist.snapshot_bid))] # x_volm is the associated volum from our initial observation 
            self.hist.ask_volm  = [float(self.hist.snapshot_ask[i][1]) for i in range(len(self.hist.snapshot_ask))]
            self.hist.snapshot_bid = [[self.hist.bid_range[i], self.hist.bid_volm[i]] for i in range(len(self.hist.snapshot_bid))]
            self.hist.snapshot_ask = [[self.hist.ask_range[i], self.hist.ask_volm[i]] for i in range(len(self.hist.snapshot_ask))] #convert x from str into floats #convert x from str into floats
            self.hist.bid_history.append([time, self.hist.snapshot_bid]) # append this initial instance of x to history
            self.hist.ask_history.append([time, self.hist.snapshot_ask]) # append this initial instance of x to history

        if msg['type'] in ['ticker']:
            time=datetime.strptime(msg['time'],'%Y-%m-%dT%H:%M:%S.%fZ') # msg['time'] into a datetime object
            event_size = float(msg['last_size'])
            best_bid = float(msg['best_bid'])
            best_ask = float(msg['best_ask'])
            spread = best_ask - best_bid
            side = msg['side']
            price = msg['price']
            position = 0
            order_type = 'market'
            mid_price = 0.5*(best_bid + best_ask)
            message = [time, order_type, price, event_size, position, mid_price, spread]
            if side == 'buy':
                self.hist.ask_events = self.hist.add_market_order_message(message, self.hist.ask_events)
            elif side == 'sell':
                self.hist.bid_events = self.hist.add_market_order_message(message, self.hist.bid_events)
            else:
                print("unknown matched order")

        if msg['type'] in ['l2update']:# update messages 
            time=datetime.strptime(msg['time'],'%Y-%m-%dT%H:%M:%S.%fZ') #from the message extract time
            changes = msg['changes'] #from the message extract the changes
            side = changes[0][0] #side in which the changes happend (don't worry its orderbook crap)
            price_level = float(changes[0][1]) #the position in x_range that the change is affecting
            level_depth = float(changes[0][2]) #the value in x_volm that is changing
            pre_level_depth = 0 
            self.hist.token=False
            if side == "buy":
                price_match_index = list(filter(lambda x: LOBf.price_match(self.hist.bid_range[x], price_level), range(len(self.hist.bid_range))))
                LOBf.UpdateSnapshot_bid_Seq(self.hist, time, side, price_level, level_depth, pre_level_depth, price_match_index)
            elif side == "sell":
                price_match_index = list(filter(lambda x: LOBf.price_match(self.hist.ask_range[x], price_level), range(len(self.hist.ask_range))))
                LOBf.UpdateSnapshot_ask_Seq(self.hist, time, side, price_level, level_depth, pre_level_depth, price_match_index)                
            else:
                print("unknown message")

        if (datetime.utcnow() - self.time_now).total_seconds() > self.recording_duration:  # after 1 second has passed
            self.loop.create_task(self.close()) # ASyncIO nonsense

    def on_close(self, was_clean, code, reason):
        print("Connection to server is closed")
        print(was_clean)
        print(code)
        print(reason)
        """Massages my list of [time, [[price, volm], ... , [price,volm]]] into a clean dataframe""" 
        final_bid_list = LOBf.convert_array_to_list_dict(self.hist.bid_history, self.position_range)
        final_ask_list = LOBf.convert_array_to_list_dict(self.hist.ask_history, self.position_range)

        title1 = "L2_orderbook_bid.xlsx"
        LOBf.pd_excel_save(title1, final_bid_list)

        title2 = "L2_orderbook_ask.xlsx"
        LOBf.pd_excel_save(title2, final_ask_list)

        title3 = "L2_orderbook_events_bid.xlsx"
        LOBf.pd_excel_save(title3, self.hist.bid_events)

        title4 = "L2_orderbook_events_ask.xlsx"        
        LOBf.pd_excel_save(title4, self.hist.ask_events)

class input_args(object):
    def __init__(self, currency_pair='ETH-USD', position_range=4, recording_duration=10, style='all'):
        self.currency_pair = currency_pair
        self.position_range = position_range
        self.recording_duration = recording_duration
        self.style = 'all'

def main():
    pass

if __name__ == '__main__':
    main()

