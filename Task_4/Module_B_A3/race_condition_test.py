"""
race_condition_test.py
Assignment 3 — Module B | CS 432 Databases | Group 15

Race condition test: 8 threads compete to buy the same low-stock product
simultaneously, released via threading.Event so all requests fire at the
exact same instant.

ACID properties tested:
  Atomicity  — failed orders leave zero partial data
  Consistency — stock never goes negative; sold units == successful orders
  Isolation  — concurrent threads do not corrupt shared stock state
"""

import threading
import requests
import time
import pymysql
from datetime import datetime

BASE_URL     = "http://127.0.0.1:5000"
MYSQL_HOST   = "localhost"
MYSQL_USER   = "root"
MYSQL_PASS   = "password"   # ← update to your MySQL root password
MYSQL_DB     = "ShopStop"

TEST_PRODUCT  = "PROD003"   # product we race over
RACE_THREADS  = 8           # more threads than available stock
STOCK_TO_SET  = 3           # intentionally low: only 3 units available

RESULTS = []
LOCK    = threading.Lock()

USERS = [
    {"username": "rajesh", "password": "user123"},
    {"username": "priya",  "password": "user123"},
    {"username": "amit",   "password": "user123"},
    {"username": "sneha",  "password": "user123"},
    {"username": "vikram", "password": "user123"},
    {"username": "rajesh", "password": "user123"},
    {"username": "priya",  "password": "user123"},
    {"username": "amit",   "password": "user123"},
]


# ─── helpers ──────────────────────────────────────────────────────────────────

def get_db():
    return pymysql.connect(
        host=MYSQL_HOST, user=MYSQL_USER,
        password=MYSQL_PASS, database=MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor, autocommit=True,
    )


def set_stock(product_id, qty):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("UPDATE Product SET StockQuantity=%s WHERE ProductID=%s",
                    (qty, product_id))
    db.close()
    print(f"  [SETUP] {product_id} stock → {qty}")


def get_stock(product_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT StockQuantity FROM Product WHERE ProductID=%s",
                    (product_id,))
        row = cur.fetchone()
    db.close()
    return row["StockQuantity"] if row else -1


def login(username, password):
    try:
        r = requests.post(
            f"{BASE_URL}/login",
            json={"user": username, "password": password},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("session_token")
    except Exception:
        pass
    return None


def log_result(thread_name, status, detail=""):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    sym = "✓" if status == "SUCCESS" else "✗"
    with LOCK:
        RESULTS.append({"thread": thread_name, "status": status, "detail": detail})
        print(f"  [{ts}] [{thread_name:<22}] {sym} {status:<12}  {detail}")


# ─── racer ────────────────────────────────────────────────────────────────────

def race_buy(user_index, user, start_event):
    """Login first, then wait at the barrier, then fire simultaneously."""
    token = login(user["username"], user["password"])
    if not token:
        log_result(f"T{user_index}({user['username']})", "LOGIN_FAIL")
        return

    # All threads block here until start_event.set() releases them together
    start_event.wait()

    r = requests.post(
        f"{BASE_URL}/api/sales/checkout",
        json={"items": [{"product_id": TEST_PRODUCT, "qty": 1}],
              "payment_method": "Cash"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )

    if r.status_code == 201:
        log_result(f"T{user_index}({user['username']})", "SUCCESS",
                   f"sale={r.json().get('sale_id', '?')}")
    elif r.status_code == 400:
        reason = r.json().get("error", "unknown")[:80]
        log_result(f"T{user_index}({user['username']})", "REJECTED",
                   f"reason: {reason}")
    else:
        log_result(f"T{user_index}({user['username']})", f"HTTP_{r.status_code}",
                   r.text[:80])


# ─── main entry point ─────────────────────────────────────────────────────────

def run_race_condition_test():
    global RESULTS
    RESULTS = []

    print("\n" + "=" * 65)
    print("  RACE CONDITION TEST")
    print(f"  Product: {TEST_PRODUCT}  |  Stock: {STOCK_TO_SET}  "
          f"|  Threads racing: {RACE_THREADS}")
    print("=" * 65)

    # Set a known low stock value
    set_stock(TEST_PRODUCT, STOCK_TO_SET)
    initial_stock = get_stock(TEST_PRODUCT)
    print(f"  [VERIFY] Stock before race: {initial_stock}\n")

    # Phase 1 — all threads login (sequential, before the race)
    start_event = threading.Event()
    threads = []
    for i, user in enumerate(USERS[:RACE_THREADS]):
        t = threading.Thread(
            target=race_buy,
            args=(i + 1, user, start_event),
            daemon=True,
        )
        threads.append(t)
        t.start()

    # Give threads time to finish login and reach start_event.wait()
    time.sleep(1.5)

    print(f"  >>> RELEASING ALL {RACE_THREADS} THREADS SIMULTANEOUSLY <<<\n")
    start_event.set()   # ← all threads fire at exactly the same moment

    for t in threads:
        t.join(timeout=20)

    # ── analysis ──────────────────────────────────────────────────────────────
    final_stock = get_stock(TEST_PRODUCT)
    successes   = [r for r in RESULTS if r["status"] == "SUCCESS"]
    rejections  = [r for r in RESULTS if r["status"] == "REJECTED"]
    stock_sold  = initial_stock - final_stock

    print("\n" + "-" * 65)
    print(f"  Stock before : {initial_stock}")
    print(f"  Stock after  : {final_stock}")
    print(f"  Successful   : {len(successes)}")
    print(f"  Rejected     : {len(rejections)}")

    # ── correctness checks ────────────────────────────────────────────────────
    print("\n  CORRECTNESS CHECKS:")

    if final_stock >= 0:
        print(f"  ✓ ATOMICITY   : Stock never went negative (final={final_stock})")
    else:
        print(f"  ✗ ATOMICITY VIOLATION: Stock is negative! (final={final_stock})")

    if stock_sold == len(successes):
        print(f"  ✓ CONSISTENCY : Stock sold ({stock_sold}) == orders succeeded ({len(successes)})")
    else:
        print(f"  ✗ CONSISTENCY VIOLATION: sold={stock_sold} but successes={len(successes)}")

    if len(successes) <= STOCK_TO_SET:
        print(f"  ✓ ISOLATION   : Only {len(successes)}/{STOCK_TO_SET} orders succeeded — no overselling")
    else:
        print(f"  ✗ ISOLATION VIOLATION: {len(successes)} succeeded but stock was only {STOCK_TO_SET}!")

    print("=" * 65)
    return {
        "initial_stock": initial_stock,
        "final_stock": final_stock,
        "successes": len(successes),
        "rejections": len(rejections),
    }


if __name__ == "__main__":
    run_race_condition_test()
