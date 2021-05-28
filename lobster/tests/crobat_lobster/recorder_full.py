import asyncio, time
from datetime import datetime
import copra.rest
from copra.websocket import Channel, Client
import pandas as pd
import LOB_funcs as LOBf
import history_funcs as hf 
import gc
import numpy as np
import filesave 
from sys import exit

pd.set_option('display.max_columns', 500)

class L2_Update(Client):
    def __init__(self, loop, channel, input_args):
        self.time_now = datetime.utcnow() #initial start time
        self.hist = LOBf.history()
        self.recording_settings = input_args
        self.snap_received = False
        super().__init__(loop, channel) # something about a parent class sending attributes to the child class (Ticker)

    def on_open(self):
        print("Let's count the L2 messages!", self.time_now)
        super().on_open() # inheriting things from the parent class who really knows    

    def on_message(self, msg):
        """ PERFORMING OPERATIONS ON self.x"""
        if msg['type'] in ['snapshot']:
            print("received the snapshot")
            time = self.time_now
            self.hist.initialize_snap_events(msg,self.time_now)
            self.snap_received = True
            self.min_dec = self.hist.min_dec 
        if msg['type'] in ['ticker']:
            #print("received ticker message")
            if self.snap_received:
                time=datetime.strptime(msg['time'],'%Y-%m-%dT%H:%M:%S.%fZ') # msg['time'] into a datetime object
                best_bid, best_ask = float(msg['best_bid']) , float(msg['best_ask'])
                direction = 1 if msg['side'] == 'sell' else -1
                spread = best_ask - best_bid
                mid_price = 0.5*(best_bid + best_ask)
                position = -1 if side == 'sell' else 1
                size = np.around(float(msg['last_size']), decimals=self.min_dec)
                message = [time, 4, int(msg['order_id']), size, float(msg['price']), direction]
                self.hist.lobster_events = self.hist.add_market_order_message(message, self.hist.lobster_events)
                self.hist.check_mkt_can_overlap(self.hist.lobster_events, 'market')
            else:
                print("mkt order arrived but no snapshot received yet")

        if msg['type'] in ['l2update']:# update messages 
            time=datetime.strptime(msg['time'],'%Y-%m-%dT%H:%M:%S.%fZ') #from the message extract time
            changes = msg['changes'] #from the message extract the changes
            side = -1 if changes[0][0] == "buy" else 1 #side in which the changes happend (don't worry its orderbook crap)
            price_level = float(changes[0][1]) #the position in x_range that the change is affecting
            level_depth = np.around( float(changes[0][2]), decimals=self.min_dec) #the value in x_volm that is changing
            pre_level_depth = 0 
            self.hist.token = False
            if side == "bid":
                price_match_index = list(filter(lambda x: LOBf.price_match(self.hist.bid_range[x], price_level), range(len(self.hist.bid_range))))
                LOBf.UpdateSnapshot_bid_Seq(self.hist, time, side, price_level, level_depth, pre_level_depth, price_match_index)
            elif side == "ask":
                price_match_index = list(filter(lambda x: LOBf.price_match(self.hist.ask_range[x], price_level), range(len(self.hist.ask_range))))
                LOBf.UpdateSnapshot_ask_Seq(self.hist, time, side, price_level, level_depth, pre_level_depth, price_match_index)                
            else:
                print("unknown message")

        if (datetime.utcnow() - self.time_now).total_seconds() > float(self.recording_settings.recording_duration):  # after 1 second has passed
            self.loop.create_task(self.close()) # ASyncIO nonsense

    def on_close(self, was_clean, code, reason):
        print("Connection to server is closed")
        print(was_clean)
        print(code)
        print(reason)

        filesave.filesaver(self.hist,
                           self.recording_settings.position_range, 
                           sides=self.recording_settings.sides, 
                           filetype=self.recording_settings.filetype)
        

        # """Massages my list of [time, [[price, volm], ... , [price,volm]]] into a clean dataframe""" 
        # final_bid_list, final_bid_prices = hf.convert_array_to_list_dict(self.hist.bid_history, self.position_range)
        # final_ask_list, final_ask_prices = hf.convert_array_to_list_dict(self.hist.ask_history, self.position_range)
        # final_signed_list, final_signed_prices = hf.convert_array_to_list_dict_sob(self.hist.signed_history, self.hist.signed_events)

        # title1 = "L2_orderbook_volm_bid"+str(self.hist.bid_events[-1][0])+".xlsx"
        # hf.pd_excel_save(title1, final_bid_list)

        # title2 = "L2_orderbook_volm_ask"+str(self.hist.ask_events[-1][0])+".xlsx"
        # hf.pd_excel_save(title2, final_ask_list)

        # title3 = "L2_orderbook_events_bid" +str(self.hist.bid_events[-1][0])+".xlsx"
        # hf.pd_excel_save(title3, self.hist.bid_events)

        # title4 = "L2_orderbook_events_ask" +str(self.hist.ask_events[-1][0])+".xlsx"        
        # hf.pd_excel_save(title4, self.hist.ask_events)

        # title5 = "L2_orderbook_prices_bid"+str(self.hist.bid_events[-1][0])+".xlsx"
        # hf.pd_excel_save(title5, final_bid_prices)

        # title6 = "L2_orderbook_prices_ask"+str(self.hist.ask_events[-1][0])+".xlsx"
        # hf.pd_excel_save(title6, final_ask_prices)

        # title7 = "L2_orderbook_volm_signed"+str(self.hist.signed_events[-1][0])+".xlsx"
        # hf.pd_excel_save(title7, final_signed_list)

        # title8 = "L2_orderbook_events_signed" +str(self.hist.signed_events[-1][0])+".xlsx"
        # hf.pd_excel_save(title8, self.hist.signed_events)

        # title8 = "L2_orderbook_prices_signed"+str(self.hist.signed_events[-1][0])+".xlsx"
        # hf.pd_excel_save(title8, final_signed_prices)

        gc.collect()
        exit() #dusty but w/e

def main():
    pass

if __name__ == '__main__':
    main()