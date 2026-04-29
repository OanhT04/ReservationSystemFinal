"""Heartbeat from primary toward backup reservation port (piggy-backed on TCP service)."""

import socket
import threading
import time
import logging

from common.protocol import sendMessage, receiveMessage
from common.config import HEARTBEAT_INTERVAL, HEARTBEAT_TIMEOUT, BACKUP_MAP, REPLICATION_HOST

logger = logging.getLogger(__name__)


class HeartbeatSender:
    def __init__(self, primary_port, backup_host=None, stop_event=None):
        self.primary_port = primary_port
        self.backup_port = BACKUP_MAP.get(primary_port)
        self.backup_host = backup_host or REPLICATION_HOST
        self.interval = HEARTBEAT_INTERVAL
        self._stop = stop_event if stop_event is not None else threading.Event()

    def run(self):
        while not self._stop.is_set():
            if self.backup_port is None:
                break
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            try:
                sock.connect((self.backup_host, self.backup_port))
                sendMessage(
                    sock,
                    {
                        "action": "heartbeat",
                        "primary_port": self.primary_port,
                    },
                )
                resp = receiveMessage(sock)
                if resp.get("status") != "ok":
                    logger.debug("Heartbeat unexpected response: %s", resp)
            except OSError as e:
                logger.debug("Heartbeat ping failed (backup may be down): %s", e)
            finally:
                # always close — prevents fd leak when connect/send/recv raises
                sock.close()
            if self._stop.wait(self.interval):
                break


class HeartbeatMonitor:
    """Watches time since last heartbeat from primary (pings arrive on backup ReservationService)."""

    def __init__(self, primary_port, on_failure=None):
        self.primary_port = primary_port
        # None until the first ping is recorded — prevents sudden promotion
        # before the primary has had a chance to send its first heartbeat.
        self.last_seen = None
        self.on_failure = on_failure
        self._fired = False
        self._stop = threading.Event()

    def record_ping(self):
        self.last_seen = time.time()

    def run(self):
        threading.Thread(target=self._watchdog_loop, daemon=True).start()

    def _watchdog_loop(self):
        while not self._stop.is_set():
            # Skip the timeout check until we've seen at least one ping,
            # and don't fire more than once.
            if self._fired or self.last_seen is None:
                time.sleep(0.5)
                continue
            if time.time() - self.last_seen > HEARTBEAT_TIMEOUT:
                self._fired = True
                if self.on_failure:
                    self.on_failure()
            time.sleep(0.5)

    def stop(self):
        self._stop.set()