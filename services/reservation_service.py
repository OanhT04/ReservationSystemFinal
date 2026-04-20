"""
reservation_service.py - TCP server for one restaurant.
Add locking + logical clock (TODO comments show where)
    - per table locking with threading.Lock()
    - book table needs to acquire lock before checking availability
    - add lock time out
    - Logical Clock - Lamport for event ordering with a thread.
    Add a method that increments and returns counter
                    and call whenever booking a table or canceling a reservation
                    store time stamp in each reservation record
Add replication + heartbeat (TODO)
    - sync writes to back up; import primary replicator and replicate changes in book table, 
    before confirming to client

"""

import json
import os
import socket
import threading
import time
import logging

from common.protocol import sendMessage, receiveMessage
from common.config import LOCK_TIMEOUT

logger = logging.getLogger(__name__)


class ReservationService:

    def __init__(self, restaurant_id, host, port, data_path, back_up = False):
        #back up = false bc the class will b used for both primary and back up node; 
        self.restaurant_id = restaurant_id
        self.host = host
        self.port = port
        with open(data_path, "r") as f:
            all_data = json.load(f)
        self.restaurant_info = all_data[restaurant_id]

        self.reservations = {}
        self.running = False

        # TODO 2: Add per-table locks
        # self.table_locks = {}
        # for table_id in self.restaurant_info["tables"]:
        #     self.table_locks[table_id] = threading.Lock()

        # TODO 2: Add logical clock
        # self.logical_clock = 0
        # self.clock_lock = threading.Lock()

        # TODO 3: Add replication 
        # self.replicator = PrimaryReplicator(primary_port=port)

        # TODO 3: Add heartbeat
        # self.heartbeat_sender = HeartbeatSender(...)

    def start(self):
        self.running = True
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(20)
        server.settimeout(1.0)
        logger.info(f"[{self.restaurant_info['name']}] on {self.host}:{self.port}")

        while self.running:
            try:
                conn, addr = server.accept()
                threading.Thread(target=self._handleClient, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
        server.close()

    def stop(self):
        self.running = False

    def _handleClient(self, conn, addr):
        try:
            msg = receiveMessage(conn)
            action = msg.get("action")

            if action == "get_info":
                response = self._getRestaurantInfo()
            elif action == "check_availability":
                response = self._checkAvailability(msg)
            elif action == "book":
                response = self._bookTable(msg)
            elif action == "cancel":
                response = self._cancelReservation(msg)
            elif action == "list_reservations":
                response = self._listReservations(msg)
            else:
                response = {"status": "error", "message": f"Unknown action: {action}"}

            sendMessage(conn, response)
        except Exception as e:
            logger.error(f"Error: {e}")
            try:
                sendMessage(conn, {"status": "error", "message": str(e)})
            except Exception:
                pass
        finally:
            conn.close()

    # ── Handlers ──────────────────────────────────────────────────

    def _getRestaurantInfo(self):
        return {
            "status": "ok",
            "restaurant_id": self.restaurant_id,
            "name": self.restaurant_info["name"],
            "cuisine": self.restaurant_info.get("cuisine", ""),
            "address": self.restaurant_info.get("address", ""),
            "menu_url": self.restaurant_info.get("menu_url", ""),
            "description": self.restaurant_info.get("description", ""),
            "price_range": self.restaurant_info.get("price_range", ""),
            "rating": self.restaurant_info.get("rating", 0),
            "features": self.restaurant_info.get("features", []),
            "tables": self.restaurant_info["tables"],
            "timeslots": self.restaurant_info["timeslots"],
        }

    def _checkAvailability(self, msg):
        date = msg.get("date")
        timeslot = msg.get("timeslot")
        party_size = msg.get("party_size", 1)

        available = []
        for table_id, table_info in self.restaurant_info["tables"].items():
            if table_info["capacity"] < party_size:
                continue
            key = (self.restaurant_id, table_id, f"{date}_{timeslot}")
            if key not in self.reservations:
                available.append({
                    "table_id": table_id,
                    "capacity": table_info["capacity"],
                    "location": table_info["location"],
                })

        return {
            "status": "ok",
            "restaurant_id": self.restaurant_id,
            "date": date,
            "timeslot": timeslot,
            "available_tables": available,
        }

    def _bookTable(self, msg):
        table_id = msg.get("table_id")
        date = msg.get("date")
        timeslot = msg.get("timeslot")
        customer_name = msg.get("customer_name")
        party_size = msg.get("party_size", 1)
        contact = msg.get("contact", "")

        if table_id not in self.restaurant_info["tables"]:
            return {"status": "error", "message": f"Table {table_id} does not exist"}

        key = (self.restaurant_id, table_id, f"{date}_{timeslot}")
        if key in self.reservations:
            return {"status": "error", "message": f"Table {table_id} at {timeslot} is already booked"}

        # TODO  2: Add lock.acquire() / lock.release()
        # TODO  3: Add self.replicator.replicate()

        reservation = {
            "restaurant_id": self.restaurant_id,
            "table_id": table_id,
            "date": date,
            "timeslot": timeslot,
            "customer_name": customer_name,
            "party_size": party_size,
            "contact": contact,
            "created_at": time.time(),
        }
        self.reservations[key] = reservation
        logger.info(f"BOOKED: {customer_name} -> {table_id} at {date} {timeslot}")

        return {"status": "ok", "message": "Reservation confirmed!", "reservation": reservation}

    def _cancelReservation(self, msg):
        table_id = msg.get("table_id")
        date = msg.get("date")
        timeslot = msg.get("timeslot")

        key = (self.restaurant_id, table_id, f"{date}_{timeslot}")
        if key not in self.reservations:
            return {"status": "error", "message": "No reservation found to cancel"}

        # TODO Add lock.acquire() / lock.release()
        # TODO Replication: Add self.replicator.replicate()

        cancelled = self.reservations[key]
        del self.reservations[key]
        logger.info(f"CANCELLED: {table_id} at {date} {timeslot}")

        return {"status": "ok", "message": "Reservation cancelled", "cancelled": cancelled}

    def _listReservations(self, msg):
        date = msg.get("date")
        results = []
        for key, reservation in self.reservations.items():
            if date and reservation.get("date") != date:
                continue
            results.append(reservation)
        return {"status": "ok", "reservations": results, "count": len(results)}
