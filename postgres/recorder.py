import asyncio, time
from datetime import datetime, timedelta
import copra.rest
from copra.websocket import Channel, Client
import pandas as pd

import sys,os
os.chdir('.')
sys.path.append(os.getcwd()+'/crobat/crobat')
sys.path.append(os.getcwd()+'/crobat/postgres')
sys.path.append(os.getcwd()+'/crobat/grafana')
print("printing the sub sys path for the recorder module for postgres")
for _ in sys.path:
    print(_)
import orderbook as LOBf
import orderbook_helpers as hf 
import gc
import numpy as np
import statistics
import sqlconnection
import CUSUMs



class Ticker(Client):
    """
    The Ticker class for postgres. works similar to the crobat ticker class (then why dont i inherit the attributes and methods?)
    works differently in the sense that there is a write operation after receiving each messsage

    Attributes
    ----------
        time_now : datetime object
            invokes method datetime.utcnow() to set an initial start time

        hist : class history object
            Instance of the class history from orderbook.py
        
        position_range : int
            ordinal range to record for
            passed from the attribute position_range from the class input_args
            
        recording_duration : int/float64
            duration in seconds to record for
            passed from the attribute recording_duration from the class input args
        
        counter : int
            starts at 0. idk what this is for anymore
            artifact when i was testing postgres writes
        
        snapshot_connection_id : str
            psuedo-key that postgres uses to find the snapshot connection reference to apply order book changes
            not really a public attribute?
        
        snapshot_reference_id : str
            psuedo-key that postgres uses to find the snapshot reference to apply order book changes
            also not really a public attribute?

        cursor, connection : psycopg2.cursor object, psycopg2.connection object
            cursor and connection object used by psycopg2 to commit inserts to postgres tsdb
            invoked using open_SQL_connection from module sqlconnection
        
        updated_snap : bool
            starts as False, becomes True to add a snapshot reference
            artifcat attribute from something
        
        start_CUSUM : bool
            starts as False, becomes True after spending some time collecting messages for initial
            rates of arrival.
        
        l0 : float64
            initial rate of Market order arrival, will later be expanded for other rates
        
        start_stamp_arrived : bool
            starts as False. becomes true when not detected and sucessfully defined attribute
            start_stamp to be a datetime object.
        
        loop, channel : copra.Client.loop object, copra.Client.channel object 
            loop and channel object inerhited from copra.Client class
        
        Methods
        -------
            __init__(loop, channel, input_args)
                Initializes the class and invokes classes
                XXXXXX
            
            on_open()
                Inherits attributes from loop, channel using by invoking super init 
                Initializes the data model in postgres
            
            on_message(msg)
                parses messages main method while websocket connection is open

            on_close(was_clean, code, reason)
                sequence of steps to perform to close the websocket connection
    """
    def __init__(self, loop, channel, input_args):
        """
        initialization function for the Ticker class. 
        uses:
            1.  datetime.utcnow()
            2.  instance of class history from orderbook.py
            3.  from instance of input_args:
                a. attribute position range : int
                b. attribute recording_duration : int/float64
            4.  from module sqlconnection invokes method open_SQL_connection()
            5.  inherits attributes from copra.Client.loop, and
                copra.Client.channel using super().__init__(loop,channel)
        
        Parameters
        ----------
            loop : ?
                ? i did this somewhere
            
            channel : ?
                ? i did this somewhere 

            input_args : class input_args object
                class object containing the recording settings 
        
        Returns
        -------
            None
        
        Raises
        ------
            None
            See indiviaual methods for their respepctive raises
        
        See Also
        --------
            module orderbook.py
            module copra.Client
        """
        self.time_now = datetime.utcnow() #initial start time
        self.hist = LOBf.history()
        self.position_range = input_args.position_range
        self.recording_duration = input_args.recording_duration
        self.counter = 0 
        self.snapshot_connection_id = None
        self.snapshot_reference_id = None
        self.cursor, self.connection = sqlconnection.open_SQL_connection()
        self.updated_snap = False
        self.start_CUSUM = False
        self.l0 = 0
        self.start_stamp_arrived = False
        super().__init__(loop, channel) # something about a parent class sending attributes to the child class (Ticker)

    def on_open(self):
        """
        Method that is called when the websocket connection is opened.
        Uses sqlconnection.set_data_model(cursor, connection),
        and method copra.Client.on_open()
        
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
            sqlconnection.set_data_model()
            copra.Client.on_open()
        """
        print("Let's count the L3 messages!", self.time_now)
        sqlconnection.set_data_model(self.cursor, self.connection)
        super().on_open() # inheriting things from the parent class who really knows    

    def on_message(self, msg):
        """
        General method that interprets how to handle the message.
        for now, only interprets ticker messages using theses classes and methods:
            1. sqlconnection
            2. CUSUM
            this is a WIP no point writing rn
    
        Parameters
        ----------
            msg : dict / json
                message payload as a json object/dict 
                see coinbasepro messages for message payload structure
            
        Returns
        -------
            None
        
        Raises
        ------
            None
            See individual methods for their respective raises
        
        See Also
        --------
            module CUSUMs.py in folder grafana
            module sqlconnection.py
            module orderbook.py
        """
        #print(msg['type'])
        if msg['type'] == "ticker": 
            prev_timestamp = sqlconnection.get_last_tstamp(self.cursor, self.connection)
            sqlconnection.insert_ticker_message(msg, self.cursor, self.connection)
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
            
            latest_stamp = sqlconnection.get_last_tstamp(self.cursor, self.connection)
            sql_cmd = """ SELECT SUM(lastsize) AS TOTAL FROM ethusd WHERE time BETWEEN '{}' AND '{}' ;""".format(self.start_stamp, latest_stamp)
            sum_orders = float(sqlconnection.custom_sql_fetch(self.cursor, self.connection, sql_cmd))
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
        """
        executes code to close the connection to the postgres server
        and states the disconnection codes from the Websocket API server

        Parameters
        ----------
            was_clean : bool
                States whether the connection was closed cleanly?
            
            code : str, None
                Closed connection code
                See copra.Client.on_close(was_clean, code, reason)
                
            reason : str, None
                if str, the reason in words why the connetion was not closed cleanly 
                if None, no reason to print a cleanly closed connection.
            
        Returns
        -------
            None
        
        Raises 
        ------
            There are issues i just don't understand them yet.
        """
        sqlconnection.close_SQL_connection(self.cursor, self.connection)
        print("Connection to server is closed")
        print(was_clean)
        print(code)
        print(reason)

def main():
    pass

if __name__ == '__main__':
    main()