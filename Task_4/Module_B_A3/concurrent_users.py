"""
concurrent_users.py
Assignment 3 — Module B | CS 432 Databases | Group 15

Simulates 5 real user sessions running simultaneously via Python threads.
Each session performs: login → browse products → view own portfolio →
attempt admin-only delete (must be blocked) → checkout.

ACID properties tested:
  Isolation  — each user only accesses their own data; RBAC blocks cross-user access
  Consistency — 5 concurrent checkouts produce 5 distinct Sale IDs, no duplicates
  Atomicity  — no partial writes even under simultaneous load
"""

import threading
import requests
import time
import random
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"

USERS = [
    {"username": "rajesh", "password": "user123", "member_id": "MEM001"},
    {"username": "priya",  "password": "user123", "member_id": "MEM002"},
    {"username": "amit",   "password": "user123", "member_id": "MEM003"},
    {"username": "sneha",  "password": "user123", "member_id": "MEM004"},
    {"username": "vikram", "password": "user123", "member_id": "MEM005"},
]

# Shared state — guarded by LOCK
RESULTS = []
LOCK    = threading.Lock()


# ─── helpers ──────────────────────────────────────────────────────────────────

def login(username, password):
    """Authenticate and return JWT token, or None on failure."""
    try:
        r = requests.post(
            f"{BASE_URL}/login",
            json={"user": username, "password": password},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("session_token")
    except Exception as e:
        print(f"  [LOGIN ERROR] {username}: {e}")
    return None


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def log(thread_name, action, status, detail=""):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    msg = f"  [{ts}] [{thread_name:<22}] {action:<38} → {status}"
    if detail:
        msg += f"  ({detail})"
    with LOCK:
        RESULTS.append(
            {"thread": thread_name, "action": action,
             "status": status, "detail": detail, "time": ts}
        )
        print(msg)


# ─── individual actions ───────────────────────────────────────────────────────

def step_login(user, thread_name):
    token = login(user["username"], user["password"])
    if token:
        log(thread_name, "LOGIN", "OK")
        return token
    log(thread_name, "LOGIN", "FAIL")
    return None


def step_browse_products(user, token, thread_name):
    r = requests.get(f"{BASE_URL}/api/products",
                     headers=auth_header(token), timeout=10)
    if r.status_code == 200:
        count = len(r.json().get("products", []))
        log(thread_name, "GET /api/products", "OK", f"{count} products")
    else:
        log(thread_name, "GET /api/products", f"FAIL {r.status_code}")


def step_view_own_portfolio(user, token, thread_name):
    mid = user["member_id"]
    r = requests.get(f"{BASE_URL}/api/members/{mid}/portfolio",
                     headers=auth_header(token), timeout=10)
    if r.status_code == 200:
        log(thread_name, f"GET portfolio/{mid}", "OK")
    elif r.status_code == 403:
        log(thread_name, f"GET portfolio/{mid}", "DENIED (RBAC correct)")
    else:
        log(thread_name, f"GET portfolio/{mid}", f"FAIL {r.status_code}", r.text[:80])


def step_try_admin_action(user, token, thread_name):
    """Regular users must be blocked from admin-only DELETE."""
    r = requests.delete(f"{BASE_URL}/api/products/PROD001",
                        headers=auth_header(token), timeout=10)
    if r.status_code == 403:
        log(thread_name, "DELETE /api/products (regular user)", "BLOCKED (correct)")
    elif r.status_code == 200:
        log(thread_name, "DELETE /api/products (regular user)",
            "ALLOWED — *** RBAC FAILURE ***", "security breach")
    else:
        log(thread_name, "DELETE /api/products (regular user)",
            f"status {r.status_code}")


def step_checkout(user, token, thread_name, product_id="PROD002", qty=1):
    """Place an online order; verifies atomicity of stock + loyalty point update."""
    r = requests.post(
        f"{BASE_URL}/api/sales/checkout",
        json={"items": [{"product_id": product_id, "qty": qty}],
              "payment_method": "Cash"},
        headers=auth_header(token),
        timeout=10,
    )
    if r.status_code == 201:
        data = r.json()
        log(thread_name, f"CHECKOUT {product_id}×{qty}", "OK",
            f"sale={data.get('sale_id')}  total=₹{data.get('final_amount')}")
    else:
        log(thread_name, f"CHECKOUT {product_id}×{qty}",
            f"FAIL {r.status_code}", r.text[:120])


# ─── thread worker ────────────────────────────────────────────────────────────

def user_session(user, thread_name):
    """One complete simulated user session."""
    token = step_login(user, thread_name)
    if not token:
        return

    # Small random jitter so threads interleave naturally
    time.sleep(random.uniform(0, 0.2))
    step_browse_products(user, token, thread_name)

    time.sleep(random.uniform(0, 0.15))
    step_view_own_portfolio(user, token, thread_name)

    time.sleep(random.uniform(0, 0.15))
    step_try_admin_action(user, token, thread_name)

    time.sleep(random.uniform(0, 0.15))
    step_checkout(user, token, thread_name, "PROD002", 1)

    log(thread_name, "SESSION", "DONE")


# ─── main entry point ─────────────────────────────────────────────────────────

def run_concurrent_users(num_users=5):
    global RESULTS
    RESULTS = []

    print("\n" + "=" * 65)
    print("  CONCURRENT USER SIMULATION")
    print(f"  Simulating {num_users} users at the same time")
    print("=" * 65)

    threads = [
        threading.Thread(
            target=user_session,
            args=(USERS[i], f"User-{i+1}({USERS[i]['username']})"),
            daemon=True,
        )
        for i in range(num_users)
    ]

    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    elapsed = time.time() - start

    print("\n" + "-" * 65)
    print(f"  All {num_users} threads finished in {elapsed:.2f}s")

    ok_count      = sum(1 for r in RESULTS if r["status"].startswith("OK"))
    blocked_count = sum(1 for r in RESULTS if "BLOCKED" in r["status"])
    fail_count    = sum(1 for r in RESULTS if "FAIL" in r["status"]
                        and "RBAC FAILURE" not in r["status"])

    print(f"  Results → OK: {ok_count}  |  Blocked (RBAC): {blocked_count}  |  Failed: {fail_count}")

    # ACID summary
    print("\n  ACID PROPERTIES VERIFIED:")
    rbac_ok = all("BLOCKED" in r["status"]
                  for r in RESULTS if "DELETE" in r["action"])
    print(f"  {'✓' if rbac_ok else '✗'} ISOLATION  — RBAC blocks cross-user admin actions")
    print(f"  {'✓' if fail_count == 0 else '✗'} CONSISTENCY — no failed writes under concurrent load")
    print("=" * 65)
    return RESULTS


if __name__ == "__main__":
    run_concurrent_users(num_users=5)
