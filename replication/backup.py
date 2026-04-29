"""
backup.py - Backup node that promotes to primary on failure.

Wraps a ReservationService on the backup port.
HeartbeatMonitor records primary heartbeats (same TCP port as the backup service).
If no ping within HEARTBEAT_TIMEOUT, promote() flips the service into primary mode.

Failover transparency:
When promotion fires, promote() mutates RESTAURANT_SERVICE_MAP in-place so that
the gateway's getServiceAddress() immediately returns the backup's host and port
instead of the dead primary's.  Because RESTAURANT_SERVICE_MAP is a plain Python
dict imported by reference in every module, writing to it here is visible to the
gateway thread instantly with no additional coordination needed.  After this update
the gateway routes directly to the promoted backup with no retry delay.
"""

import logging

from common.config import RESTAURANT_SERVICE_MAP, REPLICATION_HOST
from replication.heartbeat import HeartbeatMonitor

logger = logging.getLogger(__name__)


class BackupService:
    def __init__(self, reservation_service, primary_port, heartbeat_monitor=None):
        self.svc = reservation_service
        # Only set on_failure here if no external monitor was injected;
        # avoids overwriting a pre-configured monitor passed in by tests.
        if heartbeat_monitor is None:
            self.monitor = HeartbeatMonitor(primary_port, on_failure=self.promote)
        else:
            self.monitor = heartbeat_monitor
            self.monitor.on_failure = self.promote
        self.svc.set_heartbeat_observer(self.monitor.record_ping)

    def start(self):
        self.monitor.run()
        self.svc.start()

    def promote(self):
        logger.warning("PRIMARY FAILED — BACKUP PROMOTED (primary port %s)", self.monitor.primary_port)
        self.svc.promote_to_primary()

        # Update RESTAURANT_SERVICE_MAP in-place so the gateway's getServiceAddress()
        # immediately returns the backup's address instead of the dead primary's port.
        
        # Without; every post-failure request would first attempt the dead primary
        # and wait for a connection refusal before retrying on the backup port.
        
        backup_host = self.svc.host
        backup_port = self.svc.port
        for rid, (host, port) in RESTAURANT_SERVICE_MAP.items():
            if port == self.monitor.primary_port:
                RESTAURANT_SERVICE_MAP[rid] = (backup_host, backup_port)
                logger.warning(
                    "RESTAURANT_SERVICE_MAP updated: %s now points to backup %s:%s",
                    rid, backup_host, backup_port,
                )
                break