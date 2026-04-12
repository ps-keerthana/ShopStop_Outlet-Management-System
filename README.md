# ShopStop — Outlet Management System

> **CS 432 Databases | IIT Gandhinagar**
> A progressively built database project — from schema design to a full transaction engine with ACID compliance.

---

## What Is This?

ShopStop is a retail outlet management system developed across three assignments for CS 432. Each assignment builds on the previous one, going from a clean relational schema all the way to a Python-based transaction manager with Write-Ahead Logging and Two-Phase Locking.

The system models a real retail store: members, employees, suppliers, products, categories, sales, and purchase orders — with business rules enforced at every layer.

---

## Repository Structure

```
ShopStop_Outlet Management System/
│
├── Task_1/                         ← Assignment 1: Schema Design & ER Modelling
│   ├── shopstop.sql                ← Full MySQL schema with constraints + sample data
│   ├── ER.pdf                      ← Entity-Relationship diagram
│   └── Track1_Group15_A1.pdf       ← Submitted report
│
├── Task_2/                         ← Assignment 2: Indexing & Web Application
│   ├── Module_A/                   ← B+ Tree indexing engine (pure Python)
│   │   ├── db_management_system/
│   │   │   ├── database/           ← BPlusTree, Table, DatabaseManager, PerformanceAnalyzer
│   │   │   ├── report.ipynb        ← Live demos, tree visualisations, benchmarks
│   │   │   └── requirements.txt
│   │   └── readme.md
│   │
│   └── Module_B/                   ← Flask REST API + RBAC + SQL index benchmarking
│       ├── app/                    ← Flask application (routes, auth, db connector)
│       ├── sql/                    ← Schema additions for Module B (UserCredentials, indexes)
│       ├── shopstop.sql            ← Updated database with Module B additions
│       ├── run.py                  ← Entry point — starts the Flask server
│       ├── report.ipynb            ← SQL index benchmarking notebook
│       └── README.md
│
└── Task_3/                         ← Assignment 3: Transactions, WAL, and ACID
    ├── Module_A/                   ← Transaction engine on top of the B+ Tree
    │   ├── db_management_system/
    │   │   ├── database/           ← WALLogger, LockManager, SnapshotManager,
    │   │   │                          TransactionManager (all new in A3)
    │   │   └── data/               ← wal.log + snapshots/ (runtime-generated)
    │   └── README.md
    │
    └── Module_B/                   ← ACID testing suite on top of the Flask API
        ├── app/                    ← Flask app (carried over from Task 2)
        ├── Module_B_A3/            ← All new test scripts for A3
        │   ├── acid_verification.py
        │   ├── concurrent_users.py
        │   ├── failure_simulation.py
        │   ├── race_condition_test.py
        │   ├── stress_test.py
        │   ├── run_all_tests.py
        │   ├── locustfile.py
        │   └── locust_reports/
        └── logs/audit.log
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

**File to run:**
```sql
mysql -u root -p < Task_1/shopstop.sql
```

---

## Task 2 — Indexing and Web Application

### Module A — B+ Tree Indexing Engine

A database engine built from scratch in Python with a B+ Tree as the core index structure.

**What it implements:**

| Capability | Details |
|------------|---------|
| B+ Tree operations | Insert, delete, exact search, range query, aggregations |
| Tree visualisation | Graphviz-rendered PNG diagrams of the tree structure |
| Schema-validated tables | `Table` class wraps B+ Tree with field type checking |
| Multi-table management | `DatabaseManager` handles multiple named databases |
| Performance benchmarking | Automated comparison against a brute-force O(n) baseline |

**How to run (Google Colab — recommended):**
1. Upload `Task_2/Module_A/db_management_system.zip` to Colab
2. Open `report.ipynb` in Colab
3. Run Cell 1 — it installs all dependencies and sets up the environment
4. Run all remaining cells in order

**How to run (local machine):**
```bash
# Install system dependency
sudo apt-get install graphviz        # Ubuntu/Debian
brew install graphviz                # macOS

# Set up Python environment
cd Task_2/Module_A/db_management_system
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

jupyter notebook report.ipynb
```

**Module structure:**

| File | Role |
|------|------|
| `bplustree.py` | Core B+ Tree — splits, merges, borrows, leaf linking, Graphviz rendering |
| `bruteforce.py` | O(n) linear baseline for performance comparison |
| `table.py` | Schema-validated table wrapping the B+ Tree |
| `db_manager.py` | Multi-database / multi-table manager |
| `performance.py` | Benchmarking — timing with `perf_counter`, memory with `tracemalloc` |

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

Extends the Task 2 B+ Tree engine with full transaction support. Four new modules were added to the `database/` package:

| New file | What it does |
|----------|-------------|
| `wal_logger.py` | **Write-Ahead Log** — every BEGIN, INSERT, UPDATE, DELETE, COMMIT, and ROLLBACK is appended to `data/wal.log` *before* touching the B+ Tree. Guarantees durability and crash recovery. |
| `lock_manager.py` | **Two-Phase Locking (2PL)** — table-level shared (S) and exclusive (X) locks with a growing phase and shrinking phase. Concurrent transactions block on conflicting locks with a configurable timeout. |
| `snapshot.py` | **SnapshotManager** — captures per-transaction, per-table snapshots at the start of each operation, used to restore state on rollback. |
| `transaction_manager.py` | **TransactionManager + Transaction** — the public API. `begin()` starts a transaction, which then exposes `insert()`, `update()`, `delete()`, `get()`, `commit()`, and `rollback()`. Orchestrates WAL + locks + snapshots to deliver ACID. |

**ACID guarantees:**

- **Atomicity** — `rollback()` restores all tables to their pre-transaction snapshots
- **Consistency** — schema validation in `Table` prevents invalid records at write time
- **Isolation** — 2PL ensures no two concurrent transactions can simultaneously write the same table
- **Durability** — WAL is flushed to disk before the B+ Tree is modified; the log can be replayed after a crash

**How to run:** Same as Task 2 Module A — open `Task_3/Module_A/db_management_system/report.ipynb` and run all cells.

---

### Module B — ACID Verification and Stress Testing

A suite of test scripts that verify ACID properties and measure the Flask API under concurrent and failure conditions.

**Test scripts in `Module_B_A3/`:**

| Script | What it tests |
|--------|--------------|
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

## Dependencies

### Module A (B+ Tree engine)

```
graphviz==0.20.3
matplotlib==3.8.2
pandas==2.1.4
tabulate==0.9.0
ipykernel==6.29.0
jupyter==1.0.0
```

System binary also required: `graphviz` (`apt-get install graphviz` / `brew install graphviz`)

### Module B (Flask API)

```
flask
pymysql
pyjwt
bcrypt
```

Full list in `requirements.txt` inside each module folder.

### Module B A3 (Testing)

```
locust
requests
```

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

---

## Course Context

| Assignment | Scope |
|------------|-------|
| Task 1 | ER modelling, schema design, normalisation, SQL constraints |
| Task 2 | B+ Tree index structures, REST APIs, JWT auth, RBAC, SQL indexing |
| Task 3 | Transaction management, WAL, 2PL, ACID properties, concurrency testing |

**Course:** CS 432 — Databases, IIT Gandhinagar (2026, Track 1, Group 15)
