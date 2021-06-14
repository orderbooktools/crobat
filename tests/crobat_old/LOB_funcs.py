import pandas as pd
import copy
from bisect import bisect
"""
LOB_funcs.py contains the functions that are used in the class that interacts
with the WebSocket. 
"""
def price_match(x,y):
    """
    Used in an index search lambda
    matches prices given as x with a price in the orderbook y 
    
    Parameters
    ---------- 
    x : float64
        price arriving from a message
    y : float64
        price to check in the orderbook
    
    Returns
    -------
    bool
        True if price was found
        False if price not found
    
    Raises
    ------
        None
        maybe TypeError if the == operator can't be used on two types?
    """
    if y == x:
        return True
    else:
        return False       


def convert_array_to_list_dict(history, pos_limit=5):
    """
    Passes history array and position limit to generate the a 
    list of dictionaries containing the single sided order book for position
    limit n the keys are:
    [time, position_limit , position_limit-1, ..., position_limit n-1]
    
    Parameters
    ----------
    history : array_list list of lists 
        see bid_history or ask_history in LOB_funcs.py 

    pos_limit : int
        position limit for the order book; default 5.

    Returns
    -------
        return_list : list of dict

    Raises
    ------
        TypeError
            if anything other than array or something subscriptable
            is passed it will not be able to iterate through it. 
    """
    temp_dict = {}
    return_list = []
    for i in range(len(history)):
        temp_dict.update({"time":history[i][0]})
        for n in range(pos_limit):
            temp_dict.update({str(n):history[i][1][n][1]})
            return_list.append(temp_dict)
            temp_dict = {}
    return return_list

def pd_excel_save(title, hist_obj_dict):
    """
    Generates the .xlsx file for a given list of dictionaries by first
    turning the list of dictionaries into a pandas dataframe and then
    using xlsxwriter to write to excel.

    Parameters
    ----------
    title : string
        title for the output file

    hist_obj_dict : list of dict
        list of dictionaries that will be turned to a pd.Dataframe

    Return
    ------
    None
    Outputs a .xlsx file

    Raises
    ------
    TypeError
        from pd.Dataframe() operation if the object passed isn't an array like
        object
    """
    hist_obj_df = pd.DataFrame(hist_obj_dict)
    hist_obj_df = hist_obj_df[1:]
    writer = pd.ExcelWriter(title, engine='xlsxwriter')
    hist_obj_df.to_excel(writer, sheet_name='Sheet1')
    writer.save()

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
        self.bid_events = []
        self.ask_events = []
        self.snapshot_bid = []
        self.snapshot_ask = []
        self.bid_events = []
        self.order_type = None
        self.token = False
        self.position = 0
        self.event_size = 0
        self.snapshot_token = False

    
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
            snap_array = [[snap_array[i][0], snap_array[i][1]] for i in range(len(snap_array)) if snap_array[i][1] != 0]
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
            if price_level > max(self.bid_range):
                self.bid_range.append(price_level) 
                self.snapshot_bid.append([price_level,level_depth]) 
                self.order_type = "insertion"
                self.token = True
                self.position = 0
            elif price_level < min(self.bid_range): 
                self.token=False
                self.position = None
            else: 
                self.bid_range.append(price_level) 
                sorted(self.bid_range)[::-1]
                sorted(self.snapshot_bid)[::-1]
                self.bid_range= list(set(self.bid_range))
                self.position = bisect(self.bid_range, price_level)
                self.snapshot_bid[self.position:self.position] = [[price_level, level_depth]]
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
                self.ask_range.append(price_level) 
                self.snapshot_ask.append([price_level,level_depth]) 
                self.order_type = "insertion"
                self.token = True
                self.position = 0
            elif price_level > max(self.ask_range): 
                self.token=False
                self.position = None
            else:    
                self.ask_range.append(price_level) 
                sorted(self.ask_range)
                sorted(self.snapshot_ask)
                self.ask_range = list(set(self.ask_range))
                self.position = bisect(self.ask_range, price_level)
                self.snapshot_ask[self.position:self.position] = [[price_level, level_depth]]
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
        sorted(self.snapshot_bid)
        self.snapshot_bid[::-1]
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
        sorted(self.snapshot_ask)
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
        mid_price = 0.5*(max(self.bid_range) + min(self.ask_range))
        temp_snap = copy.deepcopy(self.snapshot_bid[:5])
        spread = min(self.ask_range) - max(self.bid_range)
        self.bid_history.append([time, temp_snap])
        self.bid_events.append([
            time, self.order_type, price_level, self.event_size, self.position,
            mid_price, spread])

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
        mid_price = 0.5*(max(self.bid_range) + min(self.ask_range))
        spread = min(self.ask_range) - max(self.bid_range)
        temp_snap = copy.deepcopy(self.snapshot_ask[:5])
        self.ask_history.append([time, temp_snap])
        self.ask_events.append([
            time, self.order_type, price_level, self.event_size, self.position,
            mid_price, spread
            ])

    def check_mkt_can_overlap(self, events):
        """
        compares the recent events for changes interpretted as a cancelation
        against a recent market order. if the sizes are the same then the 
        cancelation event is deleted.

        Parameters
        ----------
            events : list of list
                event log of a single side.

        Returns
        -------
            None
        Raises
        ------
            None 
        """
        set_of_order_of_arrival = [
            ['market', 'cancelation'],
            ['cancelation', 'market']]
        if len(events)>2:
            last_two = events[-2:]
            orders = [last_two[0][1],last_two[1][1]]
            sizes = [last_two[0][3], last_two[1][3]]
            if (sizes[0] == sizes[1]) and (orders in set_of_order_of_arrival):
                i = orders.index('cancelation') -2
                del events[i]
        
    def check_snapshot(self):
        """
        artifact method that might be deleted. for now, checks for the
        snapshot_token to be True, and reinitilizes the history object
        if the snapshot token has not arrived.

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
        if self.snapshot_token:
            pass
        else:
            self.bid_history=[]
            self.ask_history=[]
            self.snapshot_bid = []
            self.bid_events = []
            self.ask_events = []
            self.order_type = None
            self.token = False
            self.position = 0
            self.event_size = 0
            self.snapshot_token = False

def UpdateSnapshot_bid_Seq(hist_obj, time, side, price_level, level_depth,
                           pre_level_depth, price_match_index):
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
    hist_obj.snapshot_bid = hist_obj.remove_price_level(hist_obj.snapshot_bid, level_depth, price_match_index) 
    hist_obj.snapshot_bid, hist_obj.bid_range, pre_level_depth = hist_obj.update_price_index_buy(level_depth, price_level, pre_level_depth)
    hist_obj.snapshot_bid, hist_obj.bid_range = hist_obj.update_snapshot_bid()
    hist_obj.token = hist_obj.trim_coordinator(hist_obj.position, 5)
    if hist_obj.token:
        hist_obj.append_snapshot_bid(time, price_level)
        hist_obj.check_mkt_can_overlap(hist_obj.bid_events)

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
    hist_obj.snapshot_ask = hist_obj.remove_price_level(hist_obj.snapshot_ask, level_depth, price_match_index) 
    hist_obj.snapshot_ask, hist_obj.ask_range, pre_level_depth = hist_obj.update_price_index_sell(level_depth, price_level, pre_level_depth)
    hist_obj.snapshot_ask, hist_obj.ask_range = hist_obj.update_snapshot_ask()
    hist_obj.token = hist_obj.trim_coordinator(hist_obj.position, 5)
    if hist_obj.token:
        hist_obj.append_snapshot_ask(time, price_level)
        hist_obj.check_mkt_can_overlap(hist_obj.ask_events)

if __name__ == '__main__':
    pass