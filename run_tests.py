"""
Run automated tests from `tests/` with an interactive menu.

Usage:
    python run_tests.py
"""

import os
import sys
import unittest


# ----------------------------
# CONFIG: add your test classes here
# ----------------------------
from tests.test_automatic import (
    DoubleBookingTests,
    LamportClockTests,
    HeartbeatMonitorTests,
    PrimaryServerFailureTests,
    ServiceMapUpdateTests,
)


TEST_CLASSES = {
    "1": ("Double Booking Tests", DoubleBookingTests),
    "2": ("Lamport Clock Tests", LamportClockTests),
    "3": ("Heartbeat Monitor Tests", HeartbeatMonitorTests),
    "4": ("Primary Server Failure Tests", PrimaryServerFailureTests),
    "5": ("Service Map Update Tests", ServiceMapUpdateTests),
    # "3": ("Logger Tests", LoggerTests),
    "0": ("Exit", None),
}


def print_menu():
    print("\nSelect tests to run:\n")
    for key, (name, _) in TEST_CLASSES.items():
        print(f"  {key}) {name}")
    print()


def run_suite(suite):
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        buffer=False,
        failfast=False,
    )
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)
    if root not in sys.path:
        sys.path.insert(0, root)

    print("\n" + "=" * 56)
    print("Reservation system - test runner")
    print("=" * 56)

    loader = unittest.TestLoader()

    last_result = 0

    while True:
        print_menu()

        choice = input("Enter choice: ").strip().lower()

        if choice == "0":
            print("\nExiting test runner.\n")
            break

        elif choice in TEST_CLASSES:
            name, test_class = TEST_CLASSES[choice]
            print(f"\nRunning: {name}\n")
            last_result = run_suite(loader.loadTestsFromTestCase(test_class))

    return last_result

if __name__ == "__main__":
    raise SystemExit(main())