"""
All ports and settings are done.
"""
#--- Gateway
#Address where the REST gate way listens and every client request goes here
GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 5000

#--- Restaurant Services
#maps each restaurant ID to host and port, gateway looks up this map to know where to send it
#add new restaurants here aswell
RESTAURANT_SERVICE_MAP = {
    "restaurant_1": ("127.0.0.1", 6001),
    "restaurant_2": ("127.0.0.1", 6002),
    "restaurant_3": ("127.0.0.1", 6003),
    "restaurant_4": ("127.0.0.1", 6004),
    "restaurant_5": ("127.0.0.1", 6005),
    "restaurant_6": ("127.0.0.1", 6006),
}



#---Concurrency 
#timeout for thread waiting to access table lock before giving up
LOCK_TIMEOUT = 5.0

#--- Replication
#Maps each primary port to its back up port
#used in run_all.py and gateway.py so gateway knows which port to retry if primary fails
BACKUP_MAP = {
    6001: 7001, 6002: 7002, 6003: 7003, 6004: 7004, 6005: 7005, 6006: 7006,
}

#IP address that backups run on
REPLICATION_HOST = "127.0.0.1"

#-- HeartBeat/Fault tolerance; every 2 seconds primary pings
HEARTBEAT_INTERVAL = 2.0
#after back up misses 3 intervals, it triggers failure
HEARTBEAT_TIMEOUT = 6.0
# primary is on 6001 and heart beat is one 7001
HEARTBEAT_PORT_OFFSET = 1000

#-- protocol
BUFFER_SIZE = 4096
ENCODING = "utf-8"
