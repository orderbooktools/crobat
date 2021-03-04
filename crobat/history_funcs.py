
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
# function that converts the time series list of orderbook states into a list of dictionaries for a single side.
def convert_array_to_list_dict(history, pos_limit=5):
    temp_dict = {}
    volm_list = []
    price_list = []
    for i in range(len(history)):
        temp_dict.update({"time":history[i][0]})
        for n in range(pos_limit):
            temp_dict.update({str(n+1):history[i][1][n][1]})
        volm_list.append(temp_dict)
        temp_dict = {}
        temp_dict.update({"time":history[i][0]})
        for n in range(pos_limit):
            temp_dict.update({str(n+1):history[i][1][n][0]})
        price_list.append(temp_dict)
        temp_dict = {}
    return volm_list, price_list

# function that converts the time series list of orderbook states into a list of dictionaries for the signed order book
def convert_array_to_list_dict_sob(history, events, pos_limit=5):
    temp_dict = {}
    volm_list = []
    price_list = []
    temp_dict.update({"time":history[0][0]})
    last_volm = history[0][1][0][1]
    for x in range(len(history[0][1])):
        if last_volm + history[0][1][x][1] < last_volm:
            last_volm = history[0][1][x][1]
            pass
        else:
            best_ask_pos = x
            best_bid_pos = x-1
            break
    snap_prices = list(zip(*history[0][1]))[0][(best_bid_pos-(pos_limit-1)):(best_ask_pos+pos_limit)]
    snap_volm = list(zip(*history[0][1]))[1][(best_bid_pos-(pos_limit-1)):(best_ask_pos+pos_limit)]
    for n in range( len(snap_prices)):
        dict_key = n - pos_limit 
        if dict_key >= 0:
            dict_key += 1
        temp_dict.update({str(dict_key):snap_volm[n]})    
    for i in range(len(history)-1):
        temp_dict.update({"time":history[i+1][0]})
        mid_price = float(events[i][6])
        snap_prices = list(zip(*history[i+1][1]))[0]
        snap_volm = list(zip(*history[i+1][1]))
        mid_price_pos = bisect.bisect(snap_prices,mid_price)
        best_bid_pos = mid_price_pos +1
        best_ask_pos = mid_price_pos
        sob_list = snap_prices#[(best_bid_pos-pos_limit):(best_ask_pos + pos_limit )]
        for n in range(len(sob_list)):
            dict_key = n-pos_limit
            if dict_key == 0:
                dict_key +=1
            temp_dict.update({str(dict_key):history[i+1][1][n][1]})
        volm_list.append(temp_dict)
        temp_dict = {}
        temp_dict.update({"time":history[i+1][0]})
        for n in range(len(sob_list)):
            dict_key = n-pos_limit-1
            if dict_key >= 0:
                dict_key += 1
            temp_dict.update({str(dict_key):history[i+1][1][n][0]})
        price_list.append(temp_dict)
        temp_dict = {}
    return volm_list, price_list

#converts pd dfs into an excel file 
def pd_pkl_save(title, hist_obj_dict):
    hist_obj_df = pd.DataFrame(hist_obj_dict)
    hist_obj_df = hist_obj_df[1:]
    path = "./"+title+".pkl"
    hist_obj_df.to_pickle(path)

def pd_csv_save(title, hist_obj_dict):
    hist_obj_df = pd.DataFrame(hist_obj_dict)
    hist_obj_df = hist_obj_df[1:]
    path = "./"+title+".pkl"
    hist_obj_df.to_csv(index=False)

def pd_excel_save(title, hist_obj_dict):
    title +=".xlsx"
    hist_obj_df = pd.DataFrame(hist_obj_dict)
    hist_obj_df = hist_obj_df[1:]
    writer = pd.ExcelWriter(title, engine='xlsxwriter')
    hist_obj_df.to_excel(writer, sheet_name='Sheet1')
    writer.save()

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
