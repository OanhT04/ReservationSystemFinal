"""
backup.py - Backup node that promotes to primary on failure.

Wraps a ReservationService on the backup port.
HeartbeatMonitor records primary heartbeats (same TCP port as the backup service).
If no ping within HEARTBEAT_TIMEOUT, promote() flips the service into primary mode.

Note: RESTAURANT_SERVICE_MAP / gateway must be updated (or the process rebound to the
primary port) for clients to reach the promoted node; that is outside this module.
"""

import logging
import threading

from replication.heartbeat import HeartbeatMonitor

logger = logging.getLogger(__name__)


class BackupService:
    def __init__(self, reservation_service, primary_port, heartbeat_monitor=None):
        self.svc = reservation_service
        self.monitor = heartbeat_monitor or HeartbeatMonitor(primary_port, on_failure=self.promote)
        self.monitor.on_failure = self.promote
        self.svc.set_heartbeat_observer(self.monitor.record_ping)

    def start(self):
        self.monitor.run()
        self.svc.start()

    def promote(self):
        logger.warning("PRIMARY FAILED — BACKUP PROMOTED (primary port %s)", self.monitor.primary_port)
        self.svc.promote_to_primary()
