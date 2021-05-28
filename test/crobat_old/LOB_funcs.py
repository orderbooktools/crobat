import pandas as pd
import copy
from bisect import bisect

# LOB_funcs.py contains the functions that are used in the class that interacts with the WebSocket. 
# The initial functions price
def price_match(x,y):
    if y == x:
        return True
    else:
        return False       
#This function converts my ...
def convert_array_to_list_dict(history, pos_limit=5):
    temp_dict = {}
    return_list = []
    for i in range(len(history)):
        temp_dict.update({"time":history[i][0]})
        for n in range(pos_limit):
            temp_dict.update({str(n):history[i][1][n][1]})
            return_list.append(temp_dict)
            temp_dict = {}
    return return_list

def pd_excel_save(title,hist_obj_dict):
    hist_obj_df = pd.DataFrame(hist_obj_dict)
    hist_obj_df = hist_obj_df[1:]
    writer = pd.ExcelWriter(title, engine='xlsxwriter')
    hist_obj_df.to_excel(writer, sheet_name='Sheet1')
    writer.save()

class history(object):
    # init creates the object that I will start modifying 
    def __init__(self):
        self.bid_history=[]#snapshot.x_history #an empty list that will hold the history of the list tuples we're going to be working on 
        self.ask_history=[]
        self.snapshot_bid = []# snapshot.x #an empty list that will hold the current instance of the list tuples we're going to be working on 
        self.snapshot_ask = []
        self.bid_events = []# list two elemtnts classification, ,price, and size ['insertion', 0.3105 XRP-USD, 12345 XRP] 
        self.ask_events = []
        self.order_type = None
        self.token = False
        self.position = 0
        self.event_size = 0
        self.snapshot_token = False

    # event that will happen when a market order arrives defined in the ticker class, on message function
    def add_market_order_message(self, message, events):
        index_start = 0
        index_stop = len(events) 
        events.append(message)
        if index_stop < 2:
            pass
        else:
            index_start = max(0,len(events)-3)
            index_stop  = len(events)-1

        for i in range(index_start, index_stop):
            if events[i][0] == events[i-1][0]:
                events[i][3] += events[i-1][3]
                del events[i-1]
        return events

    # functions that modify the objects in __init__ on the arrival of L2 update. 
    def remove_price_level(self, snap_array, level_depth, match_index):
        if level_depth == 0 and match_index:            
            snap_array = [[snap_array[i][0], snap_array[i][1]] for i in range(len(snap_array)) if snap_array[i][1] != 0]
            self.token=True
        return snap_array

    def update_level_depth(self, snap_array, level_depth, match_index, pre_level_depth):
        if match_index: 
            update_index = match_index[0] # position of where the change happened
            self.event_size = abs(snap_array[update_index][1] - level_depth)
            pre_level_depth = snap_array[update_index][1]
            if snap_array[update_index][1] < level_depth:
                self.order_type = 'insertion'
            elif snap_array[update_index][1] > level_depth:
                self.order_type = 'cancelation'
            else:
                pass
            snap_array[update_index][1] = level_depth #sets the updated volm
            self.token=True
            self.position = update_index
        else:
            self.token = False
        return snap_array, pre_level_depth 

    def update_price_index_buy(self, level_depth, price_level, pre_level_depth):
        if not self.token:
            self.order_type = 'cancelation' if level_depth == 0 else self.order_type
            pre_level_depth = 0
            self.event_size = level_depth
            if price_level > max(self.bid_range): #it the message brought back a price level that was not in the original self.x we update it in our self.x_range, and self.x lists
                self.bid_range.append(price_level) # update the x_range
                self.snapshot_bid.append([price_level,level_depth]) # add the new pricelevel, and volm pair to self.x
                self.order_type = "insertion"
                self.token = True
                self.position = 0
            elif price_level < min(self.bid_range): #when it's below the range, we are not interested in it (orderbook stuff dwai)
                self.token=False
                self.position = None
            else: # sometimes I get a new price that is between the min and max of x_range, but not a member of the list, this says that its okay to add.             
                self.bid_range.append(price_level) #adds the new price to x_range
                sorted(self.bid_range)[::-1]
                sorted(self.snapshot_bid)[::-1]
                self.bid_range= list(set(self.bid_range))
                self.position = bisect(self.bid_range, price_level)
                self.snapshot_bid[self.position:self.position] = [[price_level, level_depth]]
                self.order_type = "insertion"
                self.token=True
        return self.snapshot_bid, self.bid_range, pre_level_depth

    def update_price_index_sell(self, level_depth, price_level, pre_level_depth):
        if not self.token:
            self.order_type = 'cancelation' if level_depth == 0 else self.order_type
            pre_level_depth = 0
            self.event_size = level_depth
            if price_level < min(self.ask_range): #it the message brought back a price level that was not in the original self.x we update it in our self.x_range, and self.x lists
                self.ask_range.append(price_level) # update the x_range
                self.snapshot_ask.append([price_level,level_depth]) # add the new pricelevel, and volm pair to self.x
                self.order_type = "insertion"
                self.token = True
                self.position = 0
            elif price_level > max(self.ask_range): #when it's below the range, we are not interested in it (orderbook stuff dwai)
                self.token=False
                self.position = None
            else: #check to see that I have not alread made a change            
                self.ask_range.append(price_level) #adds the new price to x_range
                sorted(self.ask_range)
                sorted(self.snapshot_ask)
                self.ask_range = list(set(self.ask_range))
                self.position = bisect(self.ask_range, price_level)
                self.snapshot_ask[self.position:self.position] = [[price_level, level_depth]]
                self.order_type = "insertion"
                self.token=True
                #print("the ask updated position is", position)
        return self.snapshot_ask, self.ask_range, pre_level_depth

    def update_snapshot_bid(self):
        sorted(self.snapshot_bid)#.sort(key=lambda x: x[0])[::-1]
        self.snapshot_bid[::-1]# = snapshot_array[::-1]
        self.bid_range = [self.snapshot_bid[i][0] for i in range(len(self.snapshot_bid))]
        return self.snapshot_bid, self.bid_range

    def update_snapshot_ask(self):
        sorted(self.snapshot_ask)#.sort(key=lambda x: x[0])[::-1]
        self.ask_range= [self.snapshot_ask[i][0] for i in range(len(self.snapshot_ask)) ]
        return self.snapshot_ask, self.ask_range

    def trim_coordinator(self, position, bound):
        if position>bound:
            self.token = False
        else:
            pass
        return self.token

    def append_snapshot_bid(self, time, price_level):
        mid_price = 0.5*(max(self.bid_range) + min(self.ask_range))
        temp_snap = copy.deepcopy(self.snapshot_bid[:5])
        spread = min(self.ask_range) - max(self.bid_range)
        self.bid_history.append([time, temp_snap])
        self.bid_events.append([time, self.order_type, price_level, self.event_size, self.position, mid_price, spread])

    def append_snapshot_ask(self, time, price_level):
        mid_price = 0.5*(max(self.bid_range) + min(self.ask_range))
        spread = min(self.ask_range) - max(self.bid_range)
        temp_snap = copy.deepcopy(self.snapshot_ask[:5])
        self.ask_history.append([time, temp_snap])
        self.ask_events.append([time, self.order_type, price_level, self.event_size, self.position, mid_price, spread])

    def check_mkt_can_overlap(self, events):
        set_of_order_of_arrival = [['market', 'cancelation'],['cancelation', 'market']]
        if len(events)>2:
            last_two = events[-2:]
            orders = [last_two[0][1],last_two[1][1]]
            sizes = [last_two[0][3], last_two[1][3]]
            if (sizes[0] == sizes[1]) and (orders in set_of_order_of_arrival):
                i = orders.index('cancelation') -2
                del events[i]
    
    def check_snapshot(self):
        if self.snapshot_token:
            pass
        else:
            self.bid_history=[]#snapshot.x_history #an empty list that will hold the history of the list tuples we're going to be working on 
            self.ask_history=[]
            self.snapshot_bid = []# snapshot.x #an empty list that will hold the current instance of the list tuples we're going to be working on 
            self.snapshot_ask = []
            self.bid_events = []# list two elemtnts classification, ,price, and size ['insertion', 0.3105 XRP-USD, 12345 XRP] 
            self.ask_events = []
            self.order_type = None
            self.token = False
            self.position = 0
            self.event_size = 0
            self.snapshot_token = False

def UpdateSnapshot_bid_Seq(hist_obj, time, side, price_level, level_depth, pre_level_depth, price_match_index):
    hist_obj.snapshot_bid, pre_level_depth = hist_obj.update_level_depth(hist_obj.snapshot_bid, level_depth, price_match_index, pre_level_depth)        
    hist_obj.snapshot_bid = hist_obj.remove_price_level(hist_obj.snapshot_bid, level_depth, price_match_index) # needs price range update, 
    hist_obj.snapshot_bid, hist_obj.bid_range, pre_level_depth = hist_obj.update_price_index_buy(level_depth, price_level, pre_level_depth)
    hist_obj.snapshot_bid, hist_obj.bid_range = hist_obj.update_snapshot_bid()
    hist_obj.token = hist_obj.trim_coordinator(hist_obj.position, 5)
    if hist_obj.token:
        hist_obj.append_snapshot_bid(time, price_level)
        hist_obj.check_mkt_can_overlap(hist_obj.bid_events)

def UpdateSnapshot_ask_Seq(hist_obj, time, side, price_level, level_depth, pre_level_depth, price_match_index):
    hist_obj.snapshot_ask, pre_level_depth = hist_obj.update_level_depth(hist_obj.snapshot_ask, level_depth, price_match_index, pre_level_depth)        
    hist_obj.snapshot_ask = hist_obj.remove_price_level(hist_obj.snapshot_ask, level_depth, price_match_index) # needs price range update, 
    hist_obj.snapshot_ask, hist_obj.ask_range, pre_level_depth = hist_obj.update_price_index_sell(level_depth, price_level, pre_level_depth)
    hist_obj.snapshot_ask, hist_obj.ask_range = hist_obj.update_snapshot_ask()
    hist_obj.token = hist_obj.trim_coordinator(hist_obj.position, 5)
    if hist_obj.token:
        hist_obj.append_snapshot_ask(time, price_level)
        hist_obj.check_mkt_can_overlap(hist_obj.ask_events)