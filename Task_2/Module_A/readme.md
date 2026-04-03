# ShopStop DBMS — B+ Tree Indexing Engine
### CS 432 Databases | Assignment 2, Module A

A lightweight database management system built from scratch in Python, using a **B+ Tree** as the core indexing engine. Supports insert, update, delete, exact search, range queries, and aggregations — with a full performance comparison against a brute-force linear baseline.

---

## Execution Steps

### Option A — Google Colab (Recommended)

1. **Upload the zip** — Upload `db_management_system.zip` to your Colab session storage using the files panel on the left sidebar.

2. **Open the notebook** — Upload `report.ipynb` to Colab or open it directly from Google Drive.

3. **Run Cell 1 (Setup cell)** — This cell handles everything automatically:
   ```python
   # It will:
   # - Unzip db_management_system.zip
   # - pip install all dependencies from requirements.txt
   # - apt-get install graphviz (system binary needed for tree rendering)
   # - Add db_management_system/ to sys.path
   # - Import all modules
   ```

4. **Run all remaining cells** in order — use **Runtime → Run all** or run each cell sequentially with `Shift+Enter`.

> **Note:** The benchmark cell (Section 6.1) is compute-heavy.

---

### Option B — Local Machine

**Prerequisites:** Python 3.9+ and the Graphviz system binary installed.

**Step 1 — Install Graphviz system binary**

```bash
# macOS
brew install graphviz

# Ubuntu / Debian
sudo apt-get install graphviz

# Windows — download installer from https://graphviz.org/download/
```

**Step 2 — Clone / extract the project**

```bash
unzip db_management_system.zip
cd db_management_system
```

**Step 3 — Create a virtual environment (recommended)**

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

**Step 4 — Install Python dependencies**

```bash
pip install -r requirements.txt
```

**Step 5 — Launch the notebook**

```bash
jupyter notebook report.ipynb
```

Then run all cells in order from the Jupyter interface.

**Step 6 — (Optional) Use the package directly in a Python script**

```python
import sys
sys.path.insert(0, 'db_management_system')

from database.bplustree  import BPlusTree
from database.bruteforce import BruteForceDB
from database.table      import Table
from database.db_manager import DatabaseManager

# Create a tree
tree = BPlusTree(order=8)
tree.insert(10, 'hello')
tree.insert(20, 'world')
print(tree.search(10))        # 'hello'
print(tree.range_query(5, 25)) # [(10, 'hello'), (20, 'world')]

# Visualise
dot = tree.visualize_tree(filename='my_tree')  # saves my_tree.png
```

---

## Dependencies

All listed in `requirements.txt`:

| Package | Version | Purpose |
|---------|---------|---------|
| `graphviz` | 0.20.3 | Python bindings for Graphviz — renders B+ Tree diagrams as PNG |
| `matplotlib` | 3.8.2 | Benchmark plots and performance charts |
| `pandas` | 2.1.4 | Tabular data handling (used in report analysis) |
| `tabulate` | 0.9.0 | Pretty-print tables in notebook output |
| `ipykernel` | 6.29.0 | Jupyter kernel support |
| `jupyter` | 1.0.0 | Notebook server |

> **System dependency (not in requirements.txt):** The `graphviz` Python package is just a wrapper — the actual Graphviz binary (`dot`) must be installed separately. On Colab this is handled automatically by the setup cell via `apt-get install graphviz`.

## Project Structure

```
db_management_system/
├── database/                   ← Core Python package
│   ├── __init__.py             ← Exports: BPlusTree, BPlusTreeNode, BruteForceDB,
│   │                              Table, DatabaseManager, PerformanceAnalyzer
│   ├── bplustree.py            ← B+ Tree implementation (insert, delete, search,
│   │                              range query, visualisation)
│   ├── bruteforce.py           ← O(n) list-based baseline for performance comparison
│   ├── table.py                ← Schema-validated table wrapping BPlusTree
│   ├── db_manager.py           ← Multi-database / multi-table manager
│   └── performance.py          ← Automated benchmarking & memory analysis
├── report.ipynb                ← Full report: demos, visualisations, benchmarks
└── requirements.txt            ← Python dependencies
```

### What each file does

| File | Responsibility |
|------|---------------|
| `bplustree.py` | Core B+ Tree — `BPlusTreeNode` and `BPlusTree` classes. Handles all splits, merges, borrows, leaf linking, and Graphviz visualisation |
| `bruteforce.py` | `BruteForceDB` — a plain Python list storing `(key, value)` tuples. All operations are O(n). Used as the benchmark baseline |
| `table.py` | `Table` — wraps a `BPlusTree` with a named schema (field → Python type), a designated `search_key` (primary key), and type validation on every insert/update |
| `db_manager.py` | `DatabaseManager` — manages `{ db_name → { table_name → Table } }`. Provides create/delete/list at both database and table levels |
| `performance.py` | `PerformanceAnalyzer` — measures insert, search, delete, range query, mixed ops, and memory usage using `time.perf_counter` and `tracemalloc` |
| `report.ipynb` | Jupyter notebook containing live demos of all operations, Graphviz tree visualisations, and all Matplotlib benchmark plots |

---

---

## Tools and External Sources Used

### Development Tools
| Tool | Use |
|------|-----|
| **Python 3.12** | Primary implementation language |
| **Google Colab** | Development and execution environment |
| **Visual Studio Code** | Local code editing |
| **Overleaf** | PDF report writing (LaTeX) |

### Python Standard Library Modules Used
| Module | Use |
|--------|-----|
| `bisect` | Binary search within node key lists (`bisect_left`, `bisect_right`) for O(log order) position finding |
| `math` | `math.ceil()` for computing minimum key count per node |
| `time` | `time.perf_counter()` for high-resolution benchmark timing |
| `tracemalloc` | Peak heap memory tracking during benchmarks |
| `random` | Generating random key sets for benchmarking (`random.seed(42)` for reproducibility) |
| `sys` | `sys.getsizeof()` for memory estimation; path manipulation |

### External Libraries
| Library | Use |
|---------|-----|
| `graphviz` | Rendering B+ Tree structure as HTML-table-labelled Digraph PNG images |
| `matplotlib` | All performance comparison plots (line charts, bar charts, log-scale, memory analysis) |
| `numpy` | Array operations in plotting cells |

### Reference Sources
| Source | What was referenced |
|--------|-------------------|
| [Python `bisect` documentation](https://docs.python.org/3/library/bisect.html) | Correct usage of `bisect_left` vs `bisect_right` for routing and leaf search |
| [Graphviz Python docs](https://graphviz.readthedocs.io/en/stable/) | HTML-like table labels in `Digraph` nodes for styled tree rendering |
| [tracemalloc documentation](https://docs.python.org/3/library/tracemalloc.html) | Peak memory measurement methodology |
| Ramakrishnan & Gehrke, *Database Management Systems* (3rd ed.) | B+ Tree insertion, deletion, and minimum occupancy theory |


