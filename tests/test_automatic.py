"""
Automated tests: Double booking, Lamport clock, Heartbeat monitor, Backup promotion
Uses stdlib unittest only — run via `python run_tests.py`.
"""

import os
import threading
import unittest
from unittest.mock import Mock, patch

import time

from replication.backup import BackupService
from replication.heartbeat import HeartbeatMonitor
from services.reservation_service import ReservationService


class DoubleBookingTests(unittest.TestCase):
    """Same table/date/timeslot must not admit two confirmations."""

    def setUp(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_path = os.path.join(root, "data", "restaurants.json")
        # Port not listed in BACKUP_MAP so replication is skipped (no backup required)
        self.svc = ReservationService(
            "restaurant_1", "127.0.0.1", 9999, self.data_path, back_up=False
        )

    def test_double_booking(self):
        msg = {
            "table_id": "T1",
            "date": "2026-05-01",
            "timeslot": "18:00",
            "customer_name": "Alice",
            "party_size": 2,
            "contact": "0000000000",
        }
        print()

        print("first booking:")
        time.sleep(0.5)
        print(f"customer name: {msg['customer_name']}")
        time.sleep(0.5)
        print(f"table id: {msg['table_id']}")
        time.sleep(0.5)
        print(f"date: {msg['date']}")
        time.sleep(0.5)
        print(f"timeslot: {msg['timeslot']}")
        time.sleep(0.5)
        print(f"party size: {msg['party_size']}")
        time.sleep(0.5)
        print(f"contact: {msg['contact']}")
        time.sleep(0.5)
        print()
        time.sleep(2)


        first = self.svc._bookTable(dict(msg, customer_name="Alice"))
        self.assertEqual(first["status"], "ok")
        print("first booking response:")
        time.sleep(0.5)
        print(f"status: {first['status']}")
        time.sleep(0.5)
        print(f"message: {first['message']}")
        time.sleep(0.5)
        print(first)
        time.sleep(0.5)
        print()
        time.sleep(2)

        second_msg = {
            "table_id": "T1",
            "date": "2026-05-01",
            "timeslot": "18:00",
            "customer_name": "Bob",
            "party_size": 2,
            "contact": "1111111111",
        }
        second = self.svc._bookTable(dict(second_msg, customer_name="Bob"))
        print("second booking:")
        time.sleep(0.5)
        print(f"customer name: {second_msg['customer_name']}")
        time.sleep(0.5)
        print(f"table id: {second_msg['table_id']}")
        time.sleep(0.5)
        print(f"date: {second_msg['date']}")
        time.sleep(0.5)
        print(f"timeslot: {second_msg['timeslot']}")
        time.sleep(0.5)
        print(f"party size: {second_msg['party_size']}")
        time.sleep(0.5)
        print(f"contact: {second_msg['contact']}")
        time.sleep(0.5)
        print()
        time.sleep(2)


        self.assertEqual(second["status"], "error")
        self.assertIn("already booked", second["message"].lower())
        print("second booking response:")
        time.sleep(0.5)
        print(f"status: {second['status']}")
        time.sleep(0.5)
        print(f"message: {second['message']}")
        time.sleep(0.5)
        print(second)
        time.sleep(0.5)
        print()

class LamportClockTests(unittest.TestCase):
    """Lamport clock must be advanced correctly."""

    def setUp(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_path = os.path.join(root, "data", "restaurants.json")
        # Port not listed in BACKUP_MAP so replication is skipped (no backup required)
        self.svc = ReservationService(
            "restaurant_1", "127.0.0.1", 9999, self.data_path, back_up=False
        )

    def test_lamport_clock(self):
        msg = {
            "table_id": "T1",
            "date": "2026-05-01",
            "timeslot": "18:00",
            "customer_name": "Alice",
            "party_size": 2,
            "contact": "0000000000",
        }

        print("")
        print("")
        print("first booking:")
        time.sleep(0.5)
        print(f"customer name: {msg['customer_name']}")
        time.sleep(0.5)
        print(f"date: {msg['date']}")
        time.sleep(0.5)
        print(f"timeslot: {msg['timeslot']}")
        time.sleep(1)
        first = self.svc._bookTable(dict(msg, customer_name="Alice"))
        self.assertEqual(first["status"], "ok")
        print(f"status: {first['status']}")
        time.sleep(0.5)
        print(f"message: {first['message']}")
        time.sleep(0.5)
        print(f"lamport_ts: {first['reservation']['lamport_ts']}")
        print()
        time.sleep(1)

        # Second booking must use a different slot than the first; otherwise the
        # service correctly rejects it as already booked (see DoubleBookingTests).
        second_msg = {
            "table_id": "T1",
            "date": "2026-05-01",
            "timeslot": "19:00",    
            "customer_name": "Bob",
            "party_size": 2,
            "contact": "1111111111",
        }
        print("second booking:")
        time.sleep(0.5)
        print(f"customer name: {second_msg['customer_name']}")
        time.sleep(0.5)
        print(f"date: {second_msg['date']}")
        time.sleep(0.5)
        print(f"timeslot: {second_msg['timeslot']}")
        time.sleep(1)
        second = self.svc._bookTable(dict(second_msg, customer_name="Bob"))
        self.assertEqual(second["status"], "ok")
        print(f"status: {second['status']}")
        time.sleep(0.5)
        print(f"message: {second['message']}")
        time.sleep(0.5)
        print(f"lamport_ts: {second['reservation']['lamport_ts']}")
        print()
        time.sleep(1)

        
        # Cancel increments the clock and stamps lamport_ts on the snapshot.
        print("cancel booking:")
        time.sleep(0.5)
        print(f"customer name: {second_msg['customer_name']}")
        time.sleep(0.5)
        cancel = self.svc._cancelReservation(dict(second_msg, customer_name="Bob"))
        self.assertEqual(cancel["status"], "ok")
        self.assertGreater(
            cancel["cancelled"]["lamport_ts"],
            second["reservation"]["lamport_ts"],
        )
        print(f"status: {cancel['status']}")
        time.sleep(0.5)
        print(f"message: {cancel['message']}")
        time.sleep(0.5)
        print(f"lamport_ts: {cancel['cancelled']['lamport_ts']}")
        print()
        time.sleep(1)

class HeartbeatMonitorTests(unittest.TestCase):
    """HeartbeatMonitor: backup-side watchdog for primary liveness (see replication/heartbeat.py)."""

    def _wait_until(self, predicate, timeout_sec=3.0, step=0.05):
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            if predicate():
                return True
            time.sleep(step)
        return False

    @patch("replication.heartbeat.HEARTBEAT_TIMEOUT", 0.08)
    def test_on_failure_fires_once_when_primary_silent(self):
        print()
        print()
        time.sleep(0.5)
        print("starting heartbeat monitor on port 6001")
        time.sleep(0.5)
        on_failure = Mock()
        mon = HeartbeatMonitor(6001, on_failure=on_failure)
        mon.last_seen = time.time() - 10.0
        mon.run()
        time.sleep(0.5)
        print("waiting for on_failure to be called")
        time.sleep(0.5)
        self.assertTrue(
            self._wait_until(lambda: on_failure.call_count >= 1),
            "on_failure should run after HEARTBEAT_TIMEOUT without record_ping",
        )
        time.sleep(0.5)
        print("asserting on_failure was called once")
        time.sleep(0.5)
        on_failure.assert_called_once_with()
        time.sleep(0.5)
        print("asserting on_failure was not called again")
        time.sleep(0.5)
        # Further ticks must not invoke the callback again.
        time.sleep(0.4)
        on_failure.assert_called_once_with()
        time.sleep(0.5)
        print("stopping heartbeat monitor")
        time.sleep(0.5)
        mon.stop()


    @patch("replication.heartbeat.HEARTBEAT_TIMEOUT", 3.0)
    def test_on_failure_not_called_while_pings_refresh(self):
        print()
        print()  
        time.sleep(0.5)
        print("starting heartbeat monitor on port 6002")
        time.sleep(0.5)
        on_failure = Mock()
        mon = HeartbeatMonitor(6002, on_failure=on_failure)
        mon.run()

        def pinger():
            for _ in range(40):
                mon.record_ping()
                time.sleep(0.03)

        print("starting pinger thread")
        time.sleep(0.5)
        threading.Thread(target=pinger, daemon=True).start()
        time.sleep(0.5)
        print("waiting for on_failure to not be called")
        time.sleep(0.5)
        self.assertTrue(
            self._wait_until(lambda: on_failure.call_count == 0),
            "on_failure should not be called while pings refresh",
        )
        time.sleep(0.5)
        print("asserting on_failure was not called")
        time.sleep(0.5)
        on_failure.assert_not_called()
        time.sleep(0.5)
        print("stopping heartbeat monitor")
        mon.stop()

    def test_record_ping_refreshes_last_seen(self):
        print()
        print()
        time.sleep(0.5)
        print("starting heartbeat monitor on port 6003")
        time.sleep(0.5)
        mon = HeartbeatMonitor(6003, on_failure=None)
        t0 = time.time()
        time.sleep(0.5)
        print("recording ping")
        time.sleep(0.5)
        mon.record_ping()
        time.sleep(0.5)
        print("asserting last_seen is greater than or equal to t0")
        time.sleep(0.5)
        self.assertGreaterEqual(mon.last_seen, t0)
        time.sleep(0.5)
        print("stopping heartbeat monitor")
        time.sleep(0.5)
        mon.stop()

    def test_clean_shutdown(self):
        print()
        print()
        time.sleep(0.5)
        print("starting heartbeat monitor on port 6004")
        time.sleep(0.5)
        on_failure = Mock()
        mon = HeartbeatMonitor(6004, on_failure=on_failure)
        mon.run()
        time.sleep(0.5)
        print("stopping heartbeat monitor")
        time.sleep(0.5)
        mon.stop()
        time.sleep(0.5)
        print("asserting on_failure was not called")
        time.sleep(0.5)
        on_failure.assert_not_called()

class PrimaryServerFailureTests(unittest.TestCase):
    """Primary stops; backup misses heartbeats and is promoted via BackupService / HeartbeatMonitor."""

    PRIMARY_PORT = 38441
    BACKUP_PORT = 38442

    def _wait_until(self, predicate, timeout_sec=5.0, step=0.05):
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            if predicate():
                return True
            time.sleep(step)
        return False

    # Short ping interval keeps the test brisk. TIMEOUT must be large enough that the watchdog
    # does not beat the primary's first heartbeat (backup setup + sleeps can exceed tens of ms;
    # with TIMEOUT 0.15 the monitor often promoted before any ping arrived).
    @patch("replication.heartbeat.HEARTBEAT_INTERVAL", 0.05)
    @patch("replication.heartbeat.HEARTBEAT_TIMEOUT", 3.0)
    @patch.dict("common.config.BACKUP_MAP", {38441: 38442}, clear=False)
    def test_primary_server_failure(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_path = os.path.join(root, "data", "restaurants.json")

        backup_svc = ReservationService(
            "restaurant_1", "127.0.0.1", self.BACKUP_PORT, data_path, back_up=True
        )
        backup = BackupService(backup_svc, primary_port=self.PRIMARY_PORT)
        monitor = backup.monitor

        primary_svc = ReservationService(
            "restaurant_1", "127.0.0.1", self.PRIMARY_PORT, data_path, back_up=False
        )

        try:
            print()
            print()
            # 1. Start backup (ReservationService listener + HeartbeatMonitor thread).
            print(f"starting backup server on port {self.BACKUP_PORT}")
            time.sleep(0.5)
            threading.Thread(target=backup.start, daemon=True).start()
            time.sleep(0.15)

            # Snapshot before primary: pings from the upcoming primary refresh this timestamp.
            last_seen_before_primary = monitor.last_seen

            # 2. Start primary (HeartbeatSender pings backup over TCP).
            print(f"starting primary server on port {self.PRIMARY_PORT}")
            time.sleep(0.5)
            threading.Thread(target=primary_svc.start, daemon=True).start()
            time.sleep(0.35)

            # 3. Confirm heartbeat flow works (poll: primary startup + first ping can lag on slow hosts).
            print("confirming heartbeat flow works")
            self.assertTrue(
                self._wait_until(
                    lambda: monitor.last_seen > last_seen_before_primary,
                ),
                "last_seen should refresh when primary sends heartbeats to backup",
            )

            # 4. Stop primary (no further heartbeats).
            print(f"stopping primary server on port {self.PRIMARY_PORT}")
            time.sleep(0.5)
            primary_svc.stop()

            # 5. Wait for timeout detection (silence past HEARTBEAT_TIMEOUT triggers promote()).
            print("waiting for timeout detection")
            time.sleep(0.5)
            self.assertTrue(
                self._wait_until(lambda: backup_svc._is_promoted_primary, timeout_sec=12.0),
                "watchdog should detect primary silence after heartbeat timeout",
            )

            # 6. Assert promotion (service now acts as primary).
            print("asserting promotion")
            time.sleep(0.5)
            self.assertTrue(backup_svc._is_promoted_primary)
            print("promotion successful")
            time.sleep(0.5)
            self.assertFalse(backup_svc.back_up)
            print("replication successful")
            time.sleep(0.5)
            self.assertFalse(primary_svc.back_up)


        finally:
            # 7. Cleanup (stops sockets and watchdog even if assertions fail).
            primary_svc.stop()
            backup_svc.stop()
            monitor.stop()

if __name__ == "__main__":
    unittest.main(verbosity=1)
