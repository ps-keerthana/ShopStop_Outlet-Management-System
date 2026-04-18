"""
migrate_to_shards.py  –  Migrate ShopStop data into 3 remote shards
CS 432 Assignment 4 | Group: Nexus

HOW TO RUN:
    1. Make sure you're on the IITGN network (or VPN)
    2. Have your local ShopStop MySQL DB running
    3. pip install pymysql
    4. python migrate_to_shards.py

What it does:
    - Reads Member, Sale, SaleItem from your local ShopStop DB
    - Hashes each MemberID to decide which shard (0, 1, or 2) it belongs to
    - Inserts each row into the correct remote shard at 10.0.116.184
"""

import hashlib
import pymysql
import sys

# ── CONFIG ────────────────────────────────────────────────────────────

# Your LOCAL MySQL (source of existing ShopStop data)
LOCAL = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",
    "password": "Thrisha@12",   # ← change to your local MySQL password
    "database": "ShopStop",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False,
}

# Remote shard servers (all on IITGN host, different ports)
REMOTE_HOST = "10.0.116.184"
REMOTE_USER = "Nexus"
REMOTE_PASS = "password@123"
REMOTE_DB   = "Nexus"

SHARDS = {
    0: {"host": REMOTE_HOST, "port": 3307},
    1: {"host": REMOTE_HOST, "port": 3308},
    2: {"host": REMOTE_HOST, "port": 3309},
}

NUM_SHARDS = 3

# ── SHARD ROUTING ────────────────────────────────────────────────────

def get_shard_id(member_id: str) -> int:
    """
    Hash-based sharding: shard = MD5(member_id)[:8] (hex) % NUM_SHARDS
    This gives an even distribution across 3 shards.
    A NULL MemberID (guest checkout) always goes to shard 0.
    """
    if member_id is None:
        return 0
    digest = hashlib.md5(member_id.encode()).hexdigest()[:8]
    return int(digest, 16) % NUM_SHARDS


# ── CONNECTION HELPERS ───────────────────────────────────────────────

def connect_local():
    print("  Connecting to local ShopStop DB...")
    conn = pymysql.connect(**LOCAL)
    print("  ✓ Connected to local DB")
    return conn


def connect_shard(shard_id: int):
    cfg = SHARDS[shard_id]
    conn = pymysql.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=REMOTE_USER,
        password=REMOTE_PASS,
        database=REMOTE_DB,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        connect_timeout=10,
    )
    return conn


# ── MIGRATION LOGIC ──────────────────────────────────────────────────

def migrate():
    print("\n" + "="*60)
    print("  ShopStop → Nexus Shard Migration")
    print("  Strategy: Hash-based on MemberID, 3 shards")
    print("="*60)

    # Open local connection
    local_conn = connect_local()
    local_cur  = local_conn.cursor()

    # Open all 3 shard connections
    print("\n  Connecting to remote shards...")
    shard_conns = {}
    shard_curs  = {}
    for sid in range(NUM_SHARDS):
        try:
            shard_conns[sid] = connect_shard(sid)
            shard_curs[sid]  = shard_conns[sid].cursor()
            print(f"  ✓ Shard {sid} (port {SHARDS[sid]['port']}) connected")
        except Exception as e:
            print(f"  ✗ Shard {sid} connection FAILED: {e}")
            sys.exit(1)

    # ── Insert shard metadata ─────────────────────────────────────
    print("\n  Writing ShardMeta...")
    meta = {
        0: (0, 3307, "Shard 0 – MemberIDs hashing to 0"),
        1: (1, 3308, "Shard 1 – MemberIDs hashing to 1"),
        2: (2, 3309, "Shard 2 – MemberIDs hashing to 2"),
    }
    for sid, row in meta.items():
        try:
            shard_curs[sid].execute(
                "INSERT IGNORE INTO ShardMeta VALUES (%s, %s, %s)", row
            )
            shard_conns[sid].commit()
        except Exception as e:
            print(f"  Warning (ShardMeta shard {sid}): {e}")

    # ── Migrate Member table ──────────────────────────────────────
    print("\n  Migrating Member table...")
    local_cur.execute(
        "SELECT MemberID, Name, Age, Email, ContactNumber, Address, "
        "MembershipType, RegistrationDate, LoyaltyPoints FROM Member"
    )
    members = local_cur.fetchall()
    counts  = {0: 0, 1: 0, 2: 0}

    for row in members:
        sid = get_shard_id(row["MemberID"])
        try:
            shard_curs[sid].execute(
                """INSERT IGNORE INTO Member
                   (MemberID, Name, Age, Email, ContactNumber, Address,
                    MembershipType, RegistrationDate, LoyaltyPoints, shard_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (row["MemberID"], row["Name"], row["Age"], row["Email"],
                 row["ContactNumber"], row["Address"], row["MembershipType"],
                 row["RegistrationDate"], row["LoyaltyPoints"], sid)
            )
            counts[sid] += 1
        except Exception as e:
            print(f"  Error inserting Member {row['MemberID']}: {e}")

    for sid in range(NUM_SHARDS):
        shard_conns[sid].commit()
        print(f"    Shard {sid}: {counts[sid]} members")
    print(f"  ✓ Total members migrated: {sum(counts.values())} / {len(members)}")

    # ── Migrate Sale table ────────────────────────────────────────
    print("\n  Migrating Sale table...")
    # Check whether local Sale table has an OrderType column
    local_cur.execute("SHOW COLUMNS FROM Sale LIKE 'OrderType'")
    has_order_type = local_cur.fetchone() is not None
    if has_order_type:
        print("  (local Sale table has OrderType column – reading it)")
        local_cur.execute(
            "SELECT SaleID, MemberID, EmployeeID, SaleDate, TotalAmount, "
            "DiscountAmount, FinalAmount, PaymentMethod, OrderType FROM Sale"
        )
    else:
        print("  (local Sale table has no OrderType column – defaulting to 'In-Store')")
        local_cur.execute(
            "SELECT SaleID, MemberID, EmployeeID, SaleDate, TotalAmount, "
            "DiscountAmount, FinalAmount, PaymentMethod FROM Sale"
        )
    sales  = local_cur.fetchall()
    counts = {0: 0, 1: 0, 2: 0}

    for row in sales:
        sid        = get_shard_id(row["MemberID"])  # co-locate with the member
        order_type = row.get("OrderType", "In-Store")  # use default if column absent
        try:
            shard_curs[sid].execute(
                """INSERT IGNORE INTO Sale
                   (SaleID, MemberID, EmployeeID, SaleDate, TotalAmount,
                    DiscountAmount, FinalAmount, PaymentMethod, OrderType, shard_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (row["SaleID"], row["MemberID"], row["EmployeeID"],
                 row["SaleDate"], row["TotalAmount"], row["DiscountAmount"],
                 row["FinalAmount"], row["PaymentMethod"], order_type, sid)
            )
            counts[sid] += 1
        except Exception as e:
            print(f"  Error inserting Sale {row['SaleID']}: {e}")

    for sid in range(NUM_SHARDS):
        shard_conns[sid].commit()
        print(f"    Shard {sid}: {counts[sid]} sales")

    # ── Migrate SaleItem table ────────────────────────────────────
    print("\n  Migrating SaleItem table...")
    # We need to join Sale to know which shard each SaleItem goes to
    local_cur.execute(
        "SELECT si.SaleItemID, si.SaleID, si.ProductID, si.Quantity, "
        "si.UnitPrice, si.Subtotal, s.MemberID "
        "FROM SaleItem si JOIN Sale s ON si.SaleID = s.SaleID"
    )
    items  = local_cur.fetchall()
    counts = {0: 0, 1: 0, 2: 0}

    for row in items:
        sid = get_shard_id(row["MemberID"])
        try:
            shard_curs[sid].execute(
                """INSERT IGNORE INTO SaleItem
                   (SaleItemID, SaleID, ProductID, Quantity,
                    UnitPrice, Subtotal, shard_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (row["SaleItemID"], row["SaleID"], row["ProductID"],
                 row["Quantity"], row["UnitPrice"], row["Subtotal"], sid)
            )
            counts[sid] += 1
        except Exception as e:
            print(f"  Error inserting SaleItem {row['SaleItemID']}: {e}")

    for sid in range(NUM_SHARDS):
        shard_conns[sid].commit()
        print(f"    Shard {sid}: {counts[sid]} sale items")

    # ── Verify no duplication ─────────────────────────────────────
    print("\n  Verifying data integrity...")

    # Members
    total_remote_members = 0
    for sid in range(NUM_SHARDS):
        shard_curs[sid].execute("SELECT COUNT(*) AS cnt FROM Member")
        c = shard_curs[sid].fetchone()["cnt"]
        total_remote_members += c
    if total_remote_members == len(members):
        print(f"  ✓ Member count matches: {total_remote_members} rows, no duplication")
    else:
        print(f"  ✗ Member mismatch! Local: {len(members)}, Remote total: {total_remote_members}")

    # Sales
    total_remote_sales = 0
    for sid in range(NUM_SHARDS):
        shard_curs[sid].execute("SELECT COUNT(*) AS cnt FROM Sale")
        c = shard_curs[sid].fetchone()["cnt"]
        total_remote_sales += c
    if total_remote_sales == len(sales):
        print(f"  ✓ Sale count matches: {total_remote_sales} rows, no duplication")
    else:
        print(f"  ✗ Sale mismatch! Local: {len(sales)}, Remote total: {total_remote_sales}")

    # SaleItems
    total_remote_items = 0
    for sid in range(NUM_SHARDS):
        shard_curs[sid].execute("SELECT COUNT(*) AS cnt FROM SaleItem")
        c = shard_curs[sid].fetchone()["cnt"]
        total_remote_items += c
    if total_remote_items == len(items):
        print(f"  ✓ SaleItem count matches: {total_remote_items} rows, no duplication")
    else:
        print(f"  ✗ SaleItem mismatch! Local: {len(items)}, Remote total: {total_remote_items}")

    # ── Cleanup ───────────────────────────────────────────────────
    local_conn.close()
    for sid in range(NUM_SHARDS):
        shard_conns[sid].close()

    print("\n" + "="*60)
    print("  Migration complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    migrate()