# ShopStop — Assignment 4: Sharding
**CS 432 Databases | Group: Nexus | Semester II 2025–26**

---

## What's New in Assignment 4

This extends the Assignment 3 Flask app with **horizontal sharding** of
the `Member`, `Sale`, and `SaleItem` tables across 3 remote MySQL Docker nodes.

| File / Folder | What Changed |
|---|---|
| `app/shard_router.py` | **NEW** – core routing engine (`get_shard`, `get_all_shards`) |
| `app/routes/members.py` | **REPLACED** – all reads/writes route to correct shard |
| `app/routes/sales.py` | **REPLACED** – single-shard lookup + 3-shard range fan-out |
| `app/routes/shards.py` | **NEW** – diagnostic/demo endpoints for report & video |
| `app/__init__.py` | **UPDATED** – shard config + custom JSON provider (ISO dates) |
| `run.py` | **UPDATED** – shard environment variables |
| `sql/shard_setup.sql` | **NEW** – creates Member, Sale, SaleItem, ShardMeta on each shard |
| `migrate_to_shards.py` | **NEW** – migrates existing data from local DB to 3 remote shards |
| `test_sharding.py` | **NEW** – automated verification (6 tests) |

Everything else (Products, Employees, Orders, auth) is **unchanged** from A3.

---

## Shard Key & Strategy

**Shard Key:** `MemberID`

**Strategy:** Hash-based
```
shard_id = int(MD5(member_id)[:8], 16) % 3
```

**Justification:**
- **High cardinality** – every member has a unique ID; data spreads evenly
- **Query-aligned** – almost every API endpoint filters by MemberID
- **Stable** – MemberIDs never change after creation

**Co-location:** `Sale` and `SaleItem` are stored on the same shard as their
`Member` — queries like "all sales for MEM001" never need cross-shard joins.

**Topology:**

| Shard | MySQL Port | phpMyAdmin |
|-------|-----------|------------|
| Shard 0 | 3307 | http://10.0.116.184:8081 |
| Shard 1 | 3308 | http://10.0.116.184:8082 |
| Shard 2 | 3309 | http://10.0.116.184:8083 |

**Credentials:** Username: `Nexus` / Password: `password@123` / Server: *(leave empty)*

---

## One-Time Setup — Fix Hardcoded Password

Before running anything, open `app/__init__.py` and change **line 47** to:
```python
app.config["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD", "")
```

Also update **`run.py`** line 13 and **`migrate_to_shards.py`** line 28 with your own local MySQL root password.

---

## How to Run — Complete Step by Step

### Prerequisites
```
pip install flask==3.0.3 pymysql==1.1.1 PyJWT==2.8.0 bcrypt==4.1.3 requests
```
- Local MySQL running with the ShopStop database from Assignment 3
- **Must be on IITGN network** to reach remote shards at 10.0.116.184

---

### Step 1 — Create tables on all 3 remote shards
*(Run in terminal. Password each time: `password@123`)*

```bash
mysql -h 10.0.116.184 -P 3307 -u Nexus -p Nexus < sql/shard_setup.sql
mysql -h 10.0.116.184 -P 3308 -u Nexus -p Nexus < sql/shard_setup.sql
mysql -h 10.0.116.184 -P 3309 -u Nexus -p Nexus < sql/shard_setup.sql
```

Expected from each:
```
Status
Shard tables created in database Nexus on port: 3306
```

---

### Step 2 — Migrate existing data to the 3 shards

```bash
python migrate_to_shards.py
```

Expected:
```
✓ Shard 0 (port 3307) connected
✓ Shard 1 (port 3308) connected
✓ Shard 2 (port 3309) connected
  Shard 0: 5 members  |  Shard 1: 12 members  |  Shard 2: 3 members
✓ Total members migrated: 20 / 20
✓ Sale count matches: 27 rows, no duplication
✓ SaleItem count matches: 67 rows, no duplication
Migration complete!
```

---

### Step 3 — Start the app

```bash
python run.py
```

Expected:
```
ShopStop API  -  CS 432 Assignment 4 (Sharding)
Group: Nexus
Shard 0 : mysql://Nexus@10.0.116.184:3307/Nexus
Shard 1 : mysql://Nexus@10.0.116.184:3308/Nexus
Shard 2 : mysql://Nexus@10.0.116.184:3309/Nexus
Running on http://127.0.0.1:5000
```

---

### Step 4 — Run automated verification tests

```bash
python test_sharding.py
```

All 6 tests should pass:
```
✓ Test 1: Routing Logic         (MEM001→shard1, MEM005→shard0, MEM012→shard2)
✓ Test 2: Single-Shard Lookup   (MEM001 found on exactly shard 1)
✓ Test 3: Insert Routing        (new member lands on correct shard)
✓ Test 4: Range Query           (27 sales from 3 shards, sorted by date)
✓ Test 5: Data Distribution     (all 3 shards have data)
✓ Test 6: No Duplication        (every member on exactly 1 shard)
```

---

### Step 5 — Verify via MySQL CLI

Check which container you're connected to (assignment debugging tip):
```bash
mysql -h 10.0.116.184 -P 3307 -u Nexus -p Nexus -e "SELECT @@hostname;"
mysql -h 10.0.116.184 -P 3308 -u Nexus -p Nexus -e "SELECT @@hostname;"
mysql -h 10.0.116.184 -P 3309 -u Nexus -p Nexus -e "SELECT @@hostname;"
```
Each should return a **different hostname** — proves 3 separate Docker containers.

View Member table on each shard:
```bash
mysql -h 10.0.116.184 -P 3307 -u Nexus -p Nexus -e "SELECT MemberID, Name, shard_id FROM Member;"
mysql -h 10.0.116.184 -P 3308 -u Nexus -p Nexus -e "SELECT MemberID, Name, shard_id FROM Member;"
mysql -h 10.0.116.184 -P 3309 -u Nexus -p Nexus -e "SELECT MemberID, Name, shard_id FROM Member;"
```
Expected: 5 rows / 12 rows / 3 rows respectively.

View Sale table on each shard:
```bash
mysql -h 10.0.116.184 -P 3307 -u Nexus -p Nexus -e "SELECT SaleID, MemberID, shard_id FROM Sale;"
mysql -h 10.0.116.184 -P 3308 -u Nexus -p Nexus -e "SELECT SaleID, MemberID, shard_id FROM Sale;"
mysql -h 10.0.116.184 -P 3309 -u Nexus -p Nexus -e "SELECT SaleID, MemberID, shard_id FROM Sale;"
```
Expected: 7 rows / 17 rows / 3 rows respectively.

---

### Step 6 — Verify via phpMyAdmin

Open in browser (must be on IITGN network). Leave Server field **empty**:

- http://10.0.116.184:8081 → Nexus DB → Member table (5 rows)
- http://10.0.116.184:8082 → Nexus DB → Member table (12 rows)
- http://10.0.116.184:8083 → Nexus DB → Member table (3 rows)

---

## Key API Endpoints

### No token needed (open in browser directly)
```
GET /api/shards/status
    → All 3 shards reachable, hostnames, member counts

GET /api/shards/route?member_id=MEM001
    → Shows MD5 formula + shard decision for any MemberID
```

### Requires admin token (use Authorization: Bearer <token>)
```
GET /api/shards/distribution
    → Member/Sale counts per shard + totals

GET /api/shards/verify/MEM001
    → Proves MEM001 exists on exactly 1 shard (no duplication)

GET /api/members/MEM001
    → Single member — response includes _shard_id proving 1-shard routing

GET /api/sales/range?from=2024-01-01&to=2026-12-31
    → Range query across all 3 shards — response includes shard_counts

GET /api/members
    → Fan-out to all 3 shards, merged result

POST /api/members
    → Insert routed to correct shard — response includes shard_id
```

### How to get admin token
```
POST http://localhost:5000/init-passwords   (run once, no body)
POST http://localhost:5000/login
Body: {"user": "admin", "password": "admin123"}
Response: {"session_token": "eyJhbGci..."}
```
Add header to every protected request: `Authorization: Bearer <token>`

---

## Scalability Trade-offs Summary

| Trade-off | Our Design |
|---|---|
| Horizontal vs Vertical | 3 shards handle ~1/3 data each. Adding nodes beats upgrading hardware. |
| Consistency | Strong within one shard. Cross-shard range queries are eventually consistent. |
| Availability | One shard down = ~33% members unavailable, other 67% keep working. |
| Partition Tolerance | Unreachable shard returns None instead of crashing — partial results returned with `degraded: true`. |

---

## Observations & Limitations

1. Hash re-balancing: adding a 4th shard requires re-hashing and migrating all data
2. No distributed transactions: cross-shard writes are not atomic
3. Guest sales (NULL MemberID) always route to Shard 0 — potential skew with many guest checkouts
4. Cross-shard aggregation (e.g., total revenue) requires application-level merge, not a single SQL query
5. 5/12/3 split is uneven for 20 members — expected variance; converges to 33%/33%/33% at scale
