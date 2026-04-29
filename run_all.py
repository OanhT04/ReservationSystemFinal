"""
run_all.py - Start the entire system.

Terminal 1: python run_all.py
Terminal 2: python client/client.py
- Ctrl+C to stop the system when done.
- For viewing logs, run in a separate terminal:
"""

import sys
import os
import time
import threading
import logging

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

from common.config import RESTAURANT_SERVICE_MAP, BACKUP_MAP
from replication.backup import BackupService
from services.reservation_service import ReservationService
from gateway.gateway import startGateway

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)-20s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("LAUNCHER")

DATA_PATH = os.path.join(PROJECT_ROOT, "data", "restaurants.json")


def main():
    print()
    print("  ================================================")
    print("  Distributed Restaurant Reservation System")
    print("  ================================================")
    print()

    # Start backup nodes first (primaries replicate here before confirming writes)
    for rid, (host, primary_port) in RESTAURANT_SERVICE_MAP.items():
        backup_port = BACKUP_MAP.get(primary_port)
        if backup_port is None:
            continue
        logger.info(f"Starting backup {rid} on port {backup_port}...")
        backup_svc = ReservationService(rid, host, backup_port, DATA_PATH, back_up=True)
        backup = BackupService(backup_svc, primary_port=primary_port)
        threading.Thread(target=backup.start, daemon=True).start()
        time.sleep(0.2)

    # Primary reservation services (one per restaurant)
    for rid, (host, port) in RESTAURANT_SERVICE_MAP.items():
        logger.info(f"Starting {rid} (primary) on port {port}...")
        svc = ReservationService(rid, host, port, DATA_PATH)
        threading.Thread(target=svc.start, daemon=True).start()
        time.sleep(0.2)

    # Start gateway
    logger.info("Starting Gateway on port 5000...")
    time.sleep(0.3)

    print()
    print("  All services started!")
    print()
    print("  Run client:  python client/client.py")
    print("  Press Ctrl+C to stop.")
    print()

    try:
        startGateway()
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
