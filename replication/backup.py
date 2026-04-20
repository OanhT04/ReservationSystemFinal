from logging import logger
import threading

"""
backup.py - Backup node that promotes to primary on failure.

Wraps a ReservationService running on the backup port.
Starts the HeartbeatMonitor which watches for primary failure.
When the monitor fires, promote() flips the backup into primary mode.

"""

#TODO 
class BackupService:
    def __init__(self, reservation_service, primary_port, heartbeat_monitor):
        self.svc = reservation_service       # ReservationService(is_backup=True)
        pass
        
        
        self.monitor.on_failure = self.promote
    def start(self):
        threading.Thread(target=self.monitor.run, daemon=True).start()
        self.svc.start()  # blocks
    def promote(self):
        logger.warning("PRIMARY FAILED — BACKUP PROMOTED")
        pass
