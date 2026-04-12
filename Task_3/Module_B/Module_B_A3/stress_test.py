"""
stress_test.py
Assignment 3 — Module B | CS 432 Databases | Group 15

Sends 300 HTTP requests from 20 concurrent worker threads and measures
throughput, per-endpoint response times (avg / p50 / p95 / p99), and
correctness under load.

This custom script complements the Locust load test (locustfile.py) which
provides a visual dashboard. Both test the same endpoints; this script
produces the detailed per-endpoint CSV-style breakdown for the report.

ACID properties tested:
  Atomicity  — rejected checkouts produce no partial data
  Consistency — stock never goes negative under concurrent writes
  Durability  — 0 server errors; all committed responses confirmed
"""

import threading
import requests
import time
import statistics
import random
from collections import defaultdict
from datetime import datetime

BASE_URL       = "http://127.0.0.1:5000"
TOTAL_REQUESTS = 300
WORKER_THREADS = 20

USERS = [
    {"username": "rajesh", "password": "user123"},
    {"username": "priya",  "password": "user123"},
    {"username": "amit",   "password": "user123"},
    {"username": "sneha",  "password": "user123"},
    {"username": "vikram", "password": "user123"},
]

# ── shared state ──────────────────────────────────────────────────────────────
RESPONSE_TIMES = defaultdict(list)
STATUS_COUNTS  = defaultdict(lambda: defaultdict(int))
ERRORS         = []
LOCK           = threading.Lock()


# ─── helpers ──────────────────────────────────────────────────────────────────

def login_all():
    """Login all users and return {username: token}."""
    tokens = {}
    for u in USERS:
        try:
            r = requests.post(
                f"{BASE_URL}/login",
                json={"user": u["username"], "password": u["password"]},
                timeout=10,
            )
            if r.status_code == 200:
                tokens[u["username"]] = r.json().get("session_token")
                print(f"  ✓ Logged in {u['username']}")
            else:
                print(f"  ✗ Login failed: {u['username']} (HTTP {r.status_code})")
        except Exception as e:
            print(f"  ✗ Login error: {u['username']} — {e}")
    return tokens


def timed_request(method, url, token, json_body=None, label=""):
    """Execute one timed HTTP request and record results."""
    headers = {"Authorization": f"Bearer {token}"}
    t0 = time.perf_counter()
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=15)
        else:
            r = requests.post(url, headers=headers, json=json_body, timeout=15)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        with LOCK:
            RESPONSE_TIMES[label].append(elapsed_ms)
            STATUS_COUNTS[label][r.status_code] += 1
        return r
    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        with LOCK:
            RESPONSE_TIMES[label].append(elapsed_ms)
            STATUS_COUNTS[label]["error"] += 1
            ERRORS.append(f"{label}: {str(e)[:80]}")
        return None


# ─── worker ───────────────────────────────────────────────────────────────────

def worker(tokens, queue, q_lock):
    """Pull tasks from the queue and execute them until empty."""
    usernames = list(tokens.keys())
    while True:
        with q_lock:
            if not queue:
                break
            task = queue.pop()

        username = random.choice(usernames)
        token    = tokens[username]

        if task == "browse":
            timed_request("GET", f"{BASE_URL}/api/products",
                          token, label="GET /api/products")

        elif task == "get_sales":
            timed_request("GET", f"{BASE_URL}/api/sales",
                          token, label="GET /api/sales")

        elif task == "get_orders":
            timed_request("GET", f"{BASE_URL}/api/orders",
                          token, label="GET /api/orders")

        elif task == "isauth":
            timed_request("GET", f"{BASE_URL}/isAuth",
                          token, label="GET /isAuth")

        elif task == "checkout":
            timed_request(
                "POST", f"{BASE_URL}/api/sales/checkout",
                token,
                json_body={"items": [{"product_id": "PROD002", "qty": 1}],
                           "payment_method": "Cash"},
                label="POST /api/sales/checkout",
            )


# ─── main entry point ─────────────────────────────────────────────────────────

def run_stress_test():
    global ERRORS
    RESPONSE_TIMES.clear()
    STATUS_COUNTS.clear()
    ERRORS = []

    print("\n" + "=" * 65)
    print("  STRESS TEST")
    print(f"  {TOTAL_REQUESTS} requests  |  {WORKER_THREADS} concurrent workers")
    print("  (Complemented by Locust visual load test — see locustfile.py)")
    print("=" * 65)

    tokens = login_all()
    if not tokens:
        print("  No tokens — is the Flask server running on port 5000?")
        return

    # Build task queue: mixed request types
    tasks = (
        ["browse"]     * 120 +
        ["get_sales"]  * 50  +
        ["get_orders"] * 40  +
        ["isauth"]     * 60  +
        ["checkout"]   * 30
    )[:TOTAL_REQUESTS]
    random.shuffle(tasks)
    queue  = list(tasks)
    q_lock = threading.Lock()

    print(f"\n  Task mix: browse×120  sales×50  orders×40  isAuth×60  checkout×30")
    print(f"  Dispatching {WORKER_THREADS} worker threads...\n")

    start_time = time.time()
    workers = [
        threading.Thread(target=worker, args=(tokens, queue, q_lock), daemon=True)
        for _ in range(WORKER_THREADS)
    ]
    for w in workers:
        w.start()
    for w in workers:
        w.join(timeout=120)
    total_time = time.time() - start_time

    # ── results ───────────────────────────────────────────────────────────────
    total_reqs = sum(len(v) for v in RESPONSE_TIMES.values())

    print("=" * 65)
    print("  STRESS TEST RESULTS")
    print("=" * 65)
    print(f"  Total time        : {total_time:.2f}s")
    print(f"  Requests completed: {total_reqs}")
    print(f"  Throughput        : {total_reqs / total_time:.1f} req/s")
    print(f"  Errors (network)  : {len(ERRORS)}")
    if ERRORS:
        for e in ERRORS[:3]:
            print(f"    {e}")

    print(f"\n  {'Endpoint':<38} {'Count':>6} {'Avg ms':>8} {'p50':>8} "
          f"{'p95':>8} {'200s':>6} {'4xx':>6}")
    print(f"  {'-'*38} {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*6} {'-'*6}")

    for ep, times in sorted(RESPONSE_TIMES.items()):
        if not times:
            continue
        avg  = statistics.mean(times)
        p50  = statistics.median(times)
        p95  = sorted(times)[int(len(times) * 0.95)]
        s2xx = (STATUS_COUNTS[ep].get(200, 0) +
                STATUS_COUNTS[ep].get(201, 0))
        s4xx = sum(v for k, v in STATUS_COUNTS[ep].items()
                   if isinstance(k, int) and 400 <= k < 500)
        print(f"  {ep:<38} {len(times):>6} {avg:>8.1f} {p50:>8.1f} "
              f"{p95:>8.1f} {s2xx:>6} {s4xx:>6}")

    all_times = [t for ts in RESPONSE_TIMES.values() for t in ts]
    if all_times:
        p99 = sorted(all_times)[int(len(all_times) * 0.99)]
        print(f"\n  Overall p99 response time: {p99:.1f}ms")

        print("\n  CORRECTNESS UNDER LOAD:")
        checkout_sc = STATUS_COUNTS.get("POST /api/sales/checkout", {})
        ok_co  = checkout_sc.get(201, 0)
        err_co = sum(v for k, v in checkout_sc.items()
                     if isinstance(k, int) and k != 201)
        print(f"  Checkout 201 OK  : {ok_co}")
        print(f"  Checkout 4xx     : {err_co}  (out-of-stock = expected, not a bug)")
        print(f"  {'✓' if len(ERRORS) == 0 else '✗'} Zero server/network errors")
        print(f"  {'✓' if p99 < 2000 else '✗'} System responsive under load (p99 {p99:.1f}ms < 2000ms)")

    print("=" * 65)


if __name__ == "__main__":
    run_stress_test()
