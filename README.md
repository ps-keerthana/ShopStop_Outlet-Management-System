# ShopStop — Outlet Management System

> **CS 432 Databases · IIT Gandhinagar · 2025–26 · Track 1 · Group 15 (Nexus)**
> A progressively built database project — from schema design to a fully sharded, distributed system.

---

## What Is This?

ShopStop is a retail outlet management system developed across **four assignments** for CS 432. Each task layers new database concepts on top of the previous one — from a clean relational schema all the way to a horizontally sharded, distributed Flask API with ACID compliance.

The system models a real retail store: members, employees, suppliers, products, categories, sales, and purchase orders — with business rules enforced at every layer.

---

## Repository Structure

```
ShopStop_Outlet Management System/
│
├── Task_1/                            ← Assignment 1: Schema Design & ER Modelling
│   ├── shopstop.sql                   ← Full MySQL schema with constraints + sample data
│   ├── ER.pdf                         ← Entity-Relationship diagram
│   └── Track1_Group15_A1.pdf          ← Submitted report
│
├── Task_2/                            ← Assignment 2: Indexing & Web Application
│   ├── Module_A/                      ← B+ Tree indexing engine (pure Python)
│   │   ├── db_management_system/
│   │   │   ├── database/              ← BPlusTree, Table, DatabaseManager, PerformanceAnalyzer
│   │   │   ├── report.ipynb           ← Live demos, tree visualisations, benchmarks
│   │   │   └── requirements.txt
│   │   └── readme.md
│   │
│   └── Module_B/                      ← Flask REST API + RBAC + SQL index benchmarking
│       ├── app/                       ← Flask application (routes, auth, db connector)
│       ├── sql/                       ← Schema additions (UserCredentials, indexes)
│       ├── shopstop.sql               ← Updated DB with Module B additions
│       ├── run.py                     ← Entry point — starts the Flask server
│       ├── report.ipynb               ← SQL index benchmarking notebook
│       └── README.md
│
├── Task_3/                            ← Assignment 3: Transactions, WAL, and ACID
│   ├── Module_A/                      ← Transaction engine on top of the B+ Tree
│   │   ├── db_management_system/
│   │   │   ├── database/              ← WALLogger, LockManager, SnapshotManager,
│   │   │   │                             TransactionManager (all new in A3)
│   │   │   └── data/                  ← wal.log + snapshots/ (runtime-generated)
│   │   └── README.md
│   │
│   └── Module_B/                      ← ACID testing suite on top of the Flask API
│       ├── app/                       ← Flask app (carried over from Task 2)
│       ├── Module_B_A3/               ← All new test scripts for A3
│       │   ├── acid_verification.py
│       │   ├── concurrent_users.py
│       │   ├── failure_simulation.py
│       │   ├── race_condition_test.py
│       │   ├── stress_test.py
│       │   ├── run_all_tests.py
│       │   ├── locustfile.py
│       │   └── locust_reports/        ← Pre-generated Locust HTML reports
│       └── logs/audit.log
│
└── Task_4/                            ← Assignment 4: Horizontal Sharding ← NEW
    ├── app/
    │   ├── shard_router.py            ← NEW: Core shard routing engine (MD5 hash-based)
    │   ├── routes/
    │   │   ├── members.py             ← UPDATED: All reads/writes route to correct shard
    │   │   ├── sales.py               ← UPDATED: Single-shard lookup + 3-shard range fan-out
    │   │   └── shards.py              ← NEW: Diagnostic/demo endpoints
    │   └── __init__.py                ← UPDATED: Shard config + custom JSON provider
    ├── sql/
    │   ├── schema_moduleB.sql
    │   └── shard_setup.sql            ← NEW: Creates tables on each remote shard
    ├── migrate_to_shards.py           ← NEW: Migrates existing data to 3 shards
    ├── test_sharding.py               ← NEW: 6 automated verification tests
    ├── run.py                         ← UPDATED: Shard environment variables
    └── README.md
```

---

## The Database Schema

The ShopStop MySQL database has nine tables modelling a complete retail operation:

| Table | What it stores |
|-------|----------------|
| `Member` | Registered customers — membership tier (Silver/Gold/Platinum), loyalty points |
| `Employee` | Staff with self-referencing `ManagerID` for hierarchy |
| `Supplier` | Vendors with supply category and rating |
| `Category` | Hierarchical product categories (self-referencing `ParentCategoryID`) |
| `Product` | Items with stock, reorder level, expiry, barcode |
| `Sale` | Transaction header — payment method, discount, final amount |
| `SaleItem` | Line items within each sale |
| `PurchaseOrder` | Supplier restocking orders |
| `PurchaseOrderItem` | Line items within each purchase order |

Key constraints enforced in the schema: `FinalAmount = TotalAmount - DiscountAmount`, expiry date must be after manufacture date, salary and prices must be positive, loyalty points cannot go negative.

---

## Task 1 — Schema Design and ER Modelling

**Goal:** Design and implement the full relational database from scratch.

- Drew the ER diagram covering all entities, relationships, and cardinalities
- Translated it to a normalised MySQL schema with primary keys, foreign keys, check constraints, and cascades
- Populated sample data across all tables to support realistic queries

**Run the schema:**
```sql
mysql -u root -p < Task_1/shopstop.sql
```

---

## Task 2 — Indexing and Web Application

### Module A — B+ Tree Indexing Engine

A database engine built from scratch in Python with a B+ Tree as the core index structure.

| Capability | Details |
|------------|---------|
| B+ Tree operations | Insert, delete, exact search, range query, aggregations |
| Tree visualisation | Graphviz-rendered PNG diagrams of the tree structure |
| Schema-validated tables | `Table` class wraps B+ Tree with field type checking |
| Multi-table management | `DatabaseManager` handles multiple named databases |
| Performance benchmarking | Automated comparison against a brute-force O(n) baseline |

| File | Role |
|------|------|
| `bplustree.py` | Core B+ Tree — splits, merges, borrows, leaf linking, Graphviz rendering |
| `bruteforce.py` | O(n) linear baseline for performance comparison |
| `table.py` | Schema-validated table wrapping the B+ Tree |
| `db_manager.py` | Multi-database / multi-table manager |
| `performance.py` | Benchmarking — timing with `perf_counter`, memory with `tracemalloc` |

**How to run (Google Colab — recommended):**
1. Upload `Task_2/Module_A/db_management_system.zip` to Colab
2. Open `report.ipynb` in Colab
3. Run Cell 1 — installs all dependencies and sets up the environment
4. Run all remaining cells in order

**How to run (local):**
```bash
sudo apt-get install graphviz        # Ubuntu/Debian
brew install graphviz                # macOS

cd Task_2/Module_A/db_management_system
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
jupyter notebook report.ipynb
```

---

### Module B — Flask REST API with RBAC

A locally running web application on top of the ShopStop MySQL database.

**Features:**
- JWT-based authentication (HS256)
- Role-based access control — Admin vs Regular User
- Full CRUD REST APIs for Members, Products, Sales, Employees, Orders
- Member portfolio page and billing counter UI
- Security audit log (`logs/audit.log`) recording every API action
- SQL index benchmarking notebook comparing query speed before and after indexing

**Quick start:**
```bash
cd Task_2/Module_B
pip install -r requirements.txt

# Load database
mysql -u root -p
> source /full/path/to/shopstop.sql
> source /full/path/to/sql/schema_moduleB.sql

# Update MySQL password in run.py (line 10), then:
python run.py

# First-time only — initialise passwords:
curl -X POST http://127.0.0.1:5000/init-passwords
```

Open `http://localhost:5000/login-page` in your browser.

**Login credentials:**

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Admin — full access |
| `rajesh` | `user123` | Regular user |
| `priya` | `user123` | Regular user |
| `amit` | `user123` | Regular user |

**Tech stack:** Python · Flask · MySQL 8.0 · PyJWT · bcrypt · Vanilla HTML/CSS/JS

---

## Task 3 — Transactions, WAL, and ACID

### Module A — Transaction Engine on the B+ Tree

Extends the Task 2 B+ Tree engine with full transaction support. Four new modules added to the `database/` package:

| New file | What it does |
|----------|-------------|
| `wal_logger.py` | **Write-Ahead Log** — every BEGIN, INSERT, UPDATE, DELETE, COMMIT, and ROLLBACK is appended to `data/wal.log` *before* touching the B+ Tree. Guarantees durability and crash recovery. |
| `lock_manager.py` | **Two-Phase Locking (2PL)** — table-level shared (S) and exclusive (X) locks with a growing phase and shrinking phase. Concurrent transactions block on conflicting locks with a configurable timeout. |
| `snapshot.py` | **SnapshotManager** — captures per-transaction, per-table snapshots at the start of each operation, used to restore state on rollback. |
| `transaction_manager.py` | **TransactionManager + Transaction** — the public API. `begin()` starts a transaction, which exposes `insert()`, `update()`, `delete()`, `get()`, `commit()`, and `rollback()`. Orchestrates WAL + locks + snapshots to deliver ACID. |

**ACID guarantees:**

| Property | Implementation |
|----------|---------------|
| **Atomicity** | `rollback()` restores all tables to their pre-transaction snapshots |
| **Consistency** | Schema validation in `Table` prevents invalid records at write time |
| **Isolation** | 2PL ensures no two concurrent transactions simultaneously write the same table |
| **Durability** | WAL is flushed to disk before the B+ Tree is modified; log can be replayed after a crash |

**How to run:** Same as Task 2 Module A — open `Task_3/Module_A/db_management_system/report.ipynb` and run all cells.

---

### Module B — ACID Verification and Stress Testing

A suite of test scripts that verify ACID properties and measure the Flask API under concurrent and failure conditions.

| Script | What it tests |
|--------|--------------
| `acid_verification.py` | Verifies all four ACID properties through targeted test cases |
| `concurrent_users.py` | Simulates multiple simultaneous users hitting the API |
| `race_condition_test.py` | Deliberately triggers competing writes to check isolation |
| `failure_simulation.py` | Mid-transaction crashes and checks recovery correctness |
| `stress_test.py` | High-volume load to measure throughput and error rates |
| `locustfile.py` | Locust-based load testing with HTML reports |
| `run_all_tests.py` | Runs all of the above in sequence |

**Run all tests:**
```bash
# Flask server must be running first (python run.py in Module_B/)

cd Task_3/Module_B/Module_B_A3
python run_all_tests.py
```

**Run Locust load test:**
```bash
locust -f locustfile.py --host=http://127.0.0.1:5000
# Open http://localhost:8089 to configure and launch
```

Pre-generated Locust HTML reports are saved in `locust_reports/`.

---

## Task 4 — Horizontal Sharding *(New)*

Extends the Assignment 3 Flask app with **horizontal database sharding** — the `Member`, `Sale`, and `SaleItem` tables are distributed across 3 remote MySQL Docker nodes.

### Shard Key & Strategy

**Shard Key:** `MemberID`  
**Strategy:** Hash-based

```
shard_id = int(MD5(member_id)[:8], 16) % 3
```

**Why MemberID?**
- **High cardinality** — every member has a unique ID; data spreads evenly across shards
- **Query-aligned** — almost every API endpoint filters by MemberID
- **Stable** — MemberIDs never change after creation

**Co-location:** `Sale` and `SaleItem` are stored on the *same shard* as their `Member` — queries like "all sales for MEM001" never need cross-shard joins.

### Shard Topology

| Shard | MySQL Port | phpMyAdmin | Members |
|-------|-----------|------------|---------|
| Shard 0 | 3307 | http://10.0.116.184:8081 | 5 rows |
| Shard 1 | 3308 | http://10.0.116.184:8082 | 12 rows |
| Shard 2 | 3309 | http://10.0.116.184:8083 | 3 rows |

> **Note:** Shards are accessible only from the IITGN network.

### Files Changed from Task 3

| File / Folder | Change |
|---|---|
| `app/shard_router.py` | **NEW** — core routing engine (`get_shard`, `get_all_shards`) |
| `app/routes/members.py` | **REPLACED** — all reads/writes route to correct shard |
| `app/routes/sales.py` | **REPLACED** — single-shard lookup + 3-shard range fan-out |
| `app/routes/shards.py` | **NEW** — diagnostic/demo endpoints |
| `app/__init__.py` | **UPDATED** — shard config + custom JSON provider (ISO dates) |
| `run.py` | **UPDATED** — shard environment variables |
| `sql/shard_setup.sql` | **NEW** — creates Member, Sale, SaleItem, ShardMeta on each shard |
| `migrate_to_shards.py` | **NEW** — migrates existing data from local DB to 3 remote shards |
| `test_sharding.py` | **NEW** — 6 automated verification tests |

Everything else (Products, Employees, Orders, auth) is **unchanged** from Task 3.

### Setup & Run

**Prerequisites:**
```bash
pip install flask==3.0.3 pymysql==1.1.1 PyJWT==2.8.0 bcrypt==4.1.3 requests
```
- Local MySQL running with the ShopStop database from Assignment 3
- Must be on IITGN network to reach remote shards at `10.0.116.184`

**Before running anything — fix hardcoded passwords:**
Open `app/__init__.py` line 47 and change to:
```python
app.config["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD", "")
```
Also update `run.py` line 13 and `migrate_to_shards.py` line 28 with your local MySQL root password.

**Step 1 — Create shard tables on all 3 remote nodes:**
```bash
mysql -h 10.0.116.184 -P 3307 -u Nexus -p Nexus < sql/shard_setup.sql
mysql -h 10.0.116.184 -P 3308 -u Nexus -p Nexus < sql/shard_setup.sql
mysql -h 10.0.116.184 -P 3309 -u Nexus -p Nexus < sql/shard_setup.sql
```

**Step 2 — Migrate data to the 3 shards:**
```bash
python migrate_to_shards.py
```
Expected output:
```
✓ Shard 0 (port 3307) connected
✓ Shard 1 (port 3308) connected
✓ Shard 2 (port 3309) connected
  Shard 0: 5 members  |  Shard 1: 12 members  |  Shard 2: 3 members
✓ Total members migrated: 20 / 20
Migration complete!
```

**Step 3 — Start the Flask app:**
```bash
python run.py
```

**Step 4 — Run automated verification (6 tests):**
```bash
python test_sharding.py
```
```
✓ Test 1: Routing Logic         (MEM001→shard1, MEM005→shard0, MEM012→shard2)
✓ Test 2: Single-Shard Lookup   (MEM001 found on exactly shard 1)
✓ Test 3: Insert Routing        (new member lands on correct shard)
✓ Test 4: Range Query           (27 sales from 3 shards, sorted by date)
✓ Test 5: Data Distribution     (all 3 shards have data)
✓ Test 6: No Duplication        (every member on exactly 1 shard)
```

### Key API Endpoints

**No token needed:**
```
GET /api/shards/status
    → All 3 shards reachable, hostnames, member counts

GET /api/shards/route?member_id=MEM001
    → Shows MD5 formula + shard decision for any MemberID
```

**Requires admin token (`Authorization: Bearer <token>`):**
```
GET /api/shards/distribution      → Member/Sale counts per shard + totals
GET /api/shards/verify/MEM001     → Proves MEM001 exists on exactly 1 shard
GET /api/members/MEM001           → Single member — response includes _shard_id
GET /api/sales/range?from=...     → Range query across all 3 shards
GET /api/members                  → Fan-out to all 3 shards, merged result
POST /api/members                 → Insert routed to correct shard
```

**Get admin token:**
```bash
curl -X POST http://localhost:5000/init-passwords        # run once
curl -X POST http://localhost:5000/login \
     -H "Content-Type: application/json" \
     -d '{"user": "admin", "password": "admin123"}'
# → {"session_token": "eyJhbGci..."}
```

### Scalability Trade-offs

| Aspect | Design Decision |
|--------|----------------|
| Horizontal scaling | 3 shards handle ~1/3 data each. Adding nodes beats upgrading hardware. |
| Consistency | Strong within one shard. Cross-shard range queries are eventually consistent. |
| Availability | One shard down → ~33% members unavailable, other 67% keep working. |
| Fault tolerance | Unreachable shard returns `None` instead of crashing — partial results with `degraded: true`. |

### Known Limitations

1. **Hash re-balancing** — adding a 4th shard requires re-hashing and migrating all data
2. **No distributed transactions** — cross-shard writes are not atomic
3. **Guest sales skew** — `NULL MemberID` always routes to Shard 0; high guest traffic causes imbalance
4. **Cross-shard aggregation** — total revenue queries require application-level merge, not a single SQL
5. **Uneven 5/12/3 split** — expected variance at 20 members; converges to ~33%/33%/33% at scale

---

## Dependencies

### Module A — B+ Tree Engine

```
graphviz==0.20.3
matplotlib==3.8.2
pandas==2.1.4
tabulate==0.9.0
ipykernel==6.29.0
jupyter==1.0.0
```

System binary also required: `graphviz` (`apt-get install graphviz` / `brew install graphviz`)

### Module B — Flask API (Tasks 2, 3 & 4)

```
flask
pymysql
pyjwt
bcrypt
requests     # Task 3 & 4 testing only
locust       # Task 3 load testing only
```

Full list in each module's `requirements.txt`.

---

## Troubleshooting

**`Unknown column 'OrderType'` error in MySQL**
```sql
USE ShopStop;
ALTER TABLE Sale ADD COLUMN OrderType ENUM('In-Store','Online') DEFAULT 'In-Store';
```

**`Passwords not initialised` error**
```bash
curl -X POST http://127.0.0.1:5000/init-passwords
```

**Port 5000 already in use**  
Change the port in `run.py`:
```python
app.run(host="0.0.0.0", port=5001, debug=True)
```
Then go to `http://localhost:5001/login-page`.

**MySQL not running (Windows)**  
Task Manager → Services → MySQL80 → right-click → Start

**Graphviz `ExecutableNotFound` error**  
The Python `graphviz` package is just a wrapper — the system binary must also be installed separately (see setup instructions above).

**Cannot reach shards (Task 4)**  
Ensure you are connected to the IITGN network. Shard hosts at `10.0.116.184` are only reachable on-campus.

---

## Assignment Progression

| Task | Core Concept | Key Deliverable |
|------|-------------|-----------------|
| Task 1 | ER modelling, schema design, normalisation | `shopstop.sql` — full MySQL schema |
| Task 2 | B+ Tree indexing, REST APIs, JWT auth, RBAC | B+ Tree engine + Flask API |
| Task 3 | Transaction management, WAL, 2PL, ACID | Transaction engine + ACID test suite |
| Task 4 | Horizontal sharding, distributed data | Sharded Flask API across 3 MySQL nodes |

**Course:** CS 432 — Databases, IIT Gandhinagar (2025–26, Track 1, Group 15 / Nexus)