# import psycopg2



# print(conn)

from datetime import datetime
from datetime import timedelta
import psycopg2
from psycopg2.extras import execute_values
from config import config
import json

##############################################################################
#                                                                             
#
#
#
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
        params = config(filename='database.ini', section='postgresql')

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
##############################################################################
#                                                                            #
#                   PSQL CRUD Classes: CREATE                                #
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
    def __init__(self, cursor, connection, psqloperations):
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
        super(psqloperations, self).__init__()
        self.cursor = cursor
        self.connection = connection 

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
            execcommit([postgres_insert_query, record_to_insert], cur, conn)
            count = cur.rowcount
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
            execcommit([postgres_insert_query, record_to_insert], cur, conn)
            count = cur.rowcount
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
        execcommit([postgres_insert_query, record_to_insert], cur, conn)
        count = cur.rowcount
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
            postgres_insert_query = """ INSERT INTO ethusd (sequence, time, price, side, lastsize, bestbid, bestask) VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            record_to_insert = (int(msg['sequence']), msg['time'], float(msg['price']), msg['side'], float(msg['last_size']),float(msg['best_bid']), float(msg['best_ask']))
            execcommit([postgres_insert_query, record_to_insert], cur, conn)
            count = cur.rowcount
##############################################################################
#                                                                            #
#                    PostgreSQL update operations                            #
#                                                                            #
##############################################################################

class psql_update_operations():
    def __init__():
        pass
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
        execcommit(sql, cur, conn)
        returns = cur.fetchall()
        print(returns)

##############################################################################
#                                                                            #
#                    PostgreSQL Delete operations                            #
#                                                                            #
##############################################################################
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

    def set_data_model(cur, conn):
            # function that asks postgres if it can receive insert messages
        # create the snapshots table
        postgres_create_query_1 = """ CREATE TABLE IF NOT EXISTS snapshots(tstamp TIMESTAMP, snapshot_connection_id TEXT, snapshot_reference_id TEXT, bids json, asks json);""" 
        # create the messages table for l2update messages
        postgres_create_query_2 = """ CREATE TABLE IF NOT EXISTS messages(tstamp TIMESTAMP, snapshot_connection_id TEXT, snapshot_reference_id TEXT, changes json);"""
        # create the messages table for ticker messages
        #postgres_create_query_3 = """ CREATE TABLE IF NOT EXISTS ticker(tstamp TIMESTAMP, snapshot_connection_id TEXT, snapshot_reference_id TEXT, message json);"""
        execcommit(postgres_create_query_1, cur, conn)
        execcommit(postgres_create_query_2, cur, conn)
        
class psql_read_operations(object):
    """
    psql methods to fetch data from the postgres server

    Attributes
    ----------
        None
    
    Methods
    -------
        get_last_tstamp(cur, conn)
    
        custom_sql_fetch(cur, conn, sql)
            
    """
    def get_last_tstamp(cur, conn):
        sql = """ select time from ethusd order by time desc limit 1;"""
        execcommit(sql, cur, conn)
        returns = cur.fetchall()
        print(returns[0][0])
        return returns[0][0]

    def custom_sql_fetch(cur, conn, sql):
        execcommit(sql, cur, conn)
        returns = cur.fetchall()
        print(returns)
        return returns[0][0]

class psql_insert_operations():
    def __init__(self):
        pass



def main():
    """
    test methods to check the operation of the script. 
    """
    cursor, connection = open_SQL_connection()
    print("doing some stuff in the meantime")
    latest_stamp = get_last_tstamp(cursor, connection)
    print(latest_stamp)
    start_stamp = latest_stamp - timedelta(seconds=10)
    sql_cmd = """ SELECT SUM(lastsize) AS TOTAL FROM ethusd WHERE time BETWEEN '{}' AND '{}' ;""".format(start_stamp, latest_stamp);
    sumout = custom_sql_fetch(cursor, connection, sql_cmd)
    print(sumout)
    
    # execute a statement
    #msg = {'type':"snapshot", 'product_id':"ETH-USD", 'bids':[[123,0.1], [124, 0.5]], 'asks':[[125,0.5], [126,1]]}
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
    
