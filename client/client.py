"""
client.py - Restaurant reservation client.
- Browse restaurants with full details
- Search by cuisine
- View week-ahead availability
-  table matching (assigns table based on party size + location preference)
- My reservations (search by name across all restaurants)
- Modify and cancel reservations
"""

import json
import sys
import os
import urllib.request
import urllib.error
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:5000"


# ──────────────────────────────────────────────────────────────────
#  HTTP helpers
# ──────────────────────────────────────────────────────────────────

def httpGet(path):
    try:
        resp = urllib.request.urlopen(f"{BASE_URL}{path}", timeout=10)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read().decode())
        except: return {"status": "error", "message": f"HTTP {e.code}"}
    except urllib.error.URLError as e:
        return {"status": "error", "message": f"Cannot connect: {e}"}

def httpPost(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, method="POST",
        headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read().decode())
        except: return {"status": "error", "message": f"HTTP {e.code}"}
    except urllib.error.URLError as e:
        return {"status": "error", "message": f"Cannot connect: {e}"}

def httpDelete(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, method="DELETE",
        headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read().decode())
        except: return {"status": "error", "message": f"HTTP {e.code}"}
    except urllib.error.URLError as e:
        return {"status": "error", "message": f"Cannot connect: {e}"}


# ──────────────────────────────────────────────────────────────────
#  Restaurant helpers
# ──────────────────────────────────────────────────────────────────

def fetchRestaurants():
    resp = httpGet("/restaurants")
    return resp.get("restaurants", [])

def pickRestaurant(restaurants):
    if not restaurants:
        print("\n  No restaurants found.")
        return None
    print()
    for i, r in enumerate(restaurants, 1):
        price = r.get("price_range", "")
        cuisine = r.get("cuisine", "")
        rating = r.get("rating", 0)
        line = f"    {i}. {r['name']}"
        details = []
        if cuisine: details.append(cuisine)
        if price: details.append(price)
        if rating: details.append(f"{rating}/5")
        if details:
            line += f"  ({', '.join(details)})"
        print(line)
    print(f"    0. Cancel")
    choice = input("\n  Pick a restaurant: ").strip()
    if choice == "0": return None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(restaurants): return restaurants[idx]["restaurant_id"]
    except ValueError: pass
    print("  Invalid choice.")
    return None

def getRestaurant(restaurants, rid):
    for r in restaurants:
        if r["restaurant_id"] == rid: return r
    return None

def getName(restaurants, rid):
    r = getRestaurant(restaurants, rid)
    return r["name"] if r else rid

#to allow reservations within 7 days
def getNextWeekDates():
    """Return list of date strings for today + next 6 days."""
    today = datetime.now()
    dates = []
    for i in range(7):
        d = today + timedelta(days=i)
        dates.append(d.strftime("%Y-%m-%d"))
    return dates

def pickDate():
    """Show next 7 days, let user pick."""
    dates = getNextWeekDates()
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    print("\n  Available dates:")
    for i, d in enumerate(dates, 1):
        dt = datetime.strptime(d, "%Y-%m-%d")
        day_name = days[dt.weekday()]
        label = "Today" if i == 1 else ("Tomorrow" if i == 2 else day_name)
        print(f"    {i}. {d} ({label})")
    print(f"    0. Cancel")
    choice = input("\n  Pick a date: ").strip()
    if choice == "0": return None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(dates): return dates[idx]
    except ValueError: pass
    print("  Invalid choice.")
    return None

def pickTimeslot(timeslots):
    """Show available timeslots in columns, let user pick."""
    print("\n  Available times:")
    # Show in rows of 4
    for i in range(0, len(timeslots), 4):
        row = ""
        for j in range(4):
            if i + j < len(timeslots):
                num = i + j + 1
                row += f"    {num:2d}. {timeslots[i+j]}"
        print(row)
    print(f"     0. Cancel")
    choice = input("\n  Pick a time: ").strip()
    if choice == "0": return None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(timeslots): return timeslots[idx]
    except ValueError: pass
    print("  Invalid choice.")
    return None

# automatically matches reservation party number to smallest table for people based on preference too
def matchTable(available_tables, party_size, preference=None):
    if not available_tables:
        return None
    # Sort by capacity (smallest first that fits the party)
    candidates = sorted(available_tables, key=lambda t: t["capacity"])
    if preference:
        # Try to match preference first
        preferred = [t for t in candidates if t["location"].lower() == preference.lower()]
        if preferred:
            return preferred[0]
    # No preference or no match — return smallest available
    return candidates[0]


# ──────────────────────────────────────────────────────────────────
#  1. Browse restaurants
# ──────────────────────────────────────────────────────────────────

def browseRestaurants():
    print(f"\n  {'─'*55}")
    print(f"  Browse Restaurants")
    print(f"  {'─'*55}")
    restaurants = fetchRestaurants()
    if not restaurants:
        print("  Could not load restaurants.")
        return
    for r in restaurants:
        print(f"\n  {r['name']}")
        desc = r.get("description", "")
        if desc: print(f"  {desc}")
        print()
        cuisine = r.get("cuisine", "")
        price = r.get("price_range", "")
        rating = r.get("rating", 0)
        address = r.get("address", "")
        menu_url = r.get("menu_url", "")
        features = r.get("features", [])
        if cuisine:    print(f"    {'Cuisine:':<12s} {cuisine}")
        if price:      print(f"    {'Price:':<12s} {price}")
        if rating:     print(f"    {'Rating:':<12s} {rating}/5")
        if address:    print(f"    {'Address:':<12s} {address}")
        if menu_url:   print(f"    {'Menu:':<12s} {menu_url}")
        if features:   print(f"    {'Features:':<12s} {', '.join(features)}")
        # Table layout
        locations = {}
        for tid, info in r["tables"].items():
            loc = info["location"]
            if loc not in locations: locations[loc] = []
            locations[loc].append(info["capacity"])
        layout_parts = []
        for loc, caps in sorted(locations.items()):
            layout_parts.append(f"{loc} ({', '.join(str(c) for c in sorted(caps))} seat)")
        print(f"    {'Seating:':<12s} {len(r['tables'])} tables")
        for part in layout_parts:
            print(f"    {'':12s} {part}")
        print(f"    {'Hours:':<12s} {r['timeslots'][0]} - {r['timeslots'][-1]}")


# ──────────────────────────────────────────────────────────────────
#  2. Search by cuisine
# ──────────────────────────────────────────────────────────────────

def searchByCuisine():
    print(f"\n  {'─'*55}")
    print(f"  Search by Cuisine")
    print(f"  {'─'*55}")
    restaurants = fetchRestaurants()
    if not restaurants:
        print("  Could not load restaurants.")
        return
    cuisines = sorted(set(r.get("cuisine", "") for r in restaurants if r.get("cuisine")))
    if not cuisines:
        print("\n  No cuisine data available.")
        return
    print()
    for i, c in enumerate(cuisines, 1):
        count = sum(1 for r in restaurants if r.get("cuisine") == c)
        print(f"    {i}. {c} ({count} restaurant{'s' if count > 1 else ''})")
    print(f"    0. Cancel")
    choice = input("\n  Pick a cuisine: ").strip()
    if choice == "0": return
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(cuisines): print("  Invalid choice."); return
        selected = cuisines[idx]
    except ValueError: print("  Invalid choice."); return

    matches = [r for r in restaurants if r.get("cuisine") == selected]
    print(f"\n  {selected} restaurants:\n")
    for r in matches:
        price = r.get("price_range", "")
        rating = r.get("rating", 0)
        address = r.get("address", "")
        desc = r.get("description", "")
        features = r.get("features", [])
        header = r["name"]
        if price: header += f"  {price}"
        if rating: header += f"  {rating}/5"
        print(f"    {header}")
        if desc:     print(f"      {desc}")
        if address:  print(f"      {'Address:':<11s} {address}")
        if features: print(f"      {'Features:':<11s} {', '.join(features)}")
        print(f"      {'Tables:':<11s} {len(r['tables'])}  |  Hours: {r['timeslots'][0]} - {r['timeslots'][-1]}")
        print()


# ──────────────────────────────────────────────────────────────────
#  3. Make a reservation (smart table matching)
# ──────────────────────────────────────────────────────────────────

def makeReservation():
    print(f"\n  {'─'*55}")
    print(f"  Make a Reservation")
    print(f"  {'─'*55}")
    restaurants = fetchRestaurants()
    rid = pickRestaurant(restaurants)
    if not rid: return

    rest = getRestaurant(restaurants, rid)
    name = rest["name"]
    print(f"\n  Booking at {name}")

    # Pick date from next 7 days
    date = pickDate()
    if not date: return

    # Pick timeslot from restaurant's list
    timeslot = pickTimeslot(rest["timeslots"])
    if not timeslot: return

    party_size = input("\n  Party size: ").strip()
    if not party_size:
        print("  Party size is required.")
        return
    try:
        party_size = int(party_size)
    except ValueError:
        print("  Invalid party size.")
        return

    # Get available tables
    resp = httpGet(f"/restaurants/{rid}/availability?date={date}&timeslot={timeslot}&party_size={party_size}")
    if resp.get("status") != "ok":
        print(f"  Error: {resp.get('message')}")
        return

    tables = resp.get("available_tables", [])
    if not tables:
        print(f"\n  No tables available at {name} for {party_size} guests at {timeslot} on {date}.")
        return

    # Get location preference
    locations = sorted(set(t["location"] for t in tables))
    print(f"\n  Available seating areas: {', '.join(locations)}")
    preference = input("  Seating preference (or Enter for best match): ").strip()

    # Smart table matching
    best = matchTable(tables, party_size, preference if preference else None)

    if preference and best["location"].lower() != preference.lower():
        print(f"\n  No {preference} tables available.")
        print(f"  Best match: [{best['table_id']}] {best['capacity']}-seat, {best['location']}")
        ok = input("  Accept this table? (y/n): ").strip().lower()
        if ok != "y":
            print("\n  Other available options:")
            for i, t in enumerate(tables, 1):
                marker = " <-- best match" if t["table_id"] == best["table_id"] else ""
                print(f"    {i}. [{t['table_id']}] {t['capacity']}-seat, {t['location']}{marker}")
            tc = input("\n  Pick a table (number, or 0 to cancel): ").strip()
            if tc == "0": return
            try:
                idx = int(tc) - 1
                if 0 <= idx < len(tables): best = tables[idx]
                else: print("  Invalid."); return
            except ValueError: print("  Invalid."); return
    else:
        print(f"\n  Assigned: [{best['table_id']}] {best['capacity']}-seat, {best['location']}")

    customer = input("\n  Your name: ").strip()
    if not customer:
        print("  Name is required.")
        return
    contact = input("  Contact (phone/email): ").strip()

    resp = httpPost("/reservations", {
        "restaurant_id": rid, "table_id": best["table_id"],
        "date": date, "timeslot": timeslot,
        "customer_name": customer, "party_size": party_size, "contact": contact,
    })
    if resp.get("status") == "ok":
        res = resp.get("reservation", {})
        print(f"\n  {'='*45}")
        print(f"  RESERVATION CONFIRMED")
        print(f"  {'='*45}")
        print(f"  {'Restaurant:':<14s} {name}")
        print(f"  {'Table:':<14s} {res.get('table_id')} ({best['capacity']}-seat, {best['location']})")
        print(f"  {'Date:':<14s} {res.get('date')}")
        print(f"  {'Time:':<14s} {res.get('timeslot')}")
        print(f"  {'Name:':<14s} {res.get('customer_name')}")
        print(f"  {'Party size:':<14s} {res.get('party_size')}")
        print(f"  {'Contact:':<14s} {res.get('contact', 'N/A')}")
        print(f"  {'='*45}")
    else:
        print(f"\n  Booking failed: {resp.get('message')}")


# ──────────────────────────────────────────────────────────────────
#  4. My reservations
# ──────────────────────────────────────────────────────────────────

def viewMyReservations():
    print(f"\n  {'─'*55}")
    print(f"  My Reservations")
    print(f"  {'─'*55}")
    customer = input("  Your name: ").strip().lower()
    if not customer:
        print("  Name is required.")
        return
    restaurants = fetchRestaurants()
    if not restaurants: print("  Could not load restaurants."); return
    all_res = []
    for r in restaurants:
        resp = httpGet(f"/reservations/{r['restaurant_id']}")
        if resp.get("status") == "ok":
            for res in resp.get("reservations", []):
                if res.get("customer_name", "").lower() == customer:
                    res["_restaurant_name"] = r["name"]
                    res["_address"] = r.get("address", "")
                    all_res.append(res)
    if all_res:
        # Sort by date then timeslot
        all_res.sort(key=lambda r: (r.get("date", ""), r.get("timeslot", "")))
        print(f"\n  Found {len(all_res)} reservation(s):\n")
        for i, r in enumerate(all_res, 1):
            print(f"    {i}. {r['_restaurant_name']}")
            print(f"       {'Date:':<10s} {r['date']} at {r['timeslot']}")
            print(f"       {'Table:':<10s} {r['table_id']} (party of {r['party_size']})")
            if r.get("_address"):
                print(f"       {'Address:':<10s} {r['_address']}")
            print()
    else:
        print(f"\n  No reservations found for '{customer}'.")


# ──────────────────────────────────────────────────────────────────
#  5. Modify a reservation
# ──────────────────────────────────────────────────────────────────

def modifyReservation():
    print(f"\n  {'─'*55}")
    print(f"  Modify Reservation")
    print(f"  {'─'*55}")
    restaurants = fetchRestaurants()
    rid = pickRestaurant(restaurants)
    if not rid: return
    rest = getRestaurant(restaurants, rid)
    name = rest["name"]

    # Show existing reservations to pick from
    resp = httpGet(f"/reservations/{rid}")
    if resp.get("status") != "ok" or not resp.get("reservations"):
        print(f"\n  No reservations at {name}.")
        return
    reservations = resp["reservations"]
    print(f"\n  Reservations at {name}:")
    for i, r in enumerate(reservations, 1):
        print(f"    {i}. [{r['table_id']}] {r['date']} {r['timeslot']} - {r['customer_name']} (party of {r['party_size']})")
    print(f"    0. Cancel")
    choice = input("\n  Which to modify: ").strip()
    if choice == "0": return
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(reservations): print("  Invalid."); return
        existing = reservations[idx]
    except ValueError: print("  Invalid."); return

    old_table = existing["table_id"]
    old_date = existing["date"]
    old_timeslot = existing["timeslot"]

    print(f"\n  Current: {old_date} at {old_timeslot}, table {old_table}, party of {existing['party_size']}")
    print(f"  Press Enter to keep current value.\n")

    new_date = input(f"  New date [{old_date}]: ").strip() or old_date
    new_timeslot = input(f"  New timeslot [{old_timeslot}]: ").strip() or old_timeslot
    new_party = input(f"  New party size [{existing['party_size']}]: ").strip()
    try:
        new_party = int(new_party) if new_party else existing["party_size"]
    except ValueError:
        print("  Invalid party size.")
        return

    # Cancel old booking first
    cancel_resp = httpDelete("/reservations", {
        "restaurant_id": rid, "table_id": old_table,
        "date": old_date, "timeslot": old_timeslot,
    })
    if cancel_resp.get("status") != "ok":
        print(f"\n  Could not cancel existing reservation: {cancel_resp.get('message')}")
        return

    # Find best table at new time
    avail = httpGet(f"/restaurants/{rid}/availability?date={new_date}&timeslot={new_timeslot}&party_size={new_party}")
    tables = avail.get("available_tables", [])
    if not tables:
        # No tables at new time — restore original
        print(f"\n  No tables available at new time. Restoring original reservation...")
        httpPost("/reservations", {
            "restaurant_id": rid, "table_id": old_table,
            "date": old_date, "timeslot": old_timeslot,
            "customer_name": existing["customer_name"],
            "party_size": existing["party_size"], "contact": existing.get("contact", ""),
        })
        print(f"  Original reservation restored.")
        return

    best = matchTable(tables, new_party)
    print(f"\n  Assigned: [{best['table_id']}] {best['capacity']}-seat, {best['location']}")

    book_resp = httpPost("/reservations", {
        "restaurant_id": rid, "table_id": best["table_id"],
        "date": new_date, "timeslot": new_timeslot,
        "customer_name": existing["customer_name"],
        "party_size": new_party, "contact": existing.get("contact", ""),
    })
    if book_resp.get("status") == "ok":
        res = book_resp.get("reservation", {})
        print(f"\n  {'='*45}")
        print(f"  RESERVATION MODIFIED")
        print(f"  {'='*45}")
        print(f"  {'Restaurant:':<14s} {name}")
        print(f"  {'Table:':<14s} {res.get('table_id')}")
        print(f"  {'Date:':<14s} {res.get('date')}")
        print(f"  {'Time:':<14s} {res.get('timeslot')}")
        print(f"  {'Party:':<14s} {res.get('party_size')}")
        print(f"  {'='*45}")
    else:
        # New booking failed — restore original
        print(f"\n  Modification failed. Restoring original reservation...")
        httpPost("/reservations", {
            "restaurant_id": rid, "table_id": old_table,
            "date": old_date, "timeslot": old_timeslot,
            "customer_name": existing["customer_name"],
            "party_size": existing["party_size"], "contact": existing.get("contact", ""),
        })
        print(f"  Original reservation restored.")


# ──────────────────────────────────────────────────────────────────
#  6. Cancel a reservation
# ──────────────────────────────────────────────────────────────────

def cancelReservation():
    print(f"\n  {'─'*55}")
    print(f"  Cancel Reservation")
    print(f"  {'─'*55}")
    restaurants = fetchRestaurants()
    rid = pickRestaurant(restaurants)
    if not rid: return
    name = getName(restaurants, rid)

    resp = httpGet(f"/reservations/{rid}")
    if resp.get("status") != "ok" or not resp.get("reservations"):
        print(f"\n  No reservations at {name}.")
        return
    reservations = resp["reservations"]
    print(f"\n  Reservations at {name}:")
    for i, r in enumerate(reservations, 1):
        print(f"    {i}. [{r['table_id']}] {r['date']} {r['timeslot']} - {r['customer_name']} (party of {r['party_size']})")
    print(f"    0. Go back")
    choice = input("\n  Which to cancel: ").strip()
    if choice == "0": return
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(reservations): print("  Invalid."); return
        r = reservations[idx]
    except ValueError: print("  Invalid."); return

    confirm = input(f"\n  Cancel {r['customer_name']}'s reservation at {r['timeslot']} on {r['date']}? (y/n): ").strip().lower()
    if confirm != "y": print("  Kept reservation."); return

    resp = httpDelete("/reservations", {
        "restaurant_id": rid, "table_id": r["table_id"],
        "date": r["date"], "timeslot": r["timeslot"],
    })
    if resp.get("status") == "ok":
        print(f"\n  Reservation cancelled.")
    else:
        print(f"\n  Failed: {resp.get('message')}")


# ──────────────────────────────────────────────────────────────────
#  Main menu
# ──────────────────────────────────────────────────────────────────

def main():
    print()
    print("  ================================================")
    print("  Restaurant Reservation System")
    print("  ================================================")

    while True:
        print("\n  MENU:")
        print("    1. Browse restaurants")
        print("    2. Search by cuisine")
        print("    3. Make a reservation")
        print("    4. My reservations")
        print("    5. Modify a reservation")
        print("    6. Cancel a reservation")
        print("    0. Exit")

        choice = input("\n  Choice: ").strip()

        if choice == "1": browseRestaurants()
        elif choice == "2": searchByCuisine()
        elif choice == "3": makeReservation()
        elif choice == "4": viewMyReservations()
        elif choice == "5": modifyReservation()
        elif choice == "6": cancelReservation()
        elif choice == "0": print("\n  Goodbye!\n"); break
        else: print("  Invalid choice.")


if __name__ == "__main__":
    main()