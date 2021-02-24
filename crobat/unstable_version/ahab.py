timeimport asyncio, time
from datetime import datetime
import copra.rest
from copra.websocket import Channel, Client
import pandas as pd
import LOB_funcs as LOBf
import history_funcs as hf 
import gc
import numpy as np
import statistics

pd.set_option('display.max_columns', 500)
class tracker(object):
    def __init__(self):
        self.order_ids = []
        self.order_id_thresh_coin = 5
        self.order_id_thresh_dollar = 10000
        self.watched_ids = []
        self.historical_depth = []
        self.mean_order_depth = 0
        self.messages_in_received = []
        self.messages_in_open = []
        self.messages_in_done = []

    def check_received_order(self, msg):
        self.add_message = False
        value = float(msg['price'])*float(msg['remaining_size'])
        if value > order_id_thresh_dollar:
            self.add_message = True
        else:
            variance = np.var(historical_values)
            self.mean_order_value = mean(historical_values)
            if value > self.mean_order_value + 2*variance:
                self.add_message = True
                print("stat significantly large order")

    def add_tracked_order(self, msg):
        if self.add_message = True:     
            value = float(msg['price'])*float(msg['remaining_size'])
            if "client_oid" in msg:
                _dict = {
                    'time':msg['time'],
                    'type':msg['type'],
                    'client_oid':msg['client_oid'],
                    'order_id':msg['order_id'],
                    'price':float(msg['price']),
                    'size':float(msg['remaining_size']),
                    'value':value
                    }    
            else:
                _dict = {
                    'time':msg['time'],
                    'type':msg['type'],
                    'order_id':msg['order_id'],
                    'price':float(msg['price']),
                    'size':float(msg['remaining_size']),
                    'value':value
                    }
            self.messages_in_received.append(_dict)

    def identify_tracked_order(self, msg):
        if msg['type'] == "open":
            received_list = [dicts['order_id'] for dicts in self.messages_in_received]
            received_index = list(filter(lambda x: LOBf.price_match(received_list[x], msg['order_id']), range(len(self.messages_in_received))))
            self.messages_in_open.append(self.messages_in_received[received_index])
            del self.messages_in_received[received_index] 
        elif msg['type'] == "done":
            open_list = [dicts['order_id'] for dicts in self.messages_in_open]
            open_index = list(filter(lambda x: LOBf.price_match(open_list[x], msg['order_id']), range(len(self.messages_in_open))))
            self.messages_in_done.append(self.messages_in_open[open_index])
            del self.messages_in_open[open_index]
        elif msg['type'] == "match":
            
            pass

    def update_tracked_order(self, msg):
        order_id_list = [dicts['order_id'] for dicts in self.watched_ids]
        key_match_index = list(filter(lambda x: LOBf.price_match(order_id_list[x], msg['order_id']), range(len(self.watched_ids))))
        if key_match_index:
            self.watched_ids[key_match_index]['type'] = msg['type']
            self.watched_ids[key_match_index]['remaining_size'] = float(msg['remaining_size'])
            print("updating order id", self.watched_ids[key_match_index])
            if message['type'] == "open":
                time_to_open = (msg['time'] - self.watched_ids[key_match_index]['time']).seconds()
                self.messages_in_open.append([self.watched_ids[key_match_index]['order_id'], time_to_open, msg['time']])
            elif messages['type'] == "done"
                open_order_ids = [self.messages_in_open[i][0] for i in self.messages_in_open]
                key_match_index = list(filter(lambda x: LOBf.price_match(order_id_list[x], msg['order_id']), range(len(self.watched_ids))))
                time_to_close = self.messages_in_open[index]
        else:
            print("no key match")

    def remove_tracked_order(self,msg):
        if 
        

class ahab(Client):
    def __init__(self, loop, channel, input_args):
        self.time_now = datetime.utcnow() #initial start time
        self.addresses = []
        self.tracking = tracker()
        self.position_range = input_args.position_range
        self.recording_duration = input_args.recording_duration
        self.counter = 0 
        super().__init__(loop, channel) # something about a parent class sending attributes to the child class (Ticker)

    def on_open(self):
        print("Let's count the L3 messages!", self.time_now)
        super().on_open() # inheriting things from the parent class who really knows    

    def on_message(self, msg):
        print(msg['type'])

        basically i should 
        1. collected messages in the received category 
        2. check if they move to either open
        3. then they move t o matched, change, 
        4. then they either get moved from matched to done, or change to cancel done
        # adding new order ids 
        if msg['type'] in ['received']:
            1. check order size
            2. if size add to id tracked 

        if msg['order_id'] in interesting order_ids:
            1. UPDATE THE ORDER
            if msg['type'] in ['open']:
                3. in history note the speed from received to open? (idont think this is necessary)

            elif msg['type'] in ['match']: 
                1. update tjhe state of the order
                3. create 

            elif msg['type'] in ['change']:

            elif msg['type'] in ['done']:
                delete the order id
                transport the final life cycle of the order
        
       

        else:
            print("unknown message")
            print(msg)
        """ PERFORMING OPERATIONS ON self.x"""
        # if msg['type'] in ['']:
        #     print("received the snapshot")
        #     time = self.time_now
        #     self.hist.initialize_snap_events(msg,self.time_now)
        #     self.snap_received = True
        #     self.min_dec = self.hist.min_dec 
        # elif "price" in msg:
        #     self.tracking.add_tracked_order(msg)
        #     self.tracking.update_tracked_order(msg)
        # else:
        #     print("strange message")
        #     print(msg)

        # if msg['type'] in ['ticker']:
        #     #print("received ticker message")
        #     if self.snap_received:
        #         time=datetime.strptime(msg['time'],'%Y-%m-%dT%H:%M:%S.%fZ') # msg['time'] into a datetime object
        #         best_bid, best_ask = float(msg['best_bid']) , float(msg['best_ask'])
        #         side = "bid" if msg['side'] == 'sell' else "ask"
        #         spread = best_ask - best_bid
        #         mid_price = 0.5*(best_bid + best_ask)
        #         position = -1 if side == 'sell' else 1
        #         size = np.around(float(msg['last_size']), decimals=self.min_dec)
        #         size_signed = size if side == "bid" else size*(-1)
        #         message = [time, 'market', float(msg['price']), size_signed, position, side, mid_price, spread]
        #         sided_message = [time, 'market', float(msg['price']), size, position, mid_price, spread]
        #         self.hist.signed_events = self.hist.add_market_order_message(message, self.hist.signed_events)
        #         self.hist.check_mkt_can_overlap(self.hist.signed_events,'market')
        #         if side == 'ask':
        #             self.hist.ask_events = self.hist.add_market_order_message(sided_message, self.hist.ask_events)
        #             self.hist.check_mkt_can_overlap(self.hist.ask_events, 'market')
        #         elif side == 'bid':
        #             self.hist.bid_events = self.hist.add_market_order_message(sided_message, self.hist.bid_events)
        #             self.hist.check_mkt_can_overlap(self.hist.bid_events, 'market')
        #         else:
        #             print("unknown matched order")
        #     else:
        #         print("mkt order arrived but no snapshot received yet")

        # if msg['type'] in ['l2update']:# update messages 
        #     time=datetime.strptime(msg['time'],'%Y-%m-%dT%H:%M:%S.%fZ') #from the message extract time
        #     changes = msg['changes'] #from the message extract the changes
        #     side = 'bid' if changes[0][0] == "buy" else "ask" #side in which the changes happend (don't worry its orderbook crap)
        #     price_level = float(changes[0][1]) #the position in x_range that the change is affecting
        #     level_depth = np.around( float(changes[0][2]), decimals=self.min_dec) #the value in x_volm that is changing
        #     pre_level_depth = 0 
        #     self.hist.token = False
        #     if side == "bid":
        #         price_match_index = list(filter(lambda x: LOBf.price_match(self.hist.bid_range[x], price_level), range(len(self.hist.bid_range))))
        #         LOBf.UpdateSnapshot_bid_Seq(self.hist, time, side, price_level, level_depth, pre_level_depth, price_match_index)
        #     elif side == "ask":
        #         price_match_index = list(filter(lambda x: LOBf.price_match(self.hist.ask_range[x], price_level), range(len(self.hist.ask_range))))
        #         LOBf.UpdateSnapshot_ask_Seq(self.hist, time, side, price_level, level_depth, pre_level_depth, price_match_index)                
        #     else:su
        #         print("unknown message")

        if (datetime.utcnow() - self.time_now).total_seconds() > self.recording_duration:  # after 1 second has passed
            self.loop.create_task(self.close()) # ASyncIO nonsense

    def on_close(self, was_clean, code, reason):
        print("Connection to server is closed")
        print(was_clean)
        print(code)
        print(reason)

        print("")
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

def main():
    pass

if __name__ == '__main__':
    main()