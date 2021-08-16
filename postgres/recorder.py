import asyncio, time
from datetime import datetime, timedelta
import copra.rest
from copra.websocket import Channel, Client
import pandas as pd

import sys,os
os.chdir('.')
sys.path.append(os.getcwd()+'/crobat/crobat')
sys.path.append(os.getcwd()+'/crobat/postgres')
#sys.path.append(os.getcwd()+'/crobat/grafana')
print("printing the sub sys path for the recorder module for postgres")
for _ in sys.path:
    print(_)
import orderbook as LOBf
import orderbook_helpers as hf 
import gc
import numpy as np
import sqlconnection

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
        self.snapshot_connection_id = None
        self.snapshot_reference_id = None
        self.cursor, self.connection = sqlconnection.open_SQL_connection()
        self._snap = False
        self.start_stamp_arrived = False
        self.create_instance = sqlconnection.psql_create_operations(self.cursor, self.connection)
        self.read_instance = sqlconnection.psql_read_operations(self.cursor, self.connection)
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
            msg : dict
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
            if self.snapshot_connection_id:   # needs functionality for ticker only
                self.create_instance.insert_ticker_message(msg, self.cursor, self.connection)

        if msg['type'] == "snapshot":
            self.snapshot_connection_id , self.snapshot_reference_id = self.create_instance.insert_snapshot(msg)
            self.hist.initialize_snap_events(msg, self.time_now)
            self.min_dec = self.hist.min_dec
        
        if msg['type'] == "l2update":
            time=datetime.strptime(msg['time'],'%Y-%m-%dT%H:%M:%S.%fZ') 
            changes = msg['changes'] 
            side = 'bid' if changes[0][0] == "buy" else "ask" 
            price_level = float(changes[0][1]) 
            level_depth = np.around( float(changes[0][2]), decimals=self.min_dec)
            pre_level_depth = 0 
            self.create_instance.insert_message(msg, self.snapshot_connection_id, self.snapshot_reference_id)
            if side =="bid":
                price_match_index = list(filter(lambda x: LOBf.price_match(self.hist.bid_range[x], price_level), range(len(self.hist.bid_range))))
                LOBf.UpdateSnapshot_bid_Seq(self.hist, time, side, price_level, level_depth, pre_level_depth, price_match_index, self.position_range)
            elif side =="ask":
                price_match_index = list(filter(lambda x: LOBf.price_match(self.hist.ask_range[x], price_level), range(len(self.hist.ask_range))))
                LOBf.UpdateSnapshot_ask_Seq(self.hist, time, side, price_level, level_depth, pre_level_depth, price_match_index, self.position_range)
            else:
                print("unknown side")
        if self.snapshot_connection_id:
            if (datetime.utcnow()- datetime.fromtimestamp(int(self.snapshot_connection_id[7:-5]))) > timedelta(minutes=1):
                self.snapshot_reference_id = self.create_instance.insert_minute_snapshot(msg, self.hist, self.snapshot_connection_id)
                print("created minute snapshot")

        if (datetime.utcnow() - self.time_now).total_seconds() > self.recording_duration:  
            self.loop.create_task(self.close())

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
        gc.collect()

def main():
    pass

if __name__ == '__main__':
    main()