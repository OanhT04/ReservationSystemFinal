"""
run_all.py - Start the entire system.

Terminal 1: python run_all.py
Terminal 2: python client/client.py
"""

import sys
import os
import time
import threading
import logging

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

from common.config import RESTAURANT_SERVICE_MAP
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

    # Start primary reservation services (one per restaurant)
    for rid, (host, port) in RESTAURANT_SERVICE_MAP.items():
        logger.info(f"Starting {rid} on port {port}...")
        svc = ReservationService(rid, host, port, DATA_PATH)
        threading.Thread(target=svc.start, daemon=True).start()
        time.sleep(0.2)

    #to do -- start back up reservation services

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
