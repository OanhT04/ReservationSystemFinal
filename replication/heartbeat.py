#TODO
import socket
import threading
import time
import logging
from common.protocol import sendMessage, receiveMessage
from common.config import HEARTBEAT_INTERVAL, HEARTBEAT_TIMEOUT, HEARTBEAT_PORT_OFFSET, REPLICATION_HOST

"""
Helper classes
Heart Beat sender - on primary; pings the back up every heart beat interval from config

Heart Beach Monitor -  on back up; will be used for back up to track time elapsed from last ping, 
call failure after HEARTBEAR_TIMEOUT
"""


#maybe run on primary as daemon thread
class HeartbeatSender:
    def __init__(self, primary_port): 
        #This will be the port primary uses to send heart beat to back up
        self.hb_port = primary_port + HEARTBEAT_PORT_OFFSET
        
    def run(self):  # daemon thread, loop forever until stop; 
            # try TCP connect to backup heart beat port, send ping every HEARTBEAT_INTERVAL, receive pong, close
            time.sleep(HEARTBEAT_INTERVAL)
        
            

"""Runs on back up node as daemon thread
if no pings arrive within timeout, signal failure"""
class HeartbeatMonitor:
    def __init__(self, primary_port, on_failure=None):
        self.listen_port = primary_port + HEARTBEAT_PORT_OFFSET
        self.last_seen = time.time()
        self.on_failure = on_failure
        self.fired = False
    def run(self):
        pass
        # spawn _listen_loop as thread
        # run _watchdog_loop blocking
    def listen_loop(self):
        pass
        # TCP server on self.listen_port
        # each connection: receiveMessage, update self.last_seen, sendMessage pong
    def watch_loop(self):
        while True:
            if time.time() - self.last_seen > HEARTBEAT_TIMEOUT and not self.fired:
                self.fired = True
                self.on_failure()
            time.sleep(1.0)
        pass