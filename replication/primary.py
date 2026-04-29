"""Primary → backup synchronous replication."""

import logging
import socket

from common.protocol import sendMessage, receiveMessage

logger = logging.getLogger(__name__)


class PrimaryReplicator:
    def __init__(self, backup_host, backup_port, timeout=3.0):
        self.backup_host = backup_host
        self.backup_port = backup_port
        self.timeout = timeout

    def replicate(self, message: dict) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.backup_host, self.backup_port))
            sendMessage(sock, message)
            response = receiveMessage(sock)
            sock.close()
            return response.get("status") == "ok"
        except (OSError, ConnectionError, ValueError, TypeError, KeyError) as e:
            logger.warning("Replication to backup failed: %s", e)
            return False
