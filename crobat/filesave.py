import history_funcs as hf
import pandas as pd
from datetime import datetime 

def filesaver(hist_obj, position_range, events=True, **kwargs):
    list_to_convert = []
    out_time = datetime.utcnow()
    print("recorded the time")
    if 'sides' in kwargs.keys():
        if 'bid' in kwargs['sides']:
            print("found bid okay")
            final_bid_list, final_bid_prices = hf.convert_array_to_list_dict(hist_obj.bid_history, position_range)
            titles_bid = ["L2_orderbook_volm_bid"+str(out_time),
                "L2_orderbook_prices_bid"+str(out_time),
                "L2_orderbook_events_bid"+str(out_time)]
            list_to_convert.append([[final_bid_list, titles_bid[0]], [final_bid_prices, titles_bid[1]]])
            if events:
                list_to_convert[-1].append([hist_obj.bid_events, titles_bid[2]])
                print("added events okay")
        if 'ask' in kwargs['sides']:
            final_ask_list, final_ask_prices = hf.convert_array_to_list_dict(hist_obj.ask_history, position_range)
            titles_ask = ["L2_orderbook_volm_ask"+str(out_time),
                "L2_orderbook_prices_ask"+str(out_time),
                "L2_orderbook_events_ask"+str(out_time)]
            list_to_convert.append([[final_ask_list, titles_ask[0]], [final_ask_prices, titles_ask[1]]])
            if events:
                list_to_convert[-1].append([hist_obj.ask_events, titles_ask[2]])
        if 'signed' in kwargs['sides']:
            final_signed_list, final_signed_prices = hf.convert_array_to_list_dict_sob(hist_obj.signed_history, hist_obj.signed_events)
            titles_signed = ["L2_orderbook_volm_signed"+str(out_time),
                "L2_orderbook_prices_signed"+str(out_time),
                "L2_orderbook_events_signed"+str(out_time)]
            list_to_convert.append([[final_signed_list, titles_signed[0]], [final_signed_prices, titles_signed[1]]])
            if events:
                list_to_convert[-1].append([hist_obj.signed_events, titles_signed[2]])

    else:
        print("no sides specified")

    if 'filetype' in kwargs.keys():
        if 'csv' in kwargs['filetype']:
            for i in range(len(list_to_convert)): # 0 for bid, 1 for ask 2 for signed
                for m in range(len(list_to_convert[i])): # 0 for volm, 1 for price, 2 for events
                    hf.pd_csv_save(list_to_convert[i][m][1], list_to_convert[i][m][0]) # o for data, 1 for title
        if 'pkl' in kwargs['filetype']:
            for i in range(len(list_to_convert)): # 0 for bid, 1 for ask 2 for signed
                for m in range(len(list_to_convert[i])): # 0 for volm, 1 for price, 2 for events
                    hf.pd_pkl_save(list_to_convert[i][m][1], list_to_convert[i][m][0]) # o for data, 1 for title
        if 'xlsx' in kwargs['filetype']:
            for i in range(len(list_to_convert)): # 0 for bid, 1 for ask 2 for signed
                for m in range(len(list_to_convert[i])): # 0 for volm, 1 for price, 2 for events
                    hf.pd_excel_save(list_to_convert[i][m][1], list_to_convert[i][m][0]) # o for data, 1 for title
    else:
        print("no filetype specified")
def main():
    pass

if __name__ == '__main__':
    main()