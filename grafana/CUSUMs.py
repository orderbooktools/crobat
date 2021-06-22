## in this document we implement simple changepoint detection on the stream of ticker data
## the point of this is to be able to show custom statistics on the grafana dashboard
## for data streasm

import pandas as pd
import math
import copy
import numpy as np
import matplotlib.pyplot as plt
import datetime 
from sqlconnection import execcommit
class CUSUM(object): 
    def __init__(self, l0, epsilon, volm, h, timestamp, SPRT_up=0, SPRT_dn=0, run_min_up=0, run_min_dn=0, CUSUM_dn=0, CUSUM_up=0, deltatime=0):
        # from args
        self.l0 = l0
        self.volm = volm
        self.deltatime = deltatime
        self.h = h
        self.epsilon = epsilon
        self.alarm_up = False
        self.alarm_dn = False
        self.active = 0
        self.active_stamp = datetime.datetime(1900,1,1)
        self.timestamp = datetime.datetime(1900,1,1)
        #derived
        self.SPRT_up = SPRT_up
        self.SPRT_dn = SPRT_dn
        self.run_min_dn = run_min_dn
        self.run_min_up = run_min_up
        self.CUSUM_dn = CUSUM_dn
        self.CUSUM_up = CUSUM_up

    def Reset_CUSUM(self):
        self.SPRT_up = 0
        self.run_min_up = 0
        self.CUSUM_up = 0
        self.SPRT_dn = 0
        self.run_min_dn = 0
        self.CUSUM_dn = 0
        self.active = 0 if (self.alarm_dn or not(self.alarm_up))  else self.active 
        self.alarm_up = False
        self.alarm_dn = False 

    def Update(self, l0, volm, deltatime, timestamp):
        #print(self.SPRT_up, self.SPRT_dn)
        # CUSUM values 
        #print("args", type(l0), type(volm), type(deltatime), type(timestamp), type(self.epsilon))
        self.timestamp = timestamp
        self.SPRT_up +=  volm*math.log(1 + self.epsilon) - deltatime*l0*self.epsilon
        self.SPRT_dn +=  volm*math.log(1-self.epsilon) + deltatime*l0*self.epsilon
        self.run_min_up = min(self.run_min_up, self.SPRT_up)
        self.run_min_dn = min(self.run_min_dn, self.SPRT_dn)
        self.CUSUM_up = self.SPRT_up - self.run_min_up
        self.CUSUM_dn = self.SPRT_dn - self.run_min_dn
        #alarm states
        if self.CUSUM_dn > self.h:
            self.alarm_dn = True 
            self.l0 = self.l0*(1-self.epsilon)
            self.active = 0
        else:
            self.alarm_dn = False

        if self.CUSUM_up > self.h:
            self.alarm_up = True
            self.active += 1 
            self.active_stamp = timestamp
            self.l0 = self.l0*(1+self.epsilon)
        else:
            self.alarm_up = False

        if self.alarm_up:
            self.SPRT_up = 0
            self.run_min_up = 0
            self.CUSUM_up = 0
            self.SPRT_dn = 0
            self.run_min_dn = 0
            self.CUSUM_dn = 0
            self.active = 0 if (self.alarm_dn or not(self.alarm_up))  else self.active 
            self.alarm_up = False
            self.alarm_dn = False 
            print("alarm breached on the upside")
        elif self.alarm_dn:
            self.SPRT_up = 0
            self.run_min_up = 0
            self.CUSUM_up = 0
            self.SPRT_dn = 0
            self.run_min_dn = 0
            self.CUSUM_dn = 0
            self.active = 0 if (self.alarm_dn or not(self.alarm_up))  else self.active 
            self.alarm_up = False
            self.alarm_dn = False 
            print("alarm breached on the downside")
        else:
            pass

    def set_active_flags(self, timestamp, deadline):
        if (timestamp - self.active_stamp).total_seconds() < deadline:
            pass
            #print("dissipating",(timestamp - self.active_stamp).total_seconds())
            #self.active =
        else:
            self.active = 0

    def get_vars(self):
        out_list = [self.SPRT_up, self.run_min_up, self.CUSUM_up, self.SPRT_dn, self.run_min_dn, self.CUSUM_dn, self.alarm_up, self.alarm_dn, self.active]
        return out_list

    def check_up_alarm(self):
        if self.alarm_up:
            return 1
        else:
            return 0 

    def check_dn_alarm(self):
        if self.alarm_dn:
            return 1 
        else:
            return 0

    def write_to_tsdb(self, cur, conn):
        postgres_insert_query = """ INSERT INTO CUSUM (time, SPRTup, runminup, CUSUMup, SPRTdn, runmindn, CUSUMdn, alarmup, alarmdn, active) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        record_to_insert = (
                    self.timestamp, self.SPRT_up, self.run_min_up, self.CUSUM_up,
                    self.SPRT_dn, self.run_min_dn, self.CUSUM_dn, self.alarm_up, self.alarm_dn,
                    self.active
                    )
        execcommit([postgres_insert_query,record_to_insert], cur, conn)