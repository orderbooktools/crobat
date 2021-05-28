import asyncio, time
from datetime import datetime
from datetime import timedelta
import copra.rest
from copra.websocket import Channel, Client
import pandas as pd
import LOB_funcs as LOBf
import history_funcs as hf 
import gc
import numpy as np
import statistics
from SQL_connection import *
import CUSUMs

class Ticker(Client):
    def __init__(self, loop, channel, input_args):
        self.time_now = datetime.utcnow() #initial start time
        self.hist = LOBf.history()
        self.position_range = input_args.position_range
        self.recording_duration = input_args.recording_duration
        self.counter = 0 
        self.snapshot_connection_id = None
        self.snapshot_reference_id = None
        self.cursor, self.connection = open_SQL_connection()
        self.updated_snap = False
        self.start_CUSUM = False
        self.l0 = 0
        self.start_stamp_arrived = False
        super().__init__(loop, channel) # something about a parent class sending attributes to the child class (Ticker)

    def on_open(self):
        print("Let's count the L3 messages!", self.time_now)
        set_data_model(self.cursor, self.connection)
        super().on_open() # inheriting things from the parent class who really knows    

    def on_message(self, msg):
        #print(msg['type'])
        if msg['type'] == "ticker": 
            prev_timestamp = get_last_tstamp(self.cursor, self.connection)
            insert_ticker_message(msg, self.cursor, self.connection)
            #I need mkt can overlap for the postgresql
            if not self.start_stamp_arrived:
                self.start_stamp = datetime.strptime(msg['time'],'%Y-%m-%dT%H:%M:%S.%fZ') # msg['time'] into a datetime object
                self.start_stamp_arrived = True
                
            if self.start_CUSUM:
                volm = float(msg['last_size'])
                timestamp = datetime.strptime(msg['time'],'%Y-%m-%dT%H:%M:%S.%fZ')
                #current_timestamp = get_last_tstamp(self.cursor, self.connection)
                deltatime = (timestamp - prev_timestamp).total_seconds()
                self.CUSUM.Update(self.l0, volm, deltatime, timestamp)
                #current_state = self.CUSUM.get_vars()
                #print(current_state)
                self.CUSUM.write_to_tsdb(self.cursor, self.connection)

       

        if (datetime.utcnow() - self.time_now).total_seconds() > 10 and not self.start_CUSUM:  # after 1 second has passed
            if not self.start_stamp_arrived:
                self.start_stamp = datetime.strptime(msg['time'],'%Y-%m-%dT%H:%M:%S.%fZ') # msg['time'] into a datetime object
                self.start_stamp_arrived = True
            
            latest_stamp = get_last_tstamp(self.cursor, self.connection)
            sql_cmd = """ SELECT SUM(lastsize) AS TOTAL FROM ethusd WHERE time BETWEEN '{}' AND '{}' ;""".format(self.start_stamp, latest_stamp);
            sum_orders = float(custom_sql_fetch(self.cursor, self.connection, sql_cmd))
            self.l0 = float(sum_orders/((latest_stamp - self.start_stamp).total_seconds()))
            print("initial rate of market order arrival: ", self.l0, " ETH/s")  ## a way to recall wtf was posted
            h = 0.1
            epsilon = 0.01
            self.CUSUM = CUSUMs.CUSUM(self.l0, epsilon, float(msg['last_size']), h, latest_stamp)
            self.start_CUSUM = True 

            #self.loop.create_task(self.close()) # ASyncIO nonsense


            
            #i need a snapshot connection and reference id to asssign this to
            #store the message 
            
        # if msg['type'] == "snapshot":
        #     self.snapshot_connection_id , self.snapshot_reference_id= insert_snapshot(msg, self.cursor, self.connection)
        #     self.hist.initialize_snap_events(msg, self.time_now)
        #     self.min_dec = self.hist.min_dec
        # if msg['type'] == "l2update":
        #     time=datetime.strptime(msg['time'],'%Y-%m-%dT%H:%M:%S.%fZ') #from the message extract time
        #     changes = msg['changes'] #from the message extract the changes
        #     side = 'bid' if changes[0][0] == "buy" else "ask" #side in which the changes happend (don't worry its orderbook crap)
        #     price_level = float(changes[0][1]) #the position in x_range that the change is affecting
        #     level_depth = np.around( float(changes[0][2]), decimals=self.min_dec) #the value in x_volm that is changing
        #     pre_level_depth = 0 
        #     insert_message(msg, self.cursor, self.connection, self.snapshot_connection_id, self.snapshot_reference_id)
        #     if side =="bid":
        #         price_match_index = list(filter(lambda x: LOBf.price_match(self.hist.bid_range[x], price_level), range(len(self.hist.bid_range))))
        #         LOBf.Update_bid_Seq(self.hist, time, side, price_level, level_depth, pre_level_depth, price_match_index)
        #     elif side =="ask":
        #         price_match_index = list(filter(lambda x: LOBf.price_match(self.hist.ask_range[x], price_level), range(len(self.hist.ask_range))))
        #         LOBf.Update_ask_Seq(self.hist, time, side, price_level, level_depth, pre_level_depth, price_match_index)
        #     else:
        #         print("unknown side")               

        if (datetime.utcnow() - self.time_now).total_seconds() > self.recording_duration:  # after 1 second has passed
            self.loop.create_task(self.close()) # ASyncIO nonsense

        # if datetime.utcnow().second == 00 and not self.updated_snap: # for now its do it every minute
        #     self.snapshot_reference_id = insert_minute_snapshot(self.hist, self.cursor, self.connection, self.snapshot_connection_id)
        #     self.updated_snap = True
        # elif datetime.utcnow().second == 00 and self.updated_snap:
        #     pass
        # else:
        #     self.updated_snap = False

    def on_close(self, was_clean, code, reason):
        close_SQL_connection(self.cursor, self.connection)
        print("Connection to server is closed")
        print(was_clean)
        print(code)
        print(reason)

def main():
    pass

if __name__ == '__main__':
    main()