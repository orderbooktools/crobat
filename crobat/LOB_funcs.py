import pandas as pd
import copy
import bisect
import numpy as np
import orderbook_helpers as hf

class history(object):
    """
    Class that contains the attributes and operations associated with order
    book history

    Attributes
    ----------
    bid_history : list of list
        initializes as an empty list that will hold the history of the order 
        book states for the bid side.

    ask_history : list of list 
        initializes as an empty list that will hold the history of the order
        book states for the bid side.

    snapshot_bid : list of list
        initializes as an empty list that will contain the current snapshot
        as a list of lists for the bid side. 

    snapshot_ask : list of list
        initializes as an empty list that will contain the current snapshot
        as a list of lists for the ask side.

    bid_events : list of list
        initializes as an empty list that will contain the log of changes to
        the order book on the bid side.

    ask_events : list of list
        initializes as an empty list that will contain the log of changes to
        the order book on the ask side. 

    order_type : str
        initializes as None but contains the order_type derived from the
        message. The order types can be 'insertion', 'cancellation', 'market'

    token : bool
        initializes as False. Its the flag that determines whether the change
        to the order book is recorded in the log.

    position : int
        index position in the snapshot list where a change is occurring.
    
    event_size : float64
        event size passed from the message, also computed based on the type
        and size of the message. 

    snapshot token : bool
        flag that tells the L2_Update class that it has received the snapshot
        and can begin recording ticker and other operations to the order book.
        This exists because after subscribing you can receive market orders
        and order book changes before having a snapshot to commit changes to. 
    
    Methods
    -------
    add_market_order_message(message, events)
        adds an aggregate market order at a unique timestamp to the list of
        events. 

    remove_price_level(snap_array, level_depth, match_index)
        removes the price level in the snapshot array (snap_array )provided
        it was found and saved in the match_index.

    update_level_depth(snap_array, level_depth, match_index,
                       pre_level_depth)
        updates the level depth of a found price level.

    update_price_index_buy(level_depth, price_level, pre_level_depth)
        updates the list of available prices, and snapshot for the bid side

    update_price_index_sell(level_depth, price_level, pre_level_depth)
        updates the list of available prices, and snapshot for the ask side

    update_snapshot_bid()
        updates the bid snapshot, used as a check most of the time.

    update_snapshot_ask()
        updates the ask snapshot, used as a check most of the time.

    trim_coordinator(position, bound)
        sets self.token to True the order book change position is within the bound.

    append_snapshot_bid(time, price_level)
        appends the current snapshot to the self.bid_history list,
        appends the current event to the self.bid_events list.

    append_snapshot_ask(time, price_level)
        appends the current snapshot to the self.ask_history list,
        appends the current event to the self.ask_events list. 

    check_mkt_can_overlap(events)
        compares the recent events for changes interpretted as a cancelation
        against a recent market order. if the sizes are the same then the 
        cancelation event is deleted.

    check_snapshot()
        artifact method that might be deleted. for now, checks for the
        snapshot_token to be True, and reinitilizes the history object
        if the snapshot token has not arrived.
    """
    def __init__(self):
        """
        Generates the attributes for the class (see Attributes section)

        Parameters
        ----------
            None

        Returns
        -------
            None

        Raises
        ------
            None

        """
        self.bid_history=[]
        self.ask_history=[]
        self.signed_history = []
        self.snapshot_bid = []
        self.snapshot_ask = []
        self.snapshot_signed = []
        self.bid_events = []
        self.ask_events = []
        self.signed_events = []
        self.order_type = None
        self.token = False
        self.position = 0
        self.event_size = 0
        #self.bid_price_hist = []
        #self.ask_price_hist = []
        #self.signed_price_hist = []

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
        self.snapshot_signed = [[i[0], -1*i[1]] for i in self.snapshot_bid][::-1] + self.snapshot_ask
        self.bid_history.append([time, self.snapshot_bid]) 
        self.ask_history.append([time, self.snapshot_ask]) 
        self.signed_history.append([time, self.snapshot_signed])
        #print(self.snapshot_bid)
        #self.round_digits = 0.01/self.ask_range[-1] # smallest rize i'll allow
    def add_market_order_message(self, message, events):
        """
        Adds an aggregate market order at a unique timestamp to the list of
        events.

        Parameters
        ----------
            message : list
                Message generated by the market order message.
            
            events : list of list 
                Events being compared to the market order message.

        Returns
        -------
            events : list of list
                Trimmed list of events. 

        Raises
        ------
            IndexError 
                Hopefully the passes I have added won't raise anything but
                events list isn't long enough, an IndexError may arise.
        """

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
        """
        Removes the price level in the snapshot array (snap_array) provided
        it was found and saved in the match_index.
        
        Parameters
        ----------
            snap_array : list of list
                Snapshot array being edited.
            
            level_depth : float64
                level depth passed through from the message, should be 0

            match_index : list either [] or [int]
                an empty or non empty list containing the position where a price
                was found.

        Returns
        -------
            snap_array : list of list
                snapshot array where the prices with level depth of 0
                have been removed.

        Raises
        ------
            IndexError
                Shouldn't happen but if someone passes something other than an array into
                this function, it will have issues iterating through the snapshot. 
        """
        if level_depth == 0 and match_index:            
            del snap_array[match_index[0]]
            self.token=True
        return snap_array

    def update_level_depth(self, snap_array, level_depth, match_index, pre_level_depth):
        """
        updates the level depth of a found price level. Computes self.event_size, assigns
        self.order_type, self.Token, and self.position based on the type of event.  

        Parameters
        ----------
            snap_array : list of list
                Snapshot array being edited.

            level_depth : float64
                level depth passed through from the message.
    
            match_index : list either [] or [int]
                an empty or non empty list containing the position where a
                price was found.
            
            pre_level_depth : floa64
                level depth before the operation began. default 0
                changes to the level_depth of the found price level. 

        Returns
        -------
            snap_array : list of list 
                snapshot array with the new level depth

            pre_level_depth : float64
                pre-level depth to compute partial insertions or cancelations.

        Raises
        ------
            IndexError
                If match_index isn't found in snapshot array, 
        """
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
        """
        updates the list of available prices, and snapshot for the bid side.
        Alters snapshot_bid by inserting a new price level. 
        
        Checks first to see that there was not another change before continuing.
        Computes self.event_size, assigns self.order_type, self.Token, and
        self.position based on the type of event. 

        Parameters
        ----------
            level_depth : float64
                level depth passed through from the message.
        
            price_level : float64
                price level to insert into the snapshot. 

            pre_level_depth : floa64
                level depth before the operation began. default 0
                changes to the level_depth of the found price level.       

        Returns
        -------
            self.snapshot_bid : list of lists
                updated snapshot bid

           self.bid_range : list of float64
                updated list of prices 

            pre_level_depth : float64
                pre-level depth to compute partial insertions or cancelations.

        Raises
        ------
            None (that I know of)
                
        """
        if not self.token:
            self.order_type = 'cancelation' if level_depth == 0 else self.order_type
            pre_level_depth = 0
            self.event_size = level_depth
            if price_level > self.bid_range[0]: 
                self.bid_range.insert(0,price_level) 
                self.snapshot_bid.insert(0,[price_level,level_depth]) 
                self.order_type = "insertion"
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
                    self.order_type = "insertion"
                    self.token=True
        return self.snapshot_bid, self.bid_range, pre_level_depth

    def update_price_index_sell(self, level_depth, price_level, pre_level_depth):
        """
        updates the list of available prices, and snapshot for the ask side.
        Alters snapshot_ask by inserting a new price level. 
        
        Checks first to see that there was not another change before continuing.
        Computes self.event_size, assigns self.order_type, self.Token, and
        self.position based on the type of event. 

        Parameters
        ----------
            level_depth : float64
                level depth passed through from the message.
        
            price_level : float64
                price level to insert into the snapshot. 

            pre_level_depth : floa64
                level depth before the operation began. default 0
                changes to the level_depth of the found price level.       

        Returns
        -------
            self.snapshot_ask : list of lists
                updated snapshot bid

           self.ask_range : list of float64
                updated list of prices 

            pre_level_depth : float64
                pre-level depth to compute partial insertions or cancelations.

        Raises
        ------
            None (that I know of)
                
        """
        if not self.token:
            self.order_type = 'cancelation' if level_depth == 0 else self.order_type
            pre_level_depth = 0
            self.event_size = level_depth
            if price_level < min(self.ask_range): 
                self.ask_range.insert(0, price_level) 
                self.snapshot_ask.insert(0, [price_level,level_depth]) 
                self.order_type = "insertion"
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
                    self.order_type = "insertion"
                    self.token=True
        return self.snapshot_ask, self.ask_range, pre_level_depth

    def update_snapshot_bid(self):
        """
        updates the bid snapshot, used as a check most of the time. 
        Altesets self.token to True the order book change position is within the bound.rs self.snapshot_bid and self.bid_range by sorting 

        Parameters
        ----------
            None

        Returns
        -------
            self.snapshot_bid : list of lists
                sorted snapshot bid

           self.bid_range : list of float64
                sorted list of prices 

        Raises
        ------
            None       
        """
        self.bid_range = [self.snapshot_bid[i][0] for i in range(len(self.snapshot_bid))]
        return self.snapshot_bid, self.bid_range

    def update_snapshot_ask(self):
        """
        updates the ask snapshot, used as a check most of the time. 
        Alters self.snapshot_ask and self.ask_range by sorting 

        Parameters
        ----------
            None

        Returns
        -------
            self.snapshot_ask : list of lists
                sorted snapshot bid

           self.ask_range : list of float64
                sorted list of prices 

        Raises
        ------
            None       
        """
        self.ask_range= [self.snapshot_ask[i][0] for i in range(len(self.snapshot_ask)) ]
        return self.snapshot_ask, self.ask_range

    def trim_coordinator(self, position, bound):
        """
        sets self.token to True the order book change position is within the bound.

        Parameters
        ----------
            position : int
                position where the change has occurred.

            bound : int
                position limit being checked against. 

        Returns
        -------
            self.token : bool
                True if position where the change occurred within bounds. 
        Raises
        ------
            TypeError
                If position is None or not an int it will throw this error.       
        """
        if position>bound:
            self.token = False
        else:
            pass
        return self.token

    def append_snapshot_bid(self, time, price_level):
        """
        appends the current snapshot to the self.bid_history list,
        appends the current event to the self.bid_events list.
        Alters self.bid_history, self.bid_events

        Parameters
        ----------
            time : datetime object
                timestamp when the message arrived.

            price_level : float64
                price level from  the message.

        Returns
        -------
            None
        Raises
        ------
            None 
        """
        mid_price = 0.5*(self.bid_range[0] + self.ask_range[0])
        temp_snap = copy.deepcopy(self.snapshot_bid[:6])
        spread = self.ask_range[0] - self.bid_range[0]
        self.bid_history.append([time, temp_snap])
        self.bid_events.append([time, self.order_type, price_level, self.event_size, self.position+1, mid_price, spread])

    def append_snapshot_ask(self, time, price_level):
        """
        appends the current snapshot to the self.ask_history list,
        appends the current event to the self.ask_events list.
        Alters self.ask_history, self.ask_events.

        Parameters
        ----------
            time : datetime object
                timestamp when the message arrived.

            price_level : float64
                price level from  the message.

        Returns
        -------
            None
        Raises
        ------
            None 
        """
        mid_price = 0.5*(self.bid_range[0] + self.ask_range[0])
        spread = self.ask_range[0] - self.bid_range[0]
        temp_snap = copy.deepcopy(self.snapshot_ask[:6])
        self.ask_history.append([time, temp_snap])
        self.ask_events.append([time, self.order_type, price_level, self.event_size, self.position+1, mid_price, spread])
    
    def append_signed_book(self, time, price_level, side):
        """
        Appends the current snapshot to the self.signed_history list,
        appends the current event to the self.signed_events list.
        Alters self.signed_history, self.signed_events.

        Parameters
        ----------
            time : datetime object
                timestamp when the message arrived.

            price_level : float64
                price level from  the message.

            side : str 
                bid or ask

        Returns
        -------
            None
        Raises
        ------
            None 
        """
        mid_price = 0.5*(self.bid_range[0] + self.ask_range[0])
        spread = self.ask_range[0] - self.bid_range[0]
        sign = hf.set_sign(self.event_size, side, self.order_type)
        self.event_size *= sign
        self.position = hf.set_signed_position(self.position, side)
        temp_snap_bid = [[i[0],-1*i[1]] for i in copy.deepcopy(self.snapshot_bid[:6])][::-1]
        temp_snap_ask = copy.deepcopy(self.snapshot_ask[:6])        
        self.signed_history.append([time, temp_snap_bid + temp_snap_ask])
        self.signed_events.append([time, self.order_type, price_level, self.event_size, self.position, side, mid_price, spread])

    def check_mkt_can_overlap(self, events, order_type):
        """
        Checks recent events for matching market overlap and cancellation
        messages. 

        Parameters
        ----------
            events : list of list
                events that we will check.
            
            order_type : str
                current order type that is being checked against.
            
        Returns
        -------
            None
            Edits : param events
        
        Raises
        ------
            None ?
        """
        set_of_order_of_arrival = [['market', 'cancelation'],['cancelation', 'market']]
        if len(events)>2:
            last_two = events[-2:]
            orders = [last_two[0][1],last_two[1][1]]
            sizes = [last_two[0][3], last_two[1][3]]
            if sizes[0] - sizes[1] == float(0):
                if order_type == 'market':
                    #print("1a.market message initiated deleteing", events[-2])
                    del events[-2]
                elif (order_type == 'cancelation') and (orders[0] == 'market'):
                    #print("1b. cancelation message initiated", events[-1])
                    del events[-1]
                else:
                    #print("1c.sizes agree but neither mkt,can or can,mkt received")
                    pass
            else:
                #print("sizes don't agree", sizes)
                pass

def UpdateSnapshot_bid_Seq(hist_obj, time, side, price_level, level_depth, pre_level_depth, price_match_index):
    """
    Sequence of class methods executed on an instance of the history object (hist_obj). 
    The order to try is:
        1. update level depth for a known price level 
        2. remove price level if the level depth = 0  
        3. add new price levels
    once the change has been committed you ensure the snapshot is sorted using
    update_snapshot_bid()
    then check if it is  change that is to be recorded in the bid_events variable
    using trim_coordinator(position, bound)
    if it is a change that is worth recording, thenappend the snapshot/event
    and check if there is market cancellation overlap. 

    Parameters
    ----------
        hist_obj : class
            An instance of the history class. 

        time : datetime object
                timestamp when the message arrived.
 
        side : str
            side passed from message can be bid or ask, buy or sell,
            depends on the verion.
        
        price_level : float64
            price level passed from the message.

        level_depth : float64
            level depth passed from the message. 

        pre_level_depth : float64
            typically 0 until changed by the sequence of methods.
        
        price_match_index : list of len 1 or 0
            contains a singular entry if there is price match otherwise empty.

    Returns
    -------
        See individual class methods for returns and object operations.

    Raises
    ------
        See individual class methods for raises. 
    """    
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
    """
    Sequence of class methods executed on an instance of the history object (hist_obj). 
    The order to try is:
        1. update level depth for a known price level 
        2. remove price level if the level depth = 0  
        3. add new price levels
    once the change has been committed you ensure the snapshot is sorted using
    update_snapshot_bid()
    then check if it is  change that is to be recorded in the bid_events variable
    using trim_coordinator(position, bound)
    if it is a change that is worth recording, thenappend the snapshot/event
    and check if there is market cancellation overlap. 

    Parameters
    ----------
        hist_obj : class
            An instance of the history class. 

        time : datetime object
                timestamp when the message arrived.
 
        side : str
            side passed from message can be bid or ask, buy or sell,
            depends on the verion.
        
        price_level : float64
            price level passed from the message.

        level_depth : float64
            level depth passed from the message. 

        pre_level_depth : float64
            typically 0 until changed by the sequence of methods.
        
        price_match_index : list of len 1 or 0
            contains a singular entry if there is price match otherwise empty.

    Returns
    -------
        See individual class methods for returns and object operations.

    Raises
    ------
        See individual class methods for raises. 
    """
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


class accessors(object):
    """
    Class of functions thats 

    Attributes
    ----------
        It should just inherit attributes from hist_object arg
    
    Methods
    -------
        last_inserted_order(side='signed')
            get the last limit insertion of the order book object
        
        last_canceled_order(side='signed')
            get the last canceled order from the order book object

        last_market_order(side='signed')
            get the last market order from the order book object

        last_orderbook_image(side="signed")
            get the last state of the full order book
        
        last_market_depth(side, pos_range='all')
            get the last market depth for a given side.
    """ 
    def __init__(self, object):
        """
        Initializes the class, by inheriting from the base class hist_object 
        hist_object is the instance of the order book class hist.

        Parameters
        ----------
            hist_object : class history 
                See class history in LOB_funcs.py 

        Returns
        -------
            None

        Raises
        ------
            None 
        """
        super().object.__init__()

    def last_inserted_order(self, side="signed"): #these args side, 
        """ 
        Accesses last inserted order.
        
        Parameters
        ----------
            side : str
                Can be "bid", "ask", or "signed".

        Returns
        -------
            out : list
                list in the format ofthe last limit insertion for a given side
                default signed.

        Raises
        ------
            None
        """
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
        """ 
        Accesses last canceled order.
        
        Parameters
        ----------
            side : str
                Can be "bid", "ask", or "signed".

        Returns
        -------
            out : list
                list in the format ofthe last limit cancellation for a given side
                default signed.

        Raises
        ------
            None
        """
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
        """ 
        Accesses last market order.
        
        Parameters
        ----------
            side : str
                Can be "bid", "ask", or "signed".

        Returns
        -------
            out : list
                list in the format ofthe last market fill for a given side
                default signed.

        Raises
        ------
            None
        """
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
        """ 
        Accesses latest order book image.
        
        Parameters
        ----------
            side : str
                Can be "bid", "ask", or "signed".

        Returns
        -------
            out : list
                list in the format of the latest order book state.
                Default = signed.

        Raises
        ------
            None
        """
        if side == "buy":
            orderbook_list = self.bid_history
        elif side == "sell":
            orderbook_list = self.ask_history
        else:
            orderbook_list = self.signed_history

        return orderbook_list[-1]

    def last_market_depth(self, side, pos_range='all'):
        """ 
        Accesses latest market depth for a given side, and position range.
        
        Parameters
        ----------
            side : str
                Can be "bid", "ask", or "signed".

            pos_range : str or int 
                haven't worked out what a good position range is.
                # remember the note about pos_range and pos_limit
                # please be more consistent. 

        Returns
        -------
            out : list
                list in the format ofthe last limit insertion for a given side
                default signed.

        Raises
        ------
            None
        """ 
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