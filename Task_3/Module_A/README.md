# ShopStop DBMS — Transactional B+ Tree Engine
### CS 432 Databases | Assignment 3, Module A | IIT Gandhinagar

---

## What This Is

A lightweight database management system built from scratch in Python, where every record is stored and accessed through a custom **B+ Tree**. Assignment 3 extends the Assignment 2 engine with a full transaction layer — giving it **ACID guarantees**, **crash recovery**, and **safe concurrent access** without touching the B+ Tree implementation itself.

**The problem it solves:** In Assignment 2, if the program crashed mid-operation (say, after deducting a customer's balance but before updating the stock), the database would be left in a broken, inconsistent state with no way to recover. This module fixes that.

---

## What Was Built

Four new components were added on top of the existing system:

| Component | File | What it does |
|-----------|------|--------------|
| **Write-Ahead Log** | `wal_logger.py` | Logs every operation to disk *before* touching the B+ Tree. If the program crashes, the log tells us exactly what was happening. |
| **Snapshot Manager** | `snapshot.py` | Saves a copy of table state before a transaction's first write. On rollback, rebuilds the B+ Tree from this copy. Also persists committed state to disk as `.pkl` files. |
| **Lock Manager** | `lock_manager.py` | Table-level two-phase locking (2PL). Shared locks for reads, exclusive locks for writes. Supports S→X upgrade and a 5-second timeout to prevent deadlocks. |
| **Transaction Manager** | `transaction_manager.py` | Coordinates all three above. Provides `BEGIN`, `COMMIT`, `ROLLBACK`, and two-phase crash recovery. |

---

## ACID Guarantees — All Four Tested and Passing

### Atomicity
A transaction that updates customer balance + product stock + inserts an order — if a crash happens after step 2, **both step 1 and step 2 are fully rolled back**. No partial state survives.

```
[TXN a607ce4c] BEGUN
Step 1 done: customer balance updated to 4500.0
Step 2 done: product stock updated to 8
CRASH: Simulated crash before order insert!
[TXN a607ce4c] ROLLED BACK 'customers' (3 records restored)
[TXN a607ce4c] ROLLED BACK 'products'  (3 records restored)
Customer balance after rollback: 5000.0   ✓
Product stock after rollback:    10        ✓
ATOMICITY: PASSED
```

### Consistency
A transaction trying to set stock to −99,989 is caught before any write reaches the B+ Tree. The database never enters an invalid state.

```
Constraint caught: stock would be -99989
[TXN] ROLLBACK COMPLETE
Stock after rejected update: 10 (unchanged)   ✓
CONSISTENCY: PASSED
```

### Isolation
Two threads simultaneously deduct 3 units each from the same product (stock = 10). Without locking, both would read 10 and both write 7 — losing one deduction. With 2PL:

```
Thread 1 acquires X-lock → reads 10 → commits (stock = 7)
Thread 2 waits → gets lock → reads 7 → commits (stock = 4)
Final stock: 4  (= 10 − 3 − 3)   ✓
ISOLATION: PASSED
```

### Durability
Order `O_DUR01` is committed, then a brand-new `DatabaseManager` is created (simulating a restart). Two-phase recovery runs:
- **Phase 1** — reloads last committed state from `.pkl` snapshots on disk
- **Phase 2** — replays any WAL entries that came after the snapshot

```
[RECOVERY] Loaded 'orders' (3 records from disk)
[RECOVERY] Found 3 committed transactions in WAL
Order after restart: {'order_id': 'O_DUR01', 'amount': 250.0}   ✓
DURABILITY: PASSED
```

### Multi-Relation Transaction *(required by assignment)*
A single transaction touches all three tables atomically — updates customer balance, updates product stock, inserts a new order. All three committed together or not at all.

```
[TXN 49c3d640] BEGUN
Step 1: customer balance 5000 → 4800
Step 2: product stock 50 → 49
Step 3: order O_MULTI01 inserted
[TXN 49c3d640] COMMITTED
MULTI-RELATION: PASSED
```

---

## How Recovery Works

```
Program crashes mid-transaction
         │
         ▼
    recover() called on restart
         │
    ┌────┴────┐
    │ Phase 1 │  Load .pkl snapshots from disk → rebuild B+ Trees
    └────┬────┘
         │
    ┌────┴────┐
    │ Phase 2 │  Read WAL log → replay committed txns → ignore incomplete ones
    └────┬────┘
         │
         ▼
    Database is consistent ✓
```

Incomplete transactions (those with a `BEGIN` but no `COMMIT` in the WAL) are silently ignored — their effects never reached disk, so no undo step is needed.

---

## Performance

Transactional inserts carry overhead compared to direct B+ Tree access:

| Operations | Direct (ms) | Transactional (ms) | Overhead |
|------------|-------------|-------------------|---------|
| 10 | 0.06 | 17.84 | ~297× |
| 100 | 0.28 | 133.25 | ~476× |
| 500 | 1.61 | 1023.43 | ~636× |

The dominant cost is **snapshot extraction** — before each transaction's first write, all records are read out of the B+ Tree into a flat dictionary (O(current table size)). As the table grows, this scan gets more expensive. WAL disk I/O and lock overhead are secondary.

In a production system this would be replaced by row-level undo logging (as used by InnoDB), making the cost O(rows changed) instead of O(table size).

---

## Project Structure

```
Module_A/
├── db_management_system/
│   ├── database/
│   │   ├── bplustree.py            ← Core B+ Tree (unchanged from Assignment 2)
│   │   ├── table.py                ← Schema-validated table wrapper
│   │   ├── db_manager.py           ← Multi-table database manager
│   │   ├── transaction_manager.py  ← [NEW] BEGIN / COMMIT / ROLLBACK + recovery
│   │   ├── wal_logger.py           ← [NEW] Write-Ahead Log
│   │   ├── snapshot.py             ← [NEW] Pre-transaction snapshots + disk persist
│   │   └── lock_manager.py         ← [NEW] Two-phase locking (2PL)
│   ├── data/
│   │   ├── wal.log                 ← Auto-created: full transaction history
│   │   └── snapshots/              ← Auto-created: committed state (.pkl files)
│   ├── report_Assignment3.ipynb    ← [NEW] All ACID tests + recovery demo
│   └── requirements.txt
└── readme.md
```

---

## Running the Notebook

### Google Colab (recommended)
1. Upload `db_management_system.zip` to Colab session storage
2. Open `report_Assignment3.ipynb`
3. Run all cells top to bottom (`Runtime → Run all`)

### Local
```bash
unzip db_management_system.zip && cd db_management_system
pip install -r requirements.txt
jupyter notebook report_Assignment3.ipynb
```

---

## Dependencies

```
graphviz==0.20.3   # B+ Tree visualisation
matplotlib==3.8.2  # benchmark plots
pandas==2.1.4      # WAL log inspection tables
jupyter==1.0.0     # notebook server
```

Standard library used: `threading`, `uuid`, `json`, `pickle`, `os`, `datetime`, `time`, `tracemalloc`

---

## References
- Ramakrishnan & Gehrke, *Database Management Systems* (3rd ed.) — B+ Tree theory, ACID properties, WAL and recovery algorithms
- Python [`threading`](https://docs.python.org/3/library/threading.html) docs — `threading.Condition` for lock blocking
