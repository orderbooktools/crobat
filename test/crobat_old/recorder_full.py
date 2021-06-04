import asyncio, time
from datetime import datetime
import copra.rest
from copra.websocket import Channel, Client
import pandas as pd
from . import LOB_funcs as LOBf

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
        self.time_now = datetime.utcnow() 
        self.hist = LOBf.history()
        self.currency_pair = input_args.currency_pair
        self.position_range = input_args.position_range
        self.recording_duration = input_args.recording_duration
        super().__init__(loop, channel)

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
        super().on_open()   

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
            self.snapshot_token = True
            time = self.time_now
            self.hist.snapshot_bid = msg['bids'] 
            self.hist.snapshot_ask = msg['asks'] 
            self.hist.bid_range = [float(self.hist.snapshot_bid[i][0]) for i in range(len(self.hist.snapshot_bid))]
            self.hist.ask_range = [float(self.hist.snapshot_ask[i][0]) for i in range(len(self.hist.snapshot_ask))] 
            self.hist.bid_volm  = [float(self.hist.snapshot_bid[i][1]) for i in range(len(self.hist.snapshot_bid))] 
            self.hist.ask_volm  = [float(self.hist.snapshot_ask[i][1]) for i in range(len(self.hist.snapshot_ask))]
            self.hist.snapshot_bid = [[self.hist.bid_range[i], self.hist.bid_volm[i]] for i in range(len(self.hist.snapshot_bid))]
            self.hist.snapshot_ask = [[self.hist.ask_range[i], self.hist.ask_volm[i]] for i in range(len(self.hist.snapshot_ask))] 
            self.hist.bid_history.append([time, self.hist.snapshot_bid]) 
            self.hist.ask_history.append([time, self.hist.snapshot_ask]) 

        if msg['type'] in ['ticker']:
            time=datetime.strptime(msg['time'],'%Y-%m-%dT%H:%M:%S.%fZ') 
            event_size = float(msg['last_size'])
            best_bid = float(msg['best_bid'])
            best_ask = float(msg['best_ask'])
            spread = best_ask - best_bid
            side = msg['side']
            price = msg['price']
            position = 0
            order_type = 'market'
            mid_price = 0.5*(best_bid + best_ask)
            message = [time, order_type, price,
                        event_size, position, mid_price, spread]
            if side == 'buy':
                self.hist.ask_events = self.hist.add_market_order_message(
                    message, self.hist.ask_events)
            elif side == 'sell':
                self.hist.bid_events = self.hist.add_market_order_message(
                    message, self.hist.bid_events)
            else:
                print("unknown matched order")

        if msg['type'] in ['l2update']:
            time=datetime.strptime(msg['time'],'%Y-%m-%dT%H:%M:%S.%fZ')
            changes = msg['changes'] 
            side = changes[0][0] 
            price_level = float(changes[0][1]) 
            level_depth = float(changes[0][2]) 
            pre_level_depth = 0 
            self.hist.token=False
            if side == "buy":
                price_match_index = list(filter(
                    lambda x: LOBf.price_match(self.hist.bid_range[x], price_level),
                    range(len(self.hist.bid_range))))
                LOBf.UpdateSnapshot_bid_Seq(
                    self.hist, time, side, price_level,
                    level_depth, pre_level_depth, price_match_index)
            elif side == "sell":
                price_match_index = list(filter(
                    lambda x: LOBf.price_match(self.hist.ask_range[x], price_level),
                    range(len(self.hist.ask_range))))
                LOBf.UpdateSnapshot_ask_Seq(
                    self.hist, time, side, price_level,
                    level_depth, pre_level_depth, price_match_index)                
            else:
                print("unknown message")

        if (datetime.utcnow() - self.time_now).total_seconds() > self.recording_duration:  
            self.loop.create_task(self.close()) 

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
        final_bid_list = LOBf.convert_array_to_list_dict(
            self.hist.bid_history, self.position_range)
        final_ask_list = LOBf.convert_array_to_list_dict(
            self.hist.ask_history, self.position_range)

        title1 = "L2_orderbook_bid.xlsx"
        LOBf.pd_excel_save(title1, final_bid_list)

        title2 = "L2_orderbook_ask.xlsx"
        LOBf.pd_excel_save(title2, final_ask_list)

        title3 = "L2_orderbook_events_bid.xlsx"
        LOBf.pd_excel_save(title3, self.hist.bid_events)

        title4 = "L2_orderbook_events_ask.xlsx"        
        LOBf.pd_excel_save(title4, self.hist.ask_events)


def main():
    pass

if __name__ == '__main__':
    main()
