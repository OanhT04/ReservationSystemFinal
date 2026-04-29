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
#IP address that backups run on
REPLICATION_HOST = "127.0.0.1"

#-- HeartBeat/Fault tolerance; every 2 seconds primary pings
HEARTBEAT_INTERVAL = 2.0
#after back up misses 3 intervals, it triggers failure
HEARTBEAT_TIMEOUT = 6.0
# backup port = primary port + HEARTBEAT_PORT_OFFSET (e.g. primary 6001 -> backup 7001)
HEARTBEAT_PORT_OFFSET = 1000

#Maps each primary port to its backup port, derived from offset above
#used in run_all.py and gateway.py so gateway knows which port to retry if primary fails
BACKUP_MAP = {
    port: port + HEARTBEAT_PORT_OFFSET
    for _, port in RESTAURANT_SERVICE_MAP.values()
}

#-- protocol
BUFFER_SIZE = 4096
ENCODING = "utf-8"