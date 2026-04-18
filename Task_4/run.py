"""
run.py  –  Start ShopStop with Sharding (Assignment 4)
=======================================================
1. Make sure you're on IITGN network
2. Update MYSQL_PASSWORD below
3. Run:  python run.py
4. Open: http://localhost:5000/login-page
"""

import os, sys

# ── LOCAL MySQL (unchanged from Assignment 3) ──────────────────────────
MYSQL_PASSWORD = "password"   # ← your local MySQL root password

# ── REMOTE SHARD CREDENTIALS (Nexus group) ────────────────────────────
SHARD_USER     = "Nexus"
SHARD_PASSWORD = "password@123"
SHARD_DB       = "Nexus"

# ── Set env vars ──────────────────────────────────────────────────────
os.environ["MYSQL_PASSWORD"] = MYSQL_PASSWORD
os.environ["MYSQL_USER"]     = "root"
os.environ["MYSQL_HOST"]     = "localhost"
os.environ["MYSQL_DB"]       = "ShopStop"
os.environ["MYSQL_PORT"]     = "3306"
os.environ["SECRET_KEY"]     = "shopstop-cs432-group15-secret"

os.environ["SHARD_USER"]     = SHARD_USER
os.environ["SHARD_PASSWORD"] = SHARD_PASSWORD
os.environ["SHARD_DB"]       = SHARD_DB

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

app = create_app()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  ShopStop API  -  CS 432 Assignment 4 (Sharding)")
    print("  Group: Nexus")
    print("="*60)
    print(f"  Local DB : mysql://root@localhost/ShopStop")
    print(f"  Shard 0  : mysql://Nexus@10.0.116.184:3307/Nexus")
    print(f"  Shard 1  : mysql://Nexus@10.0.116.184:3308/Nexus")
    print(f"  Shard 2  : mysql://Nexus@10.0.116.184:3309/Nexus")
    print(f"  URL      : http://localhost:5000/login-page")
    print("="*60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
