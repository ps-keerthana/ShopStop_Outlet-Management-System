"""
run.py  –  Start the ShopStop Flask app
============================================
1. Update MYSQL_PASSWORD below to your MySQL root password
2. Run:  python run.py
3. Open: http://localhost:5000/login-page
"""

import os, sys

# ── EDIT THIS ─────────────────────────────────────────────────────────
MYSQL_PASSWORD = "password"   # ← put your MySQL password here
# ─────────────────────────────────────────────────────────────────────

os.environ["MYSQL_PASSWORD"] = MYSQL_PASSWORD
os.environ["MYSQL_USER"]     = "root"
os.environ["MYSQL_HOST"]     = "localhost"
os.environ["MYSQL_DB"]       = "ShopStop"
os.environ["MYSQL_PORT"]     = "3306"
os.environ["SECRET_KEY"]     = "shopstop-cs432-group15-secret"

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

app = create_app()

if __name__ == "__main__":
    print("\n" + "="*55)
    print("  ShopStop API  -  CS 432 Assignment 2 Module B")
    print("  Group 15")
    print("="*55)
    print(f"  DB  : mysql://root@localhost/ShopStop")
    print(f"  URL : http://localhost:5000/login-page")
    print("="*55 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
