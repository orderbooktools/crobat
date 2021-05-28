import pandas as pd
import copy
import bisect
import numpy as np
import history_funcs as hf

class history(object):
    """
    Description: history object that 
    """
    def __init__(self):
        self.history=[]
        self.snapshot_bid = []
        self.snapshot_ask = []
        self.events = []
        self.order_type = None
        self.token = False
        self.position = 0
        self.event_size = 0
 
    def initialize_snap_events(self, msg, time):
        time = time
        self.snapshot_bid = msg['bids'][:3800]
        self.snapshot_ask = msg['asks'][:3800] 
        self.bid_range = [float(self.snapshot_bid[i][0]) for i in range(len(self.snapshot_bid))]
        self.ask_range = [float(self.snapshot_ask[i][0]) for i in range(len(self.snapshot_ask))] 
        self.min_dec = hf.get_min_dec(0.01,self.bid_range[0])
        self.bid_volm  = np.round([float(self.snapshot_bid[i][1]) for i in range(len(self.snapshot_bid))],decimals = self.min_dec)
        self.ask_volm  = np.round([float(self.snapshot_ask[i][1]) for i in range(len(self.snapshot_ask))],decimals = self.min_dec)
        self.snapshot_bid = [[self.bid_range[i], self.bid_volm[i]] for i in range(len(self.snapshot_bid))]
        self.snapshot_ask = [[self.ask_range[i], self.ask_volm[i]] for i in range(len(self.snapshot_ask))] 
        self.history.append = [time, self.snapshot_bid[::-1] + snapshot_ask]     
    def add_market_order_message(self, message, events):
        ## we're gonna be reqworking this program
        ## before it would receive  a makret message and aggregate the volm if 
        ## it arrived at the same time
        ## the nuance. is 
        ## sometimes a market order can extinguish the best bid and then
        ## strike the new best bid all in the same time point.
        ## however after that happens it takes a second for the L2 book to send a pair of 
        ## cancelation messages 
        index_start = 0
        index_stop = len(events) 
        events.append(message)
        if index_stop < 2:
            pass
        else:
            index_start = max(0,len(events)-3)
            index_stop  = len(events)-1

        for i in range(index_start, index_stop):
            if events[i][0] == events[i-1][0]: # suppose they arrived at the same time
                if events[i][4] == events[i][4]: # if the price is the same then just aggregate
                    events[i][3] += events[i-1][3] # aggregate the volms 
                    del events[i-1] # delete the event
                else: # if the price is different then if its a pair of market buy then the price gets higher, and market sells the prices drops 
                    pass # idk what else there is to do after that 
        return events

    # functions that modify the objects in __init__ on the arrival of L2 update. 
    def remove_price_level(self, snap_array, level_depth, match_index):
        if level_depth == 0 and match_index:            
            del snap_array[match_index[0]]
            self.token=True
        return snap_array

    def update_level_depth(self, snap_array, level_depth, match_index, pre_level_depth):
        if match_index: 
            update_index = match_index[0] 
            self.event_size = abs(snap_array[update_index][1] - level_depth)
            pre_level_depth = snap_array[update_index][1]
            if snap_array[update_index][1] < level_depth:
                self.order_type = 'insertion'
            elif snap_array[update_index][1] > level_depth:
                self.order_type = 'cancelation'
            else:
                pass
            snap_array[update_index][1] = level_depth 
            self.token=True
            self.position = update_index
        else:
            self.token = False
        return snap_array, pre_level_depth 

    def update_price_index_buy(self, level_depth, price_level, pre_level_depth):
        if not self.token:
            self.order_type = 3 if level_depth == 0 else self.order_type
            pre_level_depth = 0
            self.event_size = level_depth
            if price_level > self.bid_range[0]: 
                self.bid_range.insert(0,price_level) 
                self.snapshot_bid.insert(0,[price_level,level_depth]) 
                self.order_type = 1
                self.token = True
                self.position = 0
            elif price_level < self.bid_range[-1]: 
                self.token=False
                self.position = len(self.bid_range)
            else: 
                self.position = bisect.bisect(self.bid_range, price_level)
                if self.position == 0:
                    self.token=False
                    print("encountered problem ON BUY SIDE assigning correct bisect point for price level", price_level, "at position", self.position)
                else:
                    self.snapshot_bid.insert(self.position, [price_level, level_depth])
                    self.bid_range.insert(self.position, price_level)
                    self.order_type = 1
                    self.token=True
        return self.snapshot_bid, self.bid_range, pre_level_depth

    def update_price_index_sell(self, level_depth, price_level, pre_level_depth):
        if not self.token:
            self.order_type = 3 if level_depth == 0 else self.order_type
            pre_level_depth = 0
            self.event_size = level_depth
            if price_level < min(self.ask_range): 
                self.ask_range.insert(0, price_level) 
                self.snapshot_ask.insert(0, [price_level,level_depth]) 
                self.order_type = 1
                self.token = True
                self.position = 0
            elif price_level > max(self.ask_range): 
                self.token=False
                self.position = len(self.ask_range)
            else:
                self.position = bisect.bisect(self.ask_range, price_level) 
                if self.position == 0:
                    self.token=False
                    print("encountered problem ON SELL SIDE with assigning correct bisect point for price level", price_level, "at position", self.position)
                else: 
                    self.snapshot_ask.insert(self.position, [price_level, level_depth])
                    self.ask_range.insert(self.position, price_level)
                    self.order_type = 1
                    self.token=True
        return self.snapshot_ask, self.ask_range, pre_level_depth

    def update_snapshot_bid(self):
        self.bid_range = [self.snapshot_bid[i][0] for i in range(len(self.snapshot_bid))]
        return self.snapshot_bid, self.bid_range

    def update_snapshot_ask(self):
        self.ask_range= [self.snapshot_ask[i][0] for i in range(len(self.snapshot_ask)) ]
        return self.snapshot_ask, self.ask_range

    def trim_coordinator(self, position, bound):
        if position>bound:
            self.token = False
        else:
            pass
        return self.token

    def append_message_and_book(self, time,price_level):
        self.events.append([time, self.order_type, self.order_id, self.event_size, self.direction])
        temp_snap_bid = copy.deepcopy(self.snapshot_bid[:6])[::-1]
        temp_snap_ask = copy.deepcopy(self.snapshot_ask[:6])        
        self.history.append([time, temp_snap_bid + temp_snap_ask])

    # def append_snapshot_bid(self, time, price_level):
    #     mid_price = 0.5*(self.bid_range[0] + self.ask_range[0])
    #     temp_snap = copy.deepcopy(self.snapshot_bid[:6])
    #     spread = self.ask_range[0] - self.bid_range[0]
    #     self.bid_history.append([time, temp_snap])
    #     self.bid_events.append([time, self.order_type, price_level, self.event_size, self.position+1, mid_price, spread])

    # def append_snapshot_ask(self, time, price_level):
    #     mid_price = 0.5*(self.bid_range[0] + self.ask_range[0])
    #     spread = self.ask_range[0] - self.bid_range[0]
    #     temp_snap = copy.deepcopy(self.snapshot_ask[:6])
    #     self.ask_history.append([time, temp_snap])
    #     self.ask_events.append([time, self.order_type, price_level, self.event_size, self.position+1, mid_price, spread])
    
    # #def append_signed_book(self, time, price_level, side):
    # #    mid_price = 0.5*(self.bid_range[0] + self.ask_range[0])
    #     spread = self.ask_range[0] - self.bid_range[0]
    #     sign = hf.set_sign(self.event_size, side, self.order_type)
    #     self.event_size *= sign
    #     self.position = hf.set_signed_position(self.position, side)
    #     temp_snap_bid = [[i[0],-1*i[1]] for i in copy.deepcopy(self.snapshot_bid[:6])][::-1]
    #     temp_snap_ask = copy.deepcopy(self.snapshot_ask[:6])        
    #     self.signed_history.append([time, temp_snap_bid + temp_snap_ask])
    #     self.signed_events.append([time, self.order_type, price_level, self.event_size, self.position, side, mid_price, spread])

    def check_mkt_can_overlap(self, events, order_type):
        ## notes this will have to be reworked to addressed partial deletions
        ## it explains a lot about market order merssage being split but having the same
        ## arrival time :(
        set_of_order_of_arrival = [[4, 2], [4, 3], [2, 4], [4, 3]]
        if len(events)>2:
            last_two = events[-2:]
            orders = [last_two[0][1],last_two[1][1]]
            sizes = [last_two[0][3], last_two[1][3]]
            if sizes[0] - sizes[1] == float(0):
                if order_type == 4:
                    #print("1a.market message initiated deleteing", events[-2])
                    del events[-2]
                elif (order_type == 2)  and (orders[0] == 4): 
                    #print("1b. cancelation message initiated", events[-1])
                    del events[-1]
                else:
                    #print("1c.sizes agree but neither mkt,can or can,mkt received")
                    pass
            else:
                #print("sizes don't agree", sizes)
                pass

    #### Accessors #####
    def last_inserted_order(self, side="signed"): #these args side, 
        out = []
        if side == "buy":
            event_list = self.bid_events
        elif side == "sell":
            event_list = self.ask_events
        else:
            event_list = self.signed_events

        len_check = min(len(event_list),30)

        for i in range(len(event_list[-len_check:])):
            if event_list[::-1][i][1] == "insertion":
                out = event_list[::-1][i]
                break
            else:
                out = []
                print('no LO was found in last 30 messages')
        return out


    def last_canceled_order(self, side="signed"):
        out = []
        if side == "buy":
            event_list = self.bid_events
        elif side == "sell":
            event_list = self.ask_events
        else:
            event_list = self.signed_events

        len_check = min(len(event_list),30)

        for i in range(len(event_list[-len_check:])):
            if event_list[::-1][i][1] == "insertion":
                out = event_list[::-1][i]
                break
            else:
                out = []
                print('no CO was found in last 30 messages')
        return out


    def last_market_order(self, side="signed"):
        out = []
        if side == "buy":
            event_list = self.bid_events
        elif side == "sell":
            event_list = self.ask_events
        else:
            event_list = self.signed_events

        len_check = min(len(event_list),30)

        for i in range(len(event_list[-len_check:])):
            if event_list[::-1][i][1] == "market":
                out = event_list[::-1][i]
                break
            else:
                out = []
                print('no MO was found in last 30 messages')
        return out

    def last_orderbook_image(self, side="signed"):
        if side == "buy":
            orderbook_list = self.bid_history
        elif side == "sell":
            orderbook_list = self.ask_history
        else:
            orderbook_list = self.signed_history

        return orderbook_list[-1]

    def last_market_depth(self, side, pos_range='all'): 
        if side == "buy":
            orderbook_snap = self.bid_history[-1][1]
        elif side =="sell":
            orderbook_snap = self.ask_history[-1][1]
        else:
            print("error, no side selected. please pick bid or ask")
        if pos_range == 'all':
            pass
        else:
            orderbook_snap = orderbook_snap[:pos_range]
        depth = 0    
        for i in range(len(orderbook_snap)):
            depth += orderbook_snap[i][1] * orderbook_snap[i][0]
        return depth     

def UpdateSnapshot_bid_Seq(hist_obj, time, side, price_level, level_depth, pre_level_depth, price_match_index):
    hist_obj.snapshot_bid, pre_level_depth = hist_obj.update_level_depth(hist_obj.snapshot_bid, level_depth, price_match_index, pre_level_depth)        
    hist_obj.snapshot_bid = hist_obj.remove_price_level(hist_obj.snapshot_bid, level_depth, price_match_index) # needs price range update, 
    hist_obj.snapshot_bid, hist_obj.bid_range, pre_level_depth = hist_obj.update_price_index_buy(level_depth, price_level, pre_level_depth)
    hist_obj.snapshot_bid, hist_obj.bid_range = hist_obj.update_snapshot_bid()
    hist_obj.token = hist_obj.trim_coordinator(hist_obj.position, 5)
    if hist_obj.token:
        hist_obj.append_snapshot_bid(time, price_level)
        hist_obj.append_signed_book(time, price_level, side)
        hist_obj.check_mkt_can_overlap(hist_obj.bid_events, hist_obj.order_type)
        hist_obj.check_mkt_can_overlap(hist_obj.signed_events, hist_obj.order_type)
        if hist_obj.bid_events[-1][-1] > 100:
            print("it happened on this message", hist_obj.bid_events[-1])
            print("the type of addition was: ", hist_obj.order_type)
            print("   ")
            print("the previous bid event was:", hist_obj.bid_events[-2])
            print("the previous ask event was:", hist_obj.ask_events[-2])
            print("the previous bid book looked like", hist_obj.bid_history[-2])
            print("the previous ask book looked like", hist_obj.ask_history[-2])
            print("the bid book looks like NOW:", hist_obj.bid_history[-1])
            print("the ask book looks like NOW:", hist_obj.ask_history[-1])

def UpdateSnapshot_ask_Seq(hist_obj, time, side, price_level, level_depth, pre_level_depth, price_match_index):
    hist_obj.snapshot_ask, pre_level_depth = hist_obj.update_level_depth(hist_obj.snapshot_ask, level_depth, price_match_index, pre_level_depth)        
    hist_obj.snapshot_ask = hist_obj.remove_price_level(hist_obj.snapshot_ask, level_depth, price_match_index) # needs price range update, 
    hist_obj.snapshot_ask, hist_obj.ask_range, pre_level_depth = hist_obj.update_price_index_sell(level_depth, price_level, pre_level_depth)
    hist_obj.snapshot_ask, hist_obj.ask_range = hist_obj.update_snapshot_ask()
    hist_obj.token = hist_obj.trim_coordinator(hist_obj.position, 5)
    if hist_obj.token:
        hist_obj.append_snapshot_ask(time, price_level)
        hist_obj.append_signed_book(time, price_level, side)
        hist_obj.check_mkt_can_overlap(hist_obj.ask_events, hist_obj.order_type)
        hist_obj.check_mkt_can_overlap(hist_obj.signed_events, hist_obj.order_type)
        if hist_obj.ask_events[-1][-1] > 100:
            print("it happened on this message", hist_obj.ask_events[-1])
            print("the type of addition was: ", hist_obj.order_type)
            print("   ")
            print("the previous bid event was:", hist_obj.bid_events[-2])
            print("the previous ask event was:", hist_obj.ask_events[-2])
            print("the previous bid book looked like", hist_obj.bid_history[-2])
            print("the previous ask book looked like", hist_obj.ask_history[-2])
            print("the bid book looks like NOW:", hist_obj.bid_history[-1])
            print("the ask book looks like NOW:", hist_obj.ask_history[-1])

def price_match(x,y):
    if y == x:
        return True
    else:
        return False 

# def get_min_dec(min_currency_denom, min_asset_value):
#     min_tradable_amount = min_currency_denom/min_asset_value
#     min_dec = 0
#     while min_tradable_amount < 1:
#         min_tradable_amount*=10
#         min_dec += 1
#         if min_dec_out > 15:
#             break 
#     return min_dec_out




