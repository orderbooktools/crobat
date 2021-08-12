# import psycopg2



# print(conn)

from datetime import datetime
from datetime import timedelta
#from tests.mockobjects import l2_update_messages
import psycopg2
from psycopg2.extras import execute_values
from config import config
import json
import sys
import pandas as pd 
import os
# print("the starting working directory is: ", os.getcwd())
# os.chdir('..')
# print("the directory one level up is: ", os.getcwd())
# print("we will now append tests to the sys.path")
sys.path.append(os.getcwd()+'/tests')
print("the last entry in sys.path is....", sys.path[-1])
from mockobjects import *

##############################################################################
#                                                                            # 
#                Miscelaneous Functions                                      #
#                                                                            #
##############################################################################
def execcommit(query, cur_obj, conn_obj):
    """
    Main driver for PostgreSQL statements. 

    Parameters
    ----------
        query : str
            PostgreSQL query in the form of a formatted string.
        
        cur_obj : cursor object
            cursor object attribute (or object as instance of the subclass
            cursors) from psycopg2.connect(**kwargs) instance.
            used to establish the cursor when connected to the PostgreSQL
            server
        
        con_obj : connection object
            psycopg2.connect(**params) object.
            Used to establish a connection to a PostgreSQL database.
        
    Returns
    -------
        None

    Raises
    ------
        None
    
    See Also
    --------
        class psycopg2.connection 
    """
    if type(query) == type(list(query)):
        sql = query[0]
        record = query[1]
        cur_obj.execute(sql, record)
    else:
        cur_obj.execute(query)
        conn_obj.commit()  

def open_SQL_connection():
    """
    Connect to the PostgreSQL database server
    
    Parameters
    ----------
        None
    
    Returns
    -------
        cur : cursor object 
            instance of the subclass cursor from instance of the class
            psycopg2.connect(**params)
        
        con : connection object
            instance of psycopg2.connect(**params).
            Used to establish a connection to a PostgreSQL database.

    Raises
    ------
        None

    See Also
    --------
        class psycopg2.connect(**kwargs)
    """
    conn = None
    cur = None

    try:
        # read connection parameters
        inipath = sys.path[0]+'/database.ini'
        params = config(filename=inipath, section='postgresql')

        # connect to the PostgreSQL server
        print('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(**params)
        
        # create a cursor
        cur = conn.cursor()
       
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)

    return cur, conn

def close_SQL_connection(cur, conn):
    """
    Closes connection to the Postgres Server
    
    Parameters
    ----------        
        cur_obj : cursor object
            cursor object attribute (or object as instance of the subclass
            cursors) from psycopg2.connect(**kwargs) instance.
            used to establish the cursor when connected to the PostgreSQL
            server
        
        con_obj : connection object
            psycopg2.connect(**params) object.
            Used to establish a connection to a PostgreSQL database.
    
    Returns 
    -------
        None
    
    Raises
    ------
        None
    """
    cur.close()
    print("closed the cursor")
    if conn is not None:
        conn.close()
        print('Database connection closed.')

class psql_setup_operations(object):
    """
    psql methods that help set the data model
    
    Attributes
    ----------
        None
    
    Methods
    -------
        check_db_settings
            ?

        set_data_model(cur, conn)
            ??
    """
    def check_db_settings():
        pass

    def set_data_model(self, cur, conn):
        """
        Function that creates (if not done so already) the tables for 
        1. generated snapshots AS snapshots 
        2. messages from the l2update channel AS messages
        3. messages from the ticker channel AS ticker 

        Parameters
        ----------
            cur : cursor object
                ?
            conn : connection object
                ?
        
        Returns
        -------
            None

        Raises
        ------
            None 
        """
        # Ensure we have timescaledb extention loaded
        tsextload = """ CREATE EXTENSION IF NOT EXISTS timescaledb;"""
        # create the snapshots table
        create_snapshots = """ CREATE TABLE IF NOT EXISTS snapshots(tstamp TIMESTAMP, snapshot_connection_id TEXT, snapshot_reference_id TEXT, bids json, asks json);""" 
        # create the messages table for l2update messages
        create_messages = """ CREATE TABLE IF NOT EXISTS messages(tstamp TIMESTAMP, snapshot_connection_id TEXT, snapshot_reference_id TEXT, changes json);"""
        # create the messages table for ticker messages
        create_ticker = """ CREATE TABLE IF NOT EXISTS ticker(tstamp TIMESTAMP, snapshot_connection_id TEXT, snapshot_reference_id TEXT, message json);"""
        for query in [tsextload, create_snapshots, create_messages, create_ticker]:
            execcommit(query, cur, conn)
       
        # turn things into timescale        
        timescale_queries = [
            """ SELECT create_hypertable('snapshots', 'tstamp', if_not_exists=>TRUE);""", 
            """ SELECT create_hypertable('messages', 'tstamp', if_not_exists=>TRUE);""", 
            """ SELECT create_hypertable('ticker', 'tstamp', if_not_exists=>TRUE);"""
        ]
        for query in [timescale_queries]:
            execcommit(query, cur, conn)

    # def custom_data_model(cur,conn):
    #     """
    #     testing Function that creates (if not done so already) the tables for 
    #     1. generated snapshots AS snapshots 
    #     2. messages from the l2update channel AS messages
    #     3. messages from the ticker channel AS ticker 

    #     Parameters
    #     ----------
    #         cur : cursor object
    #             ?
    #         conn : connection object
    #             ?
        
    #     Returns
    #     -------
    #         None

    #     Raises
    #     ------
    #         None 
    #     """
    #     # function that asks postgres if it can receive insert messages
    #     # create the snapshots table
    #     postgres_create_query_1 = """ CREATE TABLE IF NOT EXISTS snapshots(tstamp TIMESTAMP, snapshot_connection_id TEXT, snapshot_reference_id TEXT, bids json, asks json);""" 
    #     # create the messages table for l2update messages
    #     postgres_create_query_2 = """ CREATE TABLE IF NOT EXISTS messages(tstamp TIMESTAMP, snapshot_connection_id TEXT, snapshot_reference_id TEXT, changes json);"""
    #     # create the messages table for ticker messages
    #     #postgres_create_query_3 = """ CREATE TABLE IF NOT EXISTS ticker(tstamp TIMESTAMP, snapshot_connection_id TEXT, snapshot_reference_id TEXT, message json);"""
    #     execcommit(postgres_create_query_1, cur, conn)
    #     execcommit(postgres_create_query_2, cur, conn)
##############################################################################
#                                                                            #
#                   PSQL CRUD Classes: CREATE operations                     #
#                                                                            #
##############################################################################

class psql_create_operations(object):
    """
    class of functions that contains the different
    methods for the postgres inserts operations.
        
    Attributes
    ----------
        None


    Methods
    -------
        __init__

        insert_snapshot(msg)

        insert_message(msg)

        insert_minute_snapshot(self, hist_obj, snapshot_connection_id):
            
        insert_ticker_message(self, msg)

        mkt_can_overlap(self, msg)
    """
    def __init__(self, cursor, connection, psqloperations=None):
        """
        inherits psqloperations? idk
        
        Parameters
        ----------
            cursor : cursor object
                cursor object attribute (or object as instance of the subclass
                cursors) from psycopg2.connect(**kwargs) instance.
                used to establish the cursor when connected to the PostgreSQL
                server
        
            connection : connection object
                psycopg2.connect(**params) object.
                Used to establish a connection to a PostgreSQL database.

        Returns
        -------
            None
        
        Raises
        ------
            None
        """
        self.cursor = cursor
        self.connection = connection 
        if psqloperations:
            super(psqloperations, self).__init__()
            # this may throw an error if not a class 

    def insert_snapshot(self, msg):
        """
        adds snapshot to the postgres table 

        Parameters
        ----------
            msg : dict 
                parsed json object containing the snapshot message in the form
                msg = {
                    bids : [[], []],
                    asks : [[], []]
                }
        
        Returns
        -------
            snapshot_connection_id : str
            
            snapshot_reference_id : str
        
        Raises
        ------
            hmmm
             
        """
        if msg['type'] == "snapshot":
            bids =json.dumps(msg['bids'][:2800])
            asks =json.dumps(msg['asks'][:2800])
            UTC_tstamp = datetime.utcnow()
            snapshot_connection_id =  msg['product_id'] + str(int(datetime.utcnow().timestamp()*(10 ** 6)))
            snapshot_reference_id = msg['product_id'] + '0'
            postgres_insert_query =  """ INSERT INTO snapshots (tstamp, snapshot_connection_id, snapshot_reference_id, bids, asks) VALUES (%s, %s, %s, %s, %s)"""
            record_to_insert = (UTC_tstamp, snapshot_connection_id, snapshot_reference_id, bids, asks)
            execcommit([postgres_insert_query, record_to_insert], self.cursor, self.connection)
            count = self.cursor.rowcount
        else:
            print("not a snapshot message")
        return snapshot_connection_id, snapshot_reference_id

    def insert_message(self, msg, snapshot_connection_id, snapshot_reference_id):
        """
        inserts message inthe postgres table. uses snapshot connection id and snapshot reference id as primary and seconadary keys 

        Parameters
        ----------
            msg : dict
            
            snapshot_connection_id : str
            
            snapshot_reference_id : str

        Returns
        -------
            None

        Raises
        ------
            None
        """    
        if msg['type'] == "l2update":
            changes=json.dumps(msg['changes'])
            postgres_insert_query =  """ INSERT INTO messages (tstamp, snapshot_connection_id, snapshot_reference_id, changes) VALUES (%s, %s, %s, %s)"""
            record_to_insert = (msg['time'], snapshot_connection_id, snapshot_reference_id, changes)
            execcommit([postgres_insert_query, record_to_insert], self.cursor, self.connection)
            count = self.cursor.rowcount
        elif msg['type'] =="ticker":
            postgres_insert_query = """ INSERT INTO ticker (tstamp, snapshot_connection_id, snapshot_reference_id, changes) VALUES (%s, %s, %s, %s)"""
            record_to_insert = (msg['time'], snapshot_connection_id, snapshot_reference_id, msg)
        else:
            print("unknown message type", msg)

    def insert_minute_snapshot(self, hist_obj, snapshot_connection_id):
        """
        inesrts the bids and asks into the snapshot table. generates the
        snapshot reference id.

        Parameters
        ----------
            hist_obj: class history object
                dw??

            snapshot_connection_id : str
        
        Returns
        -------
            snapshot_reference_id : str
                ?????
        
        Raises
        ------
            None
        """
        #generate the new snapshot by applying the current stuff
        bids, asks = json.dumps(hist_obj.snapshot_bid), json.dumps(hist_obj.snapshot_ask)
        snapshot_connection_id, _assoc_tstamp = snapshot_connection_id, int(snapshot_connection_id[7:])
        UTC_tstamp = datetime.utcnow()
        snapshot_reference_id = snapshot_connection_id[:7]+ str(UTC_tstamp.timestamp()*(10 ** 6) - _assoc_tstamp)
        postgres_insert_query =  """ INSERT INTO snapshots (tstamp, snapshot_connection_id, snapshot_reference_id, bids, asks) VALUES (%s, %s, %s, %s, %s)"""
        record_to_insert = (UTC_tstamp, snapshot_connection_id, snapshot_reference_id, bids, asks)
        execcommit([postgres_insert_query, record_to_insert], self.cursor, self.connection)
        count = self.cursor.rowcount
        print(count, "snapshot_id: " + snapshot_reference_id + " inserted successfully into snapshots table")
        return snapshot_reference_id

    def insert_ticker_message(self, msg):
        """
        inserts ticker message into the postgres table.
        
        Parameters
        ----------
            msg : dict 
                YES
        
        Returns
        -------
            None
        
        Raises
        ------
            None
        """
        if msg['type'] == 'ticker':
            postgres_insert_query = """ INSERT INTO ticker (sequence, time, price, side, lastsize, bestbid, bestask) VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            record_to_insert = (int(msg['sequence']), msg['time'], float(msg['price']), msg['side'], float(msg['last_size']),float(msg['best_bid']), float(msg['best_ask']))
            execcommit([postgres_insert_query, record_to_insert], self.cursor, self.connection)
            count = self.cursor.rowcount


##############################################################################
#                                                                            #
#                    PostgreSQL CRUD Classes: READ operations                #
#                                                                            #
##############################################################################


class psql_read_operations(object):
    """
    psql methods to fetch data from the postgres server

    Attributes
    ----------
        cursor : cursor object
            ????
        connection : connection object
    
    Methods
    -------
        get_last_tstamp(cur, conn)
    
        custom_sql_fetch(cur, conn, sql)
            
    """
    def __init__(self, cursor, connection, psqloperations=None):
        """
        inherits psqloperations? idk
        
        Parameters
        ----------
            cursor : cursor object
                cursor object attribute (or object as instance of the subclass
                cursors) from psycopg2.connect(**kwargs) instance.
                used to establish the cursor when connected to the PostgreSQL
                server
        
            connection : connection object
                psycopg2.connect(**params) object.
                Used to establish a connection to a PostgreSQL database.

        Returns
        -------
            None
        
        Raises
        ------
            None
        """
        self.cursor = cursor
        self.connection = connection 
        if psqloperations:
            super(psqloperations, self).__init__()
            # this may throw an error if not a class 


    def get_last_tstamp(self):
        """
        Fetches the last timestamp from the PostgreSQL database.

        Parameters
        ----------
            None

        Returns
        -------
            timestamp : datetime object
                Timestamp from the queried postgres db
        
        Raises
        ------
            If the queried Postgresdb does not have a time column
            psycopg2 will throw an error. 
        """
        sql = """ SELECT tstamp FROM messages ORDER BY tstamp DESC LIMIT 1;"""
        execcommit(sql, self.cursor, self.connection)
        returns = self.cursor.fetchall()
        print(returns[0][0])
        return returns[0][0]

    def custom_sql_fetch(self, sql):
        """
        Custom SQL fetch, leave the PostgreSQL code as a string.
        
        Parameters
        ----------
            sql : str
                PostgreSQL code as a string.
        
        Returns
        -------
            returns : string, or JSON object
                Custom fetch returns, needs further testing
        
        Raises
        ------
            Custom SQL fetches are complicated.
        """
        execcommit(sql, self.cursor, self.connection)
        returns = self.cursor.fetchall()
        if len(returns) > 1:
            print("multi item return of len: ", len(returns))
            returns_list = [] 
            for _ in returns:
                returns_list.append(_[0][0])
            return returns_list
        else:
            return returns[0][0]

##############################################################################
#                                                                            #
#                    PostgreSQL CRUD Classes: UPDATE operations              #
#                                                                            #
##############################################################################

class psql_update_operations(object):
    """
    class of methods that update the PostgreSQL database.

    Attributes
    ----------
        

    Methods
    -------
        
    """
    def __init__(self, cursor, connection, psqloperations=None):
        """
        inherits psqloperations? idk
        
        Parameters
        ----------
            cursor : cursor object
                cursor object attribute (or object as instance of the subclass
                cursors) from psycopg2.connect(**kwargs) instance.
                used to establish the cursor when connected to the PostgreSQL
                server
        
            connection : connection object
                psycopg2.connect(**params) object.
                Used to establish a connection to a PostgreSQL database.

        Returns
        -------
            None
        
        Raises
        ------
            None
        """
        self.cursor = cursor
        self.connection = connection 
        if psqloperations:
            super(psqloperations, self).__init__()
            print("interited sucessfully")
            # this may throw an error if not a class 
        
    def mkt_can_overlap(self, msg):
        """
        Supposed to check the postgres table for market cancelation overlaps. 
        
        Parameters
        ----------
            msg : dict
        
        Returns
        -------
            None
        
        Raises
        ------
            None
        """
        #step 1. query the db to get a a short list of entries
        sql = """ select tstamp, changes from messages order by tstamp desc limit 5;"""
        execcommit(sql, self.cursor, self.connection)
        returns = self.cursor.fetchall()
        print(returns)

##############################################################################
#                                                                            #
#                    PostgreSQL CRUD Classes: Delete operations              #
#                                                                            #
##############################################################################
def psql_delete_operations(object):
    """
    Class of methods with PostgreSQL delete operations

    Attributes
    ----------
        cursor : cursor object
            ?
        connection : connection object
        
    Methods
    -------
        Delete Last entry
        
        Custom Delete
    """
    
    def __init__(self, cursor, connection, read_operations):
        super(read_operations)
        if self.cursor == cursor:
            print("cursor inherited sucessfully")
        if self.connection == connection:
            print("connection inherited successfully")            
        pass

    def delete_last_message(self):
        lasttstamp = self.get_last_tstamp() # lets pray to jesus it inherited correctly.
        sql = """ DELETE * FROM messages WHERE tstamp = {} """.format(lasttstamp)
        execcommit(sql, self.cursor, self.connection)


def main():

    """
    test methods to check the operation of the script. 
    TEST 1: checking CREATE functions
    """
    # setup 
    cursor, connection = open_SQL_connection()
    print("sucessfully opened a connection to psql server")
    #read_instance = psql_read_operations(cursor, connection)
    
    # test 0: testing set data model functions
    #     a.  Try seeing if create datamodel works
    sdm_instance = psql_setup_operations()
    sdm_instance.set_data_model(cursor, connection)

    # test 1: testing insert operations with dummy data
    l2updateinstance  = l2_update_messages()
    snapmsg = l2updateinstance.gen_snapshot()
    l2msg = l2updateinstance.gen_l2update(price=0.99, size=1)
    print(snapmsg)
    create_instance = psql_create_operations(cursor, connection)
    snap_cid, snap_rid = create_instance.insert_snapshot(snapmsg)
    create_instance.insert_message(l2msg, snap_cid, snap_rid)
    
    # test 1: testing methods of the psql_read_operations
    #     a. get last tstamp
    read_instance = psql_read_operations(cursor, connection)
    latest_stamp = read_instance.get_last_tstamp()
    print(latest_stamp)

    
    #     b. custom sql fetch get a list of recorded change messages in the last 10 seconds
    start_stamp = latest_stamp - timedelta(seconds=1)
    print("10 seconds before the latest message message???", start_stamp)
    sql_cmd = """ SELECT changes AS TOTAL FROM messages WHERE tstamp BETWEEN '{}' AND '{}' ;""".format(start_stamp, latest_stamp)
    out = read_instance.custom_sql_fetch(sql_cmd)
    out_df = pd.DataFrame(out)
    print(out_df.head())
    
    # test 2: testing methods of the psql_update_operations
    #      a. testing mkt can overlap
    # setup by creating mkt and can messages with identical size
    
    # testing methods of psql
    # execute a statement
    # msg = {'type':"snapshot", 'product_id':"ETH-USD", 'bids':[[123,0.1], [124, 0.5]], 'asks':[[125,0.5], [126,1]]}
    # print("message to add", msg)
    # insert_message(msg, connection, cursor)

    print('PostgreSQL database version:')
    #cursor.execute('SELECT version()')
    #execute_values(cur, operation.query, operation.values)
    #connection.commit()
    
    #mkt_can_overlap(cursor, connection, msg)
    # display the PostgreSQL database server version
    #db_version = cursor.fetchone()
    #print(db_version)

    close_SQL_connection(cursor, connection)

if __name__ == '__main__':
    main()
    
