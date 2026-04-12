"""
run_all_tests.py
Assignment 3 — Module B | CS 432 Databases | Group 15

Master test runner — executes all four test modules in sequence and
finishes with the unified ACID verification summary.

USAGE:
  1. Start Flask server:   python3 ../run.py
  2. Update MYSQL_PASS below to your MySQL root password
  3. Run:                  python3 run_all_tests.py

For Locust visual load test (optional, separate):
  pip install locust
  locust -f locustfile.py --host http://127.0.0.1:5000
  Then open http://localhost:8089 in your browser.
"""

import time
import sys
import os
import pathlib
import importlib.util

# ── configuration ─────────────────────────────────────────────────────────────
MYSQL_PASS = "password"              # update to your MySQL root password
BASE_URL   = "http://127.0.0.1:5000"
# ─────────────────────────────────────────────────────────────────────────────


def patch_and_import(module_name, password, base_url):
    """Import a sibling module and inject MYSQL_PASS + BASE_URL."""
    spec = importlib.util.spec_from_file_location(
        module_name,
        pathlib.Path(__file__).parent / f"{module_name}.py",
    )
    mod = importlib.util.module_from_spec(spec)
    mod.MYSQL_PASS = password
    mod.BASE_URL   = base_url
    spec.loader.exec_module(mod)
    return mod


def divider(title, n=1, total=5):
    bar = "█" * 60
    print(f"\n{bar}")
    print(f"  {n} / {total}  {title}")
    print(f"{bar}")


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    overall_start = time.time()

    print("\n" + "=" * 65)
    print("  CS 432 — Assignment 3 | Module B | Group 15")
    print("  FULL TEST SUITE")
    print("=" * 65)
    print(f"  Flask server : {BASE_URL}")
    print(f"  Run started  : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  MySQL pass   : {'*' * len(MYSQL_PASS)}")
    print()
    print("  Tests included:")
    print("    1. Concurrent User Simulation  (5 threads, RBAC verification)")
    print("    2. Race Condition Test          (8 threads, stock=3)")
    print("    3. Failure Simulation & Rollback (5 failure modes)")
    print("    4. Stress Test                 (300 requests, 20 workers)")
    print("    5. ACID Verification           (15 named checks)")
    print()
    print("  Locust load test (visual dashboard) runs separately:")
    print("    locust -f locustfile.py --host http://127.0.0.1:5000")
    print("=" * 65)

    # ── 1. Concurrent Users ────────────────────────────────────────────────────
    divider("CONCURRENT USER SIMULATION", 1, 5)
    try:
        cu = patch_and_import("concurrent_users", MYSQL_PASS, BASE_URL)
        cu.run_concurrent_users(num_users=5)
    except Exception as e:
        print(f"  ERROR in concurrent_users: {e}")

    time.sleep(2)

    # ── 2. Race Condition ──────────────────────────────────────────────────────
    divider("RACE CONDITION TEST", 2, 5)
    try:
        rc = patch_and_import("race_condition_test", MYSQL_PASS, BASE_URL)
        rc.MYSQL_PASS = MYSQL_PASS
        rc.run_race_condition_test()
    except Exception as e:
        print(f"  ERROR in race_condition_test: {e}")

    time.sleep(2)

    # ── 3. Failure Simulation ──────────────────────────────────────────────────
    divider("FAILURE SIMULATION & ROLLBACK", 3, 5)
    try:
        fs = patch_and_import("failure_simulation", MYSQL_PASS, BASE_URL)
        fs.MYSQL_PASS = MYSQL_PASS
        fs.run_failure_simulation()
    except Exception as e:
        print(f"  ERROR in failure_simulation: {e}")

    time.sleep(2)

    # ── 4. Stress Test ─────────────────────────────────────────────────────────
    divider("STRESS TEST  (300 requests, 20 workers)", 4, 5)
    try:
        st = patch_and_import("stress_test", MYSQL_PASS, BASE_URL)
        st.run_stress_test()
    except Exception as e:
        print(f"  ERROR in stress_test: {e}")

    time.sleep(2)

    # ── 5. ACID Verification ───────────────────────────────────────────────────
    divider("ACID VERIFICATION SUMMARY  (15 checks)", 5, 5)
    try:
        av = patch_and_import("acid_verification", MYSQL_PASS, BASE_URL)
        av.MYSQL_PASS = MYSQL_PASS
        av.run_acid_verification()
    except Exception as e:
        print(f"  ERROR in acid_verification: {e}")

    # ── final summary ──────────────────────────────────────────────────────────
    total_elapsed = time.time() - overall_start
    print("\n" + "=" * 65)
    print(f"  FULL SUITE COMPLETE in {total_elapsed:.1f}s")
    print()
    print("  NEXT STEP — Locust Visual Load Test:")
    print("    pip install locust")
    print("    locust -f locustfile.py --host http://127.0.0.1:5000")
    print("    Open: http://localhost:8089  →  Users: 20  Spawn rate: 5")
    print()
    print("  Screenshot or record this terminal output for your report.")
    print("=" * 65)
