#TODO
from common.protocol import sendMessage, receiveMessage
import logging
import socket

"""
Helper class for reservation_service (primary) to call on every write

1. opens a TCP connection to back up, sends write, waits for {"status": "ok"} 
2. primary reservation_services will call replicate, wait for response from back up and then confirms to client
"""
# #use protocol.py sendMessage/receiveMessage

class PrimaryReplicator:
    def __init__(self, backup_host, backup_port, timeout=3.0): 
        self.backup_host = backup_host
        self.backup_port = backup_port
        self.timeout = timeout
        
    def replicate(self, message: dict) -> bool:
        # open TCP socket to backup
        # sendMessage(sock, message)
        # response = receiveMessage(sock)
        # return response.get("status") == "ok"
        # catch all errors, return False
        pass