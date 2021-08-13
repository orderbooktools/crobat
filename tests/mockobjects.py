"""
This file details the mock objects needed to test functions around crobat
the objects for now are going to be listed plainly such that I can use
module.object format to call the object. 
"""

from datetime import datetime

############################################################################
#                    Data Objects                                          #
############################################################################

class l2_update_messages(object):
    """
    class of l2_update messages based on their different types.

    Attributes
    ----------
        None

    Methods
    -------
        __init__

        create_message

        fetch_msg_from 

        idk i'll add more later    
    """

    def __init__(self, ws_feed_on=False):
        self.timenow = datetime.utcnow()
        if ws_feed_on:
            pass
        else:
            self.ticker_msg = {}
            self.l2update_msg = {}
            self.snapshot_msg = {
                "type": "snapshot",
                "product_id": "MKC-USD",
                "bids": [["0.99", "0.1"], ["0.98", "0.2"], ["0.97", "0.4"], ["0.96", "0.8"], ["0.95", "1.6"]],
                "asks": [["1.01", "0.1"], ["1.02", "0.2"], ["1.03", "0.4"], ["1.04", "0.8"], ["1.05", "1.6"]]
                }
        
    def gen_snapshot(self,**kwargs):
        """
        Class function to generate mock snapshots, with prespecified volume distributions.

        Parameters
        ----------
            **kwargs:
                bid_shape : string 
                    function disttribution or shape
                    can be in the set "custom" #will add more later 

                ask_shape : string
                    function disttribution or shape
                    can be in the set "custom" #will add more later 

                bid_shape_function : function
                    the customized function to be passed to generate custom
                    snapshots. Needs to have a single input for position,
                    and a single output. 
                
                ask_shape_function : function
                    the customized function to be passed to generate custom
                    snapshots. Needs to have a single input for position,
                    and a single output. 
        
        Returns
        -------
            self.snapshot : dict
                Mock snapshot object for testing purposes.
        
        Raises
        ------
            TypeError
                for many reasons...

        See Also
        --------
            cbpro message structure format.  
        """
        #for the bid side
        self.snapshot = {
            "type": "snapshot",
            "product_id": "MKC-USD",
            "bids": [],
            "asks": []
        }
        bid_mesh, bid_shape, bid_shape_params, bid_length = 0.01, "linear", [1, 0.1], 10
        ask_mesh, ask_shape, ask_shape_params, ask_length = 0.01, "linear", [1, 0.1], 10
        mid_price = 1.00 
        bid_prices = [mid_price - bid_mesh*position for position in range(1,(bid_length+1))]
        ask_prices = [mid_price + ask_mesh*position for position in range(1,(ask_length+1))]
        
        if "bid_shape" in kwargs.keys():
            bid_shape = kwargs['bid_shape']
            bid_shape_function = kwargs['bid_shape_function'] # 
        if "ask_shape" in kwargs.keys():
            ask_shape = kwargs['ask_shape']
            ask_shape_function = kwargs['ask_shape_function']

        if bid_shape == "custom":
            bid_volm = [bid_shape_function(position) for position in range(1,(bid_length+1))] 
        else: # assumes linear
            bid_volm = [(bid_shape_params[0]*position + bid_shape_params[1]) for position in range(1,(bid_length+1))]
        
        generated_bids = [[str(bid_prices[item]), str(bid_volm[item])] for item in range(len(bid_prices))]
        self.snapshot.update(bids=generated_bids)
        
        if ask_shape == "custom":
            ask_volm = [ask_shape_function(position) for position in range(1,(ask_length+1))]    
        else: # assumes linear
            ask_volm = [(ask_shape_params[0]*position + ask_shape_params[1]) for position in range(1,(ask_length+1))] 

        generated_asks = [[str(ask_prices[item]), str(ask_volm[item])] for item in range(len(ask_prices))] 
        self.snapshot.update(asks=generated_asks)        
        
        return self.snapshot 

    def gen_l2update(self, side="buy", price=0.0, size=0.0):
        """
        generating a mock l2_update message

        Parameters
        ----------
            side : str
                default "buy", side where the order takes place
            
            price : float64
                default 0.0, price level where change occurred
            
            size : float64
                default 0.0, size of change in units of Base Currency (MKC)
            
        Returns
        -------
            self.l2_update_msg : dict
                generated l2_update_msg
        
        Raises
        ------
            None or Typeerror if you messaround with inputs
        
        See Also
        --------
            cbpro l2_update message
        """
        self.l2update_msg = {
            "type": "l2update",
            "product_id": "MKC-USD", #MKC-USD MocK Coin - USD
            "time": str(self.timenow), #"2019-08-14T20:42:27.265Z",
            "changes": [
                [
                    str(side),
                    str(price),
                    str(size)
                ]
            ]}
        return self.l2update_msg

class ticker_messages(l2_update_messages):
    """
    class that holds info on how to handle ticker messages 
    should have ssupport for l2 updates
    """
    def __init__(self, snapshot):
        self.trade_id = 0
        self.sequence = 0
        self.timenow = datetime.utcnow()
        self.snapshot = snapshot
        self.ticker_msg = {
            "type": "ticker",
            "trade_id": self.trade_id,
            "sequence": self.sequence,
            "time": str(self.timenow),
            "product_id": "MKC-USD",
            "price": "0.0",
            "side": "buy", # Taker side
            "last_size": "0.0",
            "best_bid": str(self.snapshot['bids'][0][0]),
            "best_ask": str(self.snapshot['asks'][0][0])
            }
        super(l2_update_messages).__init__()

    def gen_single_msg_ticker(self, side="buy", size=0.0, **kwargs):
        """
        class function that generates ticker messages

        Parameters
        ----------
            side : str
                can be "buy" or "sell"
            price : float64
                price where the market order is executed
            size : float64
                size of the market order
            kwargs : see below?
                options to generate the associated cancellation l2 update.
                however, I feel that this option should be taken away
                because... market orders should always update the orderbook
        
        Returns
        -------
            ticker_msg : list of dict
                ticker message(s) depending how hard the market order hit the order book.
            l2update_msg : list of dict 
                associated cancellation message(s) depending how hard the market order hit the 
                order book.
        
        Raises
        ------
            None 
        
        See Also
        --------

        """
        self.sequence += 1 # how to use trade_id and sequence
        # the sequence to create a ticker message is to 
        # 1. generate the l2update at the best bid/ask 0.0 size or whatever reduction we need
        # 2. after that we must infer the mkt order from the change observed from the l2update.
        # 3. and then return either the ticker stream or both. 
        # the key is that the ticker is still contingent on the orderbook.
        mkt_side = side
        
        wl = kwargs['wl'] if "wl" in kwargs.keys() else 0
        
        if mkt_side == "buy": # market buy at the best ask
            mkt_price = float(self.snapshot['asks'][wl][0]) # retrieve the best ask
            mkt_size = float(self.snapshot['asks'][wl][1]) if float(self.snapshot['asks'][wl][1]) - size< 0 else size
            l2_size = 0.0 if float(self.snapshot['asks'][wl][1]) == mkt_size else float(self.snapshot['asks'][wl][1]) - size
            
        else:
            mkt_price = float(self.snapshot['bids'][wl][0])
            mkt_size = float(self.snapshot['bids'][wl][1]) if float(self.snapshot['bids'][wl][1]) - size< 0 else size
            l2_size = 0.0 if float(self.snapshot['bids'][wl][1]) == mkt_size else float(self.snapshot['bids'][wl][1]) - size


        l2side = "sell" if mkt_side == "buy" else "buy" # we update the opposite side
        self.timenow = datetime.utcnow()
        self.mkt_can_msg = self.gen_l2update(side=l2side, price=mkt_price, size=l2_size)
        self.ticker_msg = { 
            "type": "ticker",
            "trade_id": self.trade_id,
            "sequence": self.sequence,
            "time": str(self.timenow),
            "product_id": "MKC-USD",
            "price": str(mkt_price),
            "side": mkt_side, # Taker side
            "last_size": str(mkt_size),
            "best_bid": str(self.snapshot['bids'][wl][0]),
            "best_ask": str(self.snapshot['asks'][wl][0])
        }
        if (l2_size == 0.0) and (size > mkt_size):
            remaining_size = size - mkt_size
            return self.ticker_msg, self.mkt_can_msg, remaining_size
        else:
            remaining_size = 0
            return self.ticker_msg, self.mkt_can_msg, remaining_size
            # that may be bad code
            # needs to correct the best bid and best ask call for when the price level is extinguished

    def gen_multi_message_ticker(self, side="buy", size=0.0, **kwargs):
        self.trade_id += 1 # we will have to figure out
        current_ticker_msg, current_l2_update_msg, remaining_size = self.gen_single_msg_ticker(side, size)
        ticker_msgs, l2update_msgs = [current_ticker_msg],[current_l2_update_msg]
        current_level=0
        while remaining_size > 0:            
            current_level +=1
            current_ticker_msg, current_l2_update_msg, remaining_size = self.gen_single_msg_ticker(side, size, wl=current_level)
            ticker_msgs.append(current_ticker_msg)
            l2update_msgs.append(current_l2_update_msg)
        return ticker_msgs, l2update_msgs



                     
# class gen_orderbook_updates(object):
#     """
#     Highler level test class that directly modifies the orderboook object.
#     can be used to directly apply market, cancealtion, and insertion messages. 
#     """



# cb_l2update_msg = {
#     "type": "l2update",
#     "product_id": "BTC-USD",
#     "time": "2019-08-14T20:42:27.265Z",
#     "changes": [
#         [
#         "buy",
#         "10101.80000000",
#         "0.162567"
#         ]
#     ]
# }

# print(cb_l2update_msg)

def main():
    l2_update_instance = l2_update_messages() 
    snap = l2_update_instance.get_snapshot()
    print(snap)

    def square(x):
        return x**2
    
    snap2 = l2_update_instance.get_snapshot(bid_shape="custom", bid_shape_function=square)

    print(snap2)

if __name__ == '__main__':
    main()
    
