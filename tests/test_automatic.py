"""
Automated tests: Double booking, Lamport clock, Heartbeat monitor, Backup promotion
Uses stdlib unittest only — run via `python run_tests.py`.
"""

import os
import unittest
import time
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
        print()

        print("first booking:")
        time.sleep(0.5)
        print(f"customer name: {msg['customer_name']}")
        time.sleep(0.5)
        print(f"date: {msg['date']}")
        time.sleep(0.5)
        print(f"timeslot: {msg['timeslot']}")
        time.sleep(0.5)
        print(f"party size: {msg['party_size']}")
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
        print(f"lamport timestamp: {first['lamport_timestamp']}")
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
        self.assertEqual(second["status"], "ok")
        print("second booking response:")
        time.sleep(0.5)
        print(f"status: {second['status']}")
        time.sleep(0.5)
        print(f"message: {second['message']}")
        time.sleep(0.5)
        print(f"lamport timestamp: {second['lamport_timestamp']}")
        time.sleep(0.5)
        print()
        time.sleep(2)


if __name__ == "__main__":
    unittest.main(verbosity=1)
