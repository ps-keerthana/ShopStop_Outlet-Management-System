"""
test_sharding.py  –  Verify your sharding implementation
CS 432 Assignment 4 | Group: Nexus

Run this AFTER:
  1. shard_setup.sql has been run on all 3 shards
  2. migrate_to_shards.py has completed successfully
  3. python run.py is running (or adjust BASE_URL)

Usage:
    python test_sharding.py
"""

import requests
import json
import hashlib

BASE_URL = "http://localhost:5000"
ADMIN_TOKEN = None  # will be set after login

# ── helpers ──────────────────────────────────────────────────────────

def shard_of(member_id):
    """Python side: compute expected shard for a MemberID."""
    if member_id is None:
        return 0
    digest = hashlib.md5(member_id.encode()).hexdigest()[:8]
    return int(digest, 16) % 3


def to_iso_date(value):
    """
    Convert a SaleDate value from the API response to a plain YYYY-MM-DD string.
    Handles two formats Flask may return:
      - ISO:     "2026-02-10 18:45:00"  → "2026-02-10"
      - RFC2822: "Tue, 10 Feb 2026 18:45:00 GMT" → "2026-02-10"
    """
    s = str(value).strip()
    if not s:
        return ""
    # ISO format: starts with a digit
    if s[0].isdigit():
        return s[:10]
    # RFC 2822 format: "Tue, 10 Feb 2026 18:45:00 GMT"
    try:
        from email.utils import parsedate
        t = parsedate(s)
        if t:
            return f"{t[0]:04d}-{t[1]:02d}-{t[2]:02d}"
    except Exception:
        pass
    return s[:10]

def login():
    global ADMIN_TOKEN
    # Your app's login route is /login (not /api/auth/login)
    # and uses field "user" (not "username"), returns "session_token"
    r = requests.post(f"{BASE_URL}/login",
                      json={"user": "admin", "password": "admin123"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    ADMIN_TOKEN = r.json()["session_token"]
    print("✓ Login successful")

def headers():
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}

def ok(label, condition, detail=""):
    icon = "✓" if condition else "✗"
    print(f"  {icon} {label}" + (f"  [{detail}]" if detail else ""))
    return condition

# ── tests ─────────────────────────────────────────────────────────────

def test_routing_logic():
    print("\n── Test 1: Routing Logic ────────────────────────────────")
    members = ["MEM001", "MEM002", "MEM003", "MEM010", "MEM015", "MEM020"]
    for mid in members:
        r = requests.get(f"{BASE_URL}/api/shards/route?member_id={mid}")
        assert r.status_code == 200
        data = r.json()
        expected = shard_of(mid)
        ok(f"{mid} → shard {data['shard_id']} (port {data['shard_port']})",
           data["shard_id"] == expected,
           f"expected shard {expected}")


def test_single_shard_lookup():
    print("\n── Test 2: Single-Shard Lookup ──────────────────────────")
    # GET /api/members/MEM001 should hit exactly one shard
    r = requests.get(f"{BASE_URL}/api/members/MEM001", headers=headers())
    if r.status_code == 200:
        data = r.json()
        ok(f"MEM001 found on shard {data.get('_shard_id')}",
           data.get("_shard_id") == shard_of("MEM001"))
    else:
        print(f"  ✗ GET /api/members/MEM001 failed: {r.status_code}")


def test_insert_routing():
    print("\n── Test 3: Insert Routes to Correct Shard ───────────────")
    new_member = {
        "MemberID":        "MEMTEST",
        "Name":            "Test User",
        "Age":             25,
        "Email":           "test.shard@shopstop.com",
        "ContactNumber":   "9999999999",
        "Address":         "Test Address, Gandhinagar",
        "MembershipType":  "Silver",
        "RegistrationDate":"2026-04-13",
    }
    expected_shard = shard_of("MEMTEST")

    r = requests.post(f"{BASE_URL}/api/members", json=new_member, headers=headers())
    if r.status_code == 201:
        data = r.json()
        ok(f"Insert returned shard_id = {data.get('shard_id')}",
           data.get("shard_id") == expected_shard,
           f"expected {expected_shard}")
    else:
        print(f"  Note: {r.status_code} {r.text[:80]}")

    # Verify it exists on the right shard
    r2 = requests.get(f"{BASE_URL}/api/shards/verify/MEMTEST", headers=headers())
    if r2.status_code == 200:
        v = r2.json()
        ok("No duplication (member on exactly 1 shard)",  v["no_duplication"])
        ok("Correct shard assignment",                     v["is_correct"])

    # Cleanup
    requests.delete(f"{BASE_URL}/api/members/MEMTEST", headers=headers())


def test_range_query():
    print("\n── Test 4: Range Query (All Shards) ─────────────────────")
    # Use a wide range that covers all existing data
    from_date = "2020-01-01"
    to_date   = "2030-12-31"
    r = requests.get(
        f"{BASE_URL}/api/sales/range",
        params={"from": from_date, "to": to_date},
        headers=headers()
    )
    if r.status_code == 200:
        data = r.json()
        print(f"  Total sales across all shards: {data['total']}")
        for shard, cnt in data.get("shard_counts", {}).items():
            print(f"    {shard}: {cnt} sales")
        ok("Results returned from multiple shards",
           len(data.get("shard_counts", {})) == 3)

        sales = data.get("sales", [])

        # Verify merged results are sorted by SaleDate
        # Uses to_iso_date() to handle both ISO and RFC-2822 formats
        if len(sales) > 1:
            dates = [to_iso_date(s.get("SaleDate", "")) for s in sales]
            is_sorted = all(dates[i] <= dates[i+1] for i in range(len(dates)-1))
            ok("Merged results are sorted by SaleDate", is_sorted)
            if not is_sorted:
                for i in range(len(dates)-1):
                    if dates[i] > dates[i+1]:
                        print(f"    Out of order: {dates[i]} > {dates[i+1]}")
                        break

        # Verify every returned sale falls within the queried date range
        out_of_range = []
        for s in sales:
            d = to_iso_date(s.get("SaleDate", ""))
            if not (from_date <= d <= to_date):
                out_of_range.append(d)
        ok("All sales are within the requested date range",
           len(out_of_range) == 0)
        if out_of_range:
            print(f"    Out-of-range dates found: {out_of_range[:3]}")
    else:
        print(f"  ✗ Range query failed: {r.status_code}")

def test_distribution():
    print("\n── Test 5: Data Distribution ────────────────────────────")
    r = requests.get(f"{BASE_URL}/api/shards/distribution", headers=headers())
    if r.status_code == 200:
        data = r.json()
        total = data["summary"]["total_members_across_shards"]
        print(f"  Total members across all shards: {total}")
        for sid in range(3):
            key = f"shard_{sid}"
            if key in data and "member_count" in data[key]:
                cnt = data[key]["member_count"]
                pct = (cnt / total * 100) if total > 0 else 0
                print(f"    Shard {sid} (port {data[key]['port']}): "
                      f"{cnt} members ({pct:.1f}%)")
        ok("All 3 shards have data", all(
            data.get(f"shard_{i}", {}).get("member_count", 0) > 0
            for i in range(3)
        ))
    else:
        print(f"  ✗ Distribution check failed: {r.status_code}")


def test_no_duplication():
    print("\n── Test 6: No Duplication ───────────────────────────────")
    check_members = ["MEM001", "MEM005", "MEM010", "MEM015", "MEM020"]
    all_ok = True
    for mid in check_members:
        r = requests.get(f"{BASE_URL}/api/shards/verify/{mid}", headers=headers())
        if r.status_code == 200:
            v = r.json()
            if not ok(f"{mid}: found on exactly 1 shard", v["no_duplication"]):
                all_ok = False
    if all_ok:
        print("  All checked members exist on exactly one shard ✓")


# ── main ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("="*60)
    print("  ShopStop Assignment 4 – Sharding Tests")
    print("  Group: Nexus")
    print("="*60)

    try:
        login()
        test_routing_logic()
        test_single_shard_lookup()
        test_insert_routing()
        test_range_query()
        test_distribution()
        test_no_duplication()
        print("\n" + "="*60)
        print("  All tests complete!")
        print("="*60 + "\n")
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()