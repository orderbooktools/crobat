import asyncio, time
#from postgres.main import input_args
from datetime import datetime
import copra.rest
from copra.websocket import Channel, Client
import pandas as pd
# import orderbook
# import orderbook_helpers
#import filesave
from .orderbook import *
from .orderbook_helpers import * 
import gc
import numpy as np
from .filesave import *
from sys import exit

pd.set_option('display.max_columns', 500)

class L2_Update(Client):
    """
    class that inherits from copra.websocket Client. Contains methods for
    receiving and interpretting l2_update and ticker messages. 
    
    Attributes
    ----------
    time_now : datetime 
        local UTC time when the class initializes. used for the timeout.
    
    hist : history class object
        instance of the history object from LOBf_funcs.py
    
    currency_pair : str
        default 'ETH-USD'
        currency pair to record, inherited from class input_args
    
    position_range : int
        default 5
        position range of interest, inherited from class input_args
    
    recording_duration : int
        default 5
        recording duration in seconds, (time between the initialization of the class
        and the time of the last message received). 
        
    Methods
    -------
    __init__
        initializes attributes and inherits attributes from input_args, 
        loop and channel. 
    
    on_open 
        calls the method on_open from Client
    
    on_message
        interprets and executes messages received from the websocket

    on_close
        excutes steps to close the connection to the websocket and export
        the collected data.    
    """
    def __init__(self, loop, channel, input_args):
        """
        init method
        
        Paramaters
        ----------
        loop : Asyncio loop object
            Loop object that is passed by copra (tbh i dont understand it)                
        channel : copra.websocket Channel object
            channel settings passed L2_Update class

        input_args : class input_args object
            input arguments and recording settings. 

        Returns
        -------
        None
        
        Raises
        ------
        None 
            
        """
        self.time_now = datetime.utcnow() #initial start time
        self.hist = history()
        self.recording_settings = input_args
        self.snap_received = False
        super().__init__(loop, channel) # something about a parent class sending attributes to the child class (Ticker)

    def on_open(self):
        """
        calls inherited on_open method from copra.websocket Client class
        
        Parameters
        ----------
        None
        
        Returns
        -------
        None

        Raises
        ------
        None

        See Also
        --------
        put a link to copra's on_open method
        """
        print("Let's count the L2 messages!", self.time_now)
        super().on_open() # inheriting things from the parent class who really knows    

    def on_message(self, msg):
        """
        calls inherited on_message method from copra.websocket Client class.
        General section where one decides how incoming messages are handled.
        
        Parameters
        ----------
        msg : dict
            json message from the websocket feed. see 
            link to coinbase websocket feed, for details
            on the layout of each message. 
        
        Returns
        -------
        None
        
        Raises
        ------
        TypeError
            If the message is not a dictionary, the key cannot be called.
    
            Needs further testing, will generally ignore message if it doesn't contain
            the key 'type'.
        """
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
                side = "bid" if msg['side'] == 'sell' else "ask"
                spread = best_ask - best_bid
                mid_price = 0.5*(best_bid + best_ask)
                position = -1 if side == 'sell' else 1
                size = np.around(float(msg['last_size']), decimals=self.min_dec)
                size_signed = size if side == "bid" else size*(-1)
                message = [time, 'market', float(msg['price']), size_signed, position, side, mid_price, spread]
                sided_message = [time, 'market', float(msg['price']), size, position, mid_price, spread]
                self.hist.signed_events = self.hist.add_market_order_message(message, self.hist.signed_events)
                self.hist.check_mkt_can_overlap(self.hist.signed_events,'market')
                if side == 'ask':
                    self.hist.ask_events = self.hist.add_market_order_message(sided_message, self.hist.ask_events)
                    self.hist.check_mkt_can_overlap(self.hist.ask_events, 'market')
                elif side == 'bid':
                    self.hist.bid_events = self.hist.add_market_order_message(sided_message, self.hist.bid_events)
                    self.hist.check_mkt_can_overlap(self.hist.bid_events, 'market')
                else:
                    print("unknown matched order")
            else:
                print("mkt order arrived but no snapshot received yet")

        if msg['type'] in ['l2update']:# update messages 
            time=datetime.strptime(msg['time'],'%Y-%m-%dT%H:%M:%S.%fZ') #from the message extract time
            changes = msg['changes'] #from the message extract the changes
            side = 'bid' if changes[0][0] == "buy" else "ask" #side in which the changes happend (don't worry its orderbook crap)
            price_level = float(changes[0][1]) #the position in x_range that the change is affecting
            level_depth = np.around( float(changes[0][2]), decimals=self.min_dec) #the value in x_volm that is changing
            pre_level_depth = 0 
            self.hist.token = False
            if side == "bid":
                price_match_index = list(filter(lambda x: price_match(self.hist.bid_range[x], price_level), range(len(self.hist.bid_range))))
                UpdateSnapshot_bid_Seq(self.hist, time, side, price_level, level_depth, pre_level_depth, price_match_index, self.recording_settings.position_range)
            elif side == "ask":
                price_match_index = list(filter(lambda x: price_match(self.hist.ask_range[x], price_level), range(len(self.hist.ask_range))))
                UpdateSnapshot_ask_Seq(self.hist, time, side, price_level, level_depth, pre_level_depth, price_match_index, self.recording_settings.position_range)                
            else:
                print("unknown message")

        if (datetime.utcnow() - self.time_now).total_seconds() > float(self.recording_settings.recording_duration):  # after 1 second has passed
            self.loop.create_task(self.close()) # ASyncIO nonsense

    def on_close(self, was_clean, code, reason):
        """
        calls on inherited method on_close from crobat.websocket Client class.
        Sequence of steps initiated after self.close() method is called.
        Creates the output files from the websocket session.

        Parameters
        ----------
        was_clean : bool
            True if the websocket connection was closed cleanly, else False.
        
        code : str 
            Connection code. 0 if clean 1 if error. need to look into this.    
        
        reason : str
            Reason the connection was closed. Look into this.

        Raises
        ------
            Happens in current crobat. The connection never gets instructed to 
            be closed. Gives rise to a warn error.   
        """
        print("Connection to server is closed")
        print(was_clean)
        print(code)
        print(reason)

        filesaver(self.hist,
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