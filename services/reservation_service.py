"""
reservation_service.py - TCP server for one restaurant.
Per-table locks, Lamport logical clock, replication to backup, heartbeat pings.
"""

import json
import socket
import threading
import time
import logging

from common.protocol import sendMessage, receiveMessage
from common.config import LOCK_TIMEOUT, BACKUP_MAP, REPLICATION_HOST
from replication.primary import PrimaryReplicator
from replication.heartbeat import HeartbeatSender

logger = logging.getLogger(__name__)


def _key_to_list(key):
    return [key[0], key[1], key[2]]


class ReservationService:

    def __init__(self, restaurant_id, host, port, data_path, back_up=False):
        self.restaurant_id = restaurant_id
        self.host = host
        self.port = port
        self.back_up = back_up
        with open(data_path, "r") as f:
            all_data = json.load(f)
        self.restaurant_info = all_data[restaurant_id]

        self.reservations = {}
        self.running = False

        self.table_locks = {}
        for table_id in self.restaurant_info["tables"]:
            self.table_locks[table_id] = threading.Lock()

        self.logical_clock = 0
        self.clock_lock = threading.Lock()

        backup_port = BACKUP_MAP.get(port)
        self.replicator = None
        if not back_up and backup_port is not None:
            self.replicator = PrimaryReplicator(REPLICATION_HOST, backup_port)

        self._heartbeat_sender = None
        self._heartbeat_stop = threading.Event()
        self._on_heartbeat = None
        self._is_promoted_primary = False

    def _next_lamport(self):
        with self.clock_lock:
            self.logical_clock += 1
            return self.logical_clock

    def _advance_lamport_from_peer(self, ts):
        if ts is None:
            return
        try:
            t = int(ts)
        except (TypeError, ValueError):
            return
        with self.clock_lock:
            self.logical_clock = max(self.logical_clock, t)

    def start(self):
        self.running = True
        if not self.back_up and self.port in BACKUP_MAP:
            self._heartbeat_sender = HeartbeatSender(
                self.port,
                backup_host=REPLICATION_HOST,
                stop_event=self._heartbeat_stop,
            )
            threading.Thread(target=self._heartbeat_sender.run, daemon=True).start()

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
        self._heartbeat_stop.set()
        server.close()

    def stop(self):
        self.running = False
        self._heartbeat_stop.set()

    def set_heartbeat_observer(self, fn):
        """Called on backup when a heartbeat TCP message is received from the primary."""
        self._on_heartbeat = fn

    def promote_to_primary(self):
        """Backup takes over as authoritative node (no longer back_up-only)."""
        if self._is_promoted_primary:
            return
        self._is_promoted_primary = True
        self.back_up = False
        self._on_heartbeat = None
        backup_target = BACKUP_MAP.get(self.port)
        if backup_target is not None:
            self.replicator = PrimaryReplicator(REPLICATION_HOST, backup_target)
        else:
            self.replicator = None
        logger.warning("Backup promoted to primary on %s:%s", self.host, self.port)

    def _handleClient(self, conn, addr):
        try:
            msg = receiveMessage(conn)
            action = msg.get("action")

            if action == "heartbeat":
                if self._on_heartbeat:
                    self._on_heartbeat()
                response = {"status": "ok", "message": "pong"}
            elif action == "apply_replication":
                response = self._applyReplication(msg)
            elif action == "get_info":
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

    def _applyReplication(self, msg):
        """Apply a replicated write from the primary (backup node)."""
        operation = msg.get("operation")
        key_parts = msg.get("key")
        if operation not in ("book", "cancel") or not isinstance(key_parts, list) or len(key_parts) != 3:
            return {"status": "error", "message": "Invalid replication payload"}
        _, table_id, _ = key_parts
        if table_id not in self.table_locks:
            return {"status": "error", "message": "Unknown table"}

        lock = self.table_locks[table_id]
        if not lock.acquire(timeout=LOCK_TIMEOUT):
            return {"status": "error", "message": "Lock timeout"}

        try:
            key = tuple(key_parts)
            if operation == "book":
                reservation = msg.get("reservation") or {}
                self._advance_lamport_from_peer(reservation.get("lamport_timestamp"))
                self.reservations[key] = reservation
            else:
                res = msg.get("reservation")
                if isinstance(res, dict):
                    self._advance_lamport_from_peer(res.get("cancel_lamport_timestamp"))
                self.reservations.pop(key, None)
            return {"status": "ok"}
        finally:
            lock.release()

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

    def _replicate_book(self, key, reservation):
        if self.replicator is None or self.back_up:
            return True
        return self.replicator.replicate(
            {
                "action": "apply_replication",
                "operation": "book",
                "key": _key_to_list(key),
                "reservation": reservation,
            }
        )

    def _replicate_cancel(self, key, cancelled_snapshot):
        if self.replicator is None or self.back_up:
            return True
        return self.replicator.replicate(
            {
                "action": "apply_replication",
                "operation": "cancel",
                "key": _key_to_list(key),
                "reservation": cancelled_snapshot,
            }
        )

    def _bookTable(self, msg):
        table_id = msg.get("table_id")
        date = msg.get("date")
        timeslot = msg.get("timeslot")
        customer_name = msg.get("customer_name")
        party_size = msg.get("party_size", 1)
        contact = msg.get("contact", "")

        if table_id not in self.restaurant_info["tables"]:
            return {"status": "error", "message": f"Table {table_id} does not exist"}

        lock = self.table_locks[table_id]
        got = lock.acquire(timeout=LOCK_TIMEOUT)
        if not got:
            return {"status": "error", "message": "Could not acquire table lock (timed out)"}

        try:
            key = (self.restaurant_id, table_id, f"{date}_{timeslot}")
            if key in self.reservations:
                return {"status": "error", "message": f"Table {table_id} at {timeslot} is already booked"}

            lamport_ts = self._next_lamport()
            reservation = {
                "restaurant_id": self.restaurant_id,
                "table_id": table_id,
                "date": date,
                "timeslot": timeslot,
                "customer_name": customer_name,
                "party_size": party_size,
                "contact": contact,
                "created_at": time.time(),
                "lamport_timestamp": lamport_ts,
            }

            if not self._replicate_book(key, reservation):
                return {"status": "error", "message": "Backup replication failed"}

            self.reservations[key] = reservation
            logger.info(f"BOOKED: {customer_name} -> {table_id} at {date} {timeslot}")

            return {"status": "ok", "message": "Reservation confirmed!", "reservation": reservation}
        finally:
            lock.release()

    def _cancelReservation(self, msg):
        table_id = msg.get("table_id")
        date = msg.get("date")
        timeslot = msg.get("timeslot")

        if table_id not in self.restaurant_info["tables"]:
            return {"status": "error", "message": f"Table {table_id} does not exist"}

        key = (self.restaurant_id, table_id, f"{date}_{timeslot}")

        lock = self.table_locks[table_id]
        got = lock.acquire(timeout=LOCK_TIMEOUT)
        if not got:
            return {"status": "error", "message": "Could not acquire table lock (timed out)"}

        try:
            if key not in self.reservations:
                return {"status": "error", "message": "No reservation found to cancel"}

            cancel_lamport = self._next_lamport()
            cancelled = dict(self.reservations[key])
            cancelled["cancel_lamport_timestamp"] = cancel_lamport

            if not self._replicate_cancel(key, cancelled):
                return {"status": "error", "message": "Backup replication failed"}

            del self.reservations[key]
            logger.info(f"CANCELLED: {table_id} at {date} {timeslot}")

            return {"status": "ok", "message": "Reservation cancelled", "cancelled": cancelled}
        finally:
            lock.release()

    def _listReservations(self, msg):
        date = msg.get("date")
        results = []
        for key, reservation in self.reservations.items():
            if date and reservation.get("date") != date:
                continue
            results.append(reservation)
        return {"status": "ok", "reservations": results, "count": len(results)}
