
## Functions that help the history class 
import pandas as pd
import bisect

# test function that checks that the snapshot is sorted correctly.
def check_order(snapshot,side):
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

# used to flip position for bid side
def set_signed_position(position, side):
    position += 1
    if side =="bid":
        position *= -1
    return position

# function used to get the smallest tradable amount of XTC base currency for a given tick size in the float currency (i.e., 0.01 USD)
def get_min_dec(min_currency_denom, min_asset_value):
    min_tradable_amount = min_currency_denom/min_asset_value
    min_dec_out = 0
    while min_tradable_amount < 1:
        min_tradable_amount*=10
        min_dec_out += 1
        if min_dec_out > 10:
            print("min_dec >10")
            break 
    return min_dec_out

# stuff I'm working on now 
def get_tick_distance(ref_price, input_price, ticksize=0.01):
    tick_distance = abs(ref_price - input_price)/ticksize
    return tick_distance 
