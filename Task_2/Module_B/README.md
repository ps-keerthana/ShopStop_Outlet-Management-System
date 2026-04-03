# Module B — ShopStop Outlet Management System
### Local Web Application with REST APIs, RBAC, and SQL Indexing
> CS 432 – Databases | Assignment 2

A fully functional local web application built on top of the ShopStop retail database. It includes a JWT-based login system, role-based access control, full CRUD APIs, a member portfolio UI, and SQL index benchmarking.

---

## Folder Structure

```
Module_B/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── auth.py              # JWT generation, @require_auth, @require_role decorators
│   ├── db.py                # MySQL connection helper
│   ├── routes/
│   │   ├── auth.py          # /login, /isAuth, / endpoints
│   │   ├── members.py       # Member CRUD + portfolio
│   │   ├── products.py      # Product CRUD
│   │   ├── sales.py         # Sales CRUD + online checkout
│   │   ├── employees.py     # Employee CRUD + salary management
│   │   ├── orders.py        # Purchase order management
│   │   └── ui.py            # Serves HTML pages
│   └── templates/
│       ├── login.html       # Login page
│       ├── dashboard.html   # Main app dashboard
│       └── portfolio.html   # Member portfolio page
├── sql/
│   └── schema_moduleB.sql   # Core tables (UserCredentials, GroupMapping) + SQL indexes
├── logs/
│   └── audit.log            # Auto-generated security audit log
├── shopstop.sql             # Main database with all tables and sample data
├── run.py                   # Flask app entry point — run this to start the server
├── report.ipynb             # SQL index benchmarking notebook
├── query_benchmark.csv      # Saved benchmark results
├── index_benchmark.png      # Benchmark chart
├── Module_B_Report.pdf      # Full report
└── requirements.txt         # Python dependencies
```

---

## Prerequisites

- Python 3.8 or higher
- MySQL 8.0 or higher
- pip

---

## Setup and Running

### Step 1 — Install Python packages

```bash
cd Module_B
pip install -r requirements.txt
```

### Step 2 — Load the database into MySQL

```bash
mysql -u root -p
```

Then inside MySQL:

```sql
source /full/path/to/Module_B/shopstop.sql
source /full/path/to/Module_B/sql/schema_moduleB.sql
```

> **Windows example:**
> ```sql
> source C:/Users/YourName/Module_B/shopstop.sql
> source C:/Users/YourName/Module_B/sql/schema_moduleB.sql
> ```

### Step 3 — Update your MySQL password

Open `run.py` and change line 10:

```python
MYSQL_PASSWORD = "your_mysql_password_here"
```

Also update it in `report.ipynb` Cell 2 (DB_CONFIG section).

### Step 4 — Start the Flask server

```bash
python run.py
```

You should see:

```
=======================================================
  ShopStop API  -  CS 432 Assignment 2 Module B
=======================================================
  DB  : mysql://root@localhost/ShopStop
  URL : http://localhost:5000/login-page
=======================================================
```

### Step 5 — Initialize passwords (first time only)

Open a second terminal and run:

```bash
curl -X POST http://127.0.0.1:5000/init-passwords
```

Only needs to be done once after a fresh database load.

### Step 6 — Open the app

```
http://localhost:5000/login-page
```

---

## Login Credentials

| Username | Password | Role | Linked to |
|----------|----------|------|-----------|
| admin | admin123 | Admin — full access | Employee EMP001 |
| rajesh | user123 | Regular user | Member MEM001 |
| priya | user123 | Regular user | Member MEM002 |
| amit | user123 | Regular user | Member MEM003 |
| sneha | user123 | Regular user | Member MEM004 |
| vikram | user123 | Regular user | Member MEM005 |

---

## API Endpoints

All endpoints except `/`, `/login`, and `/login-page` require a valid JWT token:
```
Authorization: Bearer <your_token>
```

### Authentication
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/` | Welcome message | No |
| POST | `/login` | Login and get JWT token | No |
| GET | `/isAuth` | Check if session is valid | Yes |

### Members `/api/members`
| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/members` | Admin only |
| GET | `/api/members/<id>` | Admin or own record |
| GET | `/api/members/<id>/portfolio` | Admin or own record |
| POST | `/api/members` | Admin only |
| PUT | `/api/members/<id>` | Admin or own record |
| DELETE | `/api/members/<id>` | Admin only |

### Products `/api/products`
| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/products` | All users |
| GET | `/api/products/<id>` | All users |
| POST | `/api/products` | Admin only |
| PUT | `/api/products/<id>` | Admin only |
| DELETE | `/api/products/<id>` | Admin only |

### Sales `/api/sales`
| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/sales` | All users |
| GET | `/api/sales/<id>` | All users |
| POST | `/api/sales` | Admin only |
| POST | `/api/sales/checkout` | All users |
| PUT | `/api/sales/<id>` | Admin only |
| DELETE | `/api/sales/<id>` | Admin only |

### Employees `/api/employees`
| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/employees` | All users (salary hidden for regular users) |
| POST | `/api/employees` | Admin only |
| PUT | `/api/employees/<id>/salary` | Admin only |
| DELETE | `/api/employees/<id>` | Admin only |
| GET | `/api/employees/<id>/portfolio` | Admin or own record |

### Purchase Orders `/api/orders`
| Method | Endpoint | Access |
|--------|----------|--------|
| GET | `/api/orders` | All users |
| GET | `/api/orders/<id>` | All users |
| PUT | `/api/orders/<id>/status` | Admin only |

---

## Role-Based Access Control

**Admin** gets a full management dashboard:
- Overview, Products, Members, Employees
- Billing Counter for in-store sales
- Sales History and Purchase Orders

**Regular User** gets a personal shopping interface:
- My Dashboard, Browse & Shop
- View Cart and Buy, My Purchases
- My Profile and Portfolio

Admin sections are completely hidden from regular users in the UI. Direct API calls to admin endpoints return `403 Forbidden`.

---

## Running the Benchmark Notebook

`report.ipynb` measures query performance before and after SQL indexing. Flask does **not** need to be running — the notebook connects directly to MySQL.

Open in Jupyter or VS Code and run all cells. Make sure the password is updated in Cell 2 first.

---

## Security Audit Log

Every API operation is logged automatically to `logs/audit.log`:

```
[2026-03-22 02:00:06] user=rajesh role=user action=LOGIN table=- id=- status=SUCCESS
[2026-03-22 02:00:55] user=MEM003 role=unknown action=LOGIN table=- id=- status=FAILED
[2026-03-21 05:06:00] user=admin role=admin action=UPDATE_SALARY table=Employee id=EMP014 status=SUCCESS
```

Direct database changes that bypass the API will not appear here, making them detectable as unauthorized.

---

## Troubleshooting

**"Unknown column 'OrderType'"**
```sql
USE ShopStop;
ALTER TABLE Sale ADD COLUMN OrderType ENUM('In-Store','Online') DEFAULT 'In-Store';
```

**"Passwords not initialised"**
```bash
curl -X POST http://127.0.0.1:5000/init-passwords
```

**Port 5000 already in use**

Change the port in `run.py`:
```python
app.run(host="0.0.0.0", port=5001, debug=True)
```
Then go to `http://localhost:5001/login-page`

**MySQL server not running (Windows)**

Task Manager → Services tab → find MySQL80 → right click → Start

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, Flask |
| Database | MySQL 8.0 |
| Authentication | PyJWT (HS256), bcrypt |
| Frontend | HTML, CSS, JavaScript (vanilla) |
| Benchmarking | Jupyter Notebook, pymysql, matplotlib, pandas |

---

> **Note:** This application runs locally only. It requires a running MySQL server and Python backend and cannot be deployed on GitHub Pages.
