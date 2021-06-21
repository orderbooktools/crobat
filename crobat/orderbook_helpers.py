
## Functions that help the history class 
import pandas as pd
import bisect

def check_order(snapshot,side):
    """
    test function that checks that the snapshot is sorted correctly.

    Parameters
    ----------
        snapshot : list of list
            snapshot array ordered as follows [[price, volm],[price,volm]]
        
        side : str
            side being checked, can be "bid" or "ask"
    
    Returns
    -------
        None

    Raises
    ------
        None
    
    Remarks
    ------- 
        edits the snapshot argument using function sorted(list_object)

    """
    if side == "bid":
        ans = sorted(snapshot, key=lambda x: x[0])[::-1]  
    else:
        ans = sorted(snapshot, key=lambda x: x[0])
    if snapshot == ans:
        pass
    else:
        pass  


# used to set the sign in OFI for signed order book events
def set_sign(event_size, side, order_type):
    """
    Sets the sign for the order book event in the signed order book.
    if side is ask:
        POSITIVE sign for market orders and limit insertions
        NEGATIVE sign for limit cancellations
    if side is bid:
        NEGATIVE sign for market orders and limit insertions
        POSITIVE sign for limit cancellations
    
    Parameters
    ----------
        event_size : float64
            size of the event
        
        side : str
            given side of the event can be "bid" or "ask"
        
        order_type : str
            type of order can be "market", "insertion", "cancelation"
    
    Returns
    -------
        sign : int
            1 or -1 depending on conditions inferred. 

    Raises
    ------ 
        None
        default sign := 1 
    """
    sign=1
    if order_type in ["insertion", "market"]:
        sign = 1
    elif order_type == "cancelation":
        sign = -1 
    else:
        pass
    if side == "bid":
        sign *= -1 
    else:
        pass
    return sign


def set_signed_position(position, side):
    """
    Understand the order book is really two assumed separate order books.
    used to flip position for bid side. 

    Parameters
    ----------
        position : int
            position where the order book was updated [0,len(snapshot)-1]
        
        side : str
            side where the event occurred, can be "bid" or "ask"
    
    Returns
    -------
        position : int
            The signed position:
                -1 * position if side == "bid"
                +1 * position if side == "ask"
    
    Raises
    ------ 
        Type error if parameter passed isn't an int
    """
    position += 1
    if side =="bid":
        position *= -1
    return position

def get_min_dec(min_currency_denom, min_asset_value):
    """
    Computes the smallest tradable amount of XTC base currency for a given
    tick size in the float currency (i.e., 0.01 USD)
    
    Parameters
    ----------
        min_currency_denom : float64
            Minimum currency denomination of the float currency
            (e.g., 0.01 USD)
        
        min_asset_value : float64
            Minimum observed price of the base currency in
            denominated by the float currency.
            i.e., the worst bid in the order book

    Returns
    -------
        min_dec_out : float64
            the smallest tradable amount for the lowest observed price.
            This gives a floor as to how small trades can be locally. 

    Raises
    ------
        TypeError 
            If you try to pass anything that isn't int or float64.
            can occurr if you forget to use float(msg['price']).     
    """
    min_tradable_amount = min_currency_denom/min_asset_value
    min_dec_out = 0
    while min_tradable_amount < 1:
        min_tradable_amount*=10
        min_dec_out += 1
        if min_dec_out > 10:
            print("min_dec >10")
            break 
    return min_dec_out

def get_tick_distance(ref_price, input_price, ticksize=0.01):
    """
        WIP. some papers like to use tick distance
        I do not understand yet how this helps.
    """
    tick_distance = abs(ref_price - input_price)/ticksize
    return tick_distance 
