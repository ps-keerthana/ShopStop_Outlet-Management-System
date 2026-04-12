"""
app/routes/employees.py  -  Employee API with salary management
Full CRUD: GET (list), POST (add), PUT (general fields), PUT (salary), DELETE
RBAC: admins full access; regular users can view their own portfolio only.
"""
from flask import Blueprint, request, jsonify, g
from app.db   import get_db
from app.auth import require_auth, require_role, audit_log

employees_bp = Blueprint("employees", __name__, url_prefix="/api/employees")


# ── GET /api/employees  (list) ────────────────────────────────────────
@employees_bp.route("", methods=["GET"])
@require_auth
def list_employees():
    db  = get_db()
    cur = db.cursor()
    if g.current_user["role"] == "admin":
        cur.execute(
            "SELECT e.EmployeeID, e.Name, e.Position, e.Salary, "
            "e.HireDate, e.ShiftTiming, e.ContactNumber, e.Email, "
            "m.Name as ManagerName "
            "FROM Employee e "
            "LEFT JOIN Employee m ON e.ManagerID = m.EmployeeID "
            "ORDER BY e.Salary DESC"
        )
    else:
        # Regular users: salary column hidden
        cur.execute(
            "SELECT e.EmployeeID, e.Name, e.Position, "
            "e.HireDate, e.ShiftTiming, "
            "m.Name as ManagerName "
            "FROM Employee e "
            "LEFT JOIN Employee m ON e.ManagerID = m.EmployeeID "
            "ORDER BY e.Name"
        )
    rows = cur.fetchall()
    return jsonify({"employees": rows, "count": len(rows)}), 200


# ── GET /api/employees/salary-summary  (admin only) ───────────────────
@employees_bp.route("/salary-summary", methods=["GET"])
@require_auth
@require_role("admin")
def salary_summary():
    db  = get_db()
    cur = db.cursor()
    cur.execute("SELECT SUM(Salary) as total, COUNT(*) as count FROM Employee")
    totals = cur.fetchone()
    cur.execute(
        "SELECT Position, COUNT(*) as count, "
        "SUM(Salary) as total_salary, "
        "AVG(Salary) as avg_salary, "
        "MIN(Salary) as min_salary, "
        "MAX(Salary) as max_salary "
        "FROM Employee GROUP BY Position ORDER BY total_salary DESC"
    )
    by_position = cur.fetchall()
    cur.execute(
        "SELECT ShiftTiming, COUNT(*) as count, SUM(Salary) as total_salary "
        "FROM Employee GROUP BY ShiftTiming"
    )
    by_shift = cur.fetchall()
    return jsonify({
        "total_payroll":   float(totals["total"] or 0),
        "total_employees": totals["count"],
        "by_position":     by_position,
        "by_shift":        by_shift,
    }), 200


# ── GET /api/employees/me/employee-id  ────────────────────────────────
@employees_bp.route("/me/employee-id", methods=["GET"])
@require_auth
def my_employee_id():
    db  = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT EmployeeID FROM UserCredentials WHERE UserID = %s",
        (g.current_user["user_id"],)
    )
    row = cur.fetchone()
    if not row or not row["EmployeeID"]:
        return jsonify({"employee_id": None}), 200
    return jsonify({"employee_id": row["EmployeeID"]}), 200


# ── POST /api/employees  (admin only) ────────────────────────────────
@employees_bp.route("", methods=["POST"])
@require_auth
@require_role("admin")
def add_employee():
    """Add a new employee."""
    data = request.get_json(silent=True) or {}
    required = ["EmployeeID", "Name", "Email", "ContactNumber",
                "Position", "Salary", "HireDate", "ShiftTiming"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400
    db  = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "INSERT INTO Employee (EmployeeID, Name, Email, ContactNumber, "
            "Position, Salary, HireDate, ShiftTiming, ManagerID) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (data["EmployeeID"], data["Name"], data["Email"],
             data["ContactNumber"], data["Position"], float(data["Salary"]),
             data["HireDate"], data["ShiftTiming"],
             data.get("ManagerID") or None)
        )
        db.commit()
        u = g.current_user
        audit_log(u["username"], u["role"], "INSERT", "Employee", data["EmployeeID"])
        return jsonify({"message": "Employee added successfully"}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# ── PUT /api/employees/<id>  (admin only) ────────────────────────────
@employees_bp.route("/<emp_id>", methods=["PUT"])
@require_auth
@require_role("admin")
def update_employee(emp_id):
    """
    Update general employee fields (admin only).
    Salary has its own dedicated endpoint /salary for clarity.
    Allowed: Name, Email, ContactNumber, Position, ShiftTiming, ManagerID.
    """
    data = request.get_json(silent=True) or {}

    allowed = {"Name", "Email", "ContactNumber", "Position", "ShiftTiming", "ManagerID"}
    updates = {k: v for k, v in data.items() if k in allowed}

    if not updates:
        return jsonify({"error": f"No valid fields to update. Allowed: {sorted(allowed)}"}), 400

    db  = get_db()
    cur = db.cursor()
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values     = list(updates.values()) + [emp_id]
    try:
        cur.execute(f"UPDATE Employee SET {set_clause} WHERE EmployeeID = %s", values)
        if cur.rowcount == 0:
            return jsonify({"error": "Employee not found"}), 404
        db.commit()
        u = g.current_user
        audit_log(u["username"], u["role"], "UPDATE", "Employee", emp_id)
        return jsonify({"message": f"Employee {emp_id} updated successfully"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# ── PUT /api/employees/<id>/salary  (admin only) ──────────────────────
@employees_bp.route("/<emp_id>/salary", methods=["PUT"])
@require_auth
@require_role("admin")
def update_salary(emp_id):
    """Update salary for a specific employee."""
    data   = request.get_json(silent=True) or {}
    salary = data.get("Salary")
    if salary is None or float(salary) <= 0:
        return jsonify({"error": "Salary must be a positive number"}), 400
    db  = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "UPDATE Employee SET Salary = %s WHERE EmployeeID = %s",
            (float(salary), emp_id)
        )
        if cur.rowcount == 0:
            return jsonify({"error": "Employee not found"}), 404
        db.commit()
        u = g.current_user
        audit_log(u["username"], u["role"], "UPDATE_SALARY", "Employee", emp_id)
        return jsonify({"message": f"Salary updated for {emp_id}"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# ── DELETE /api/employees/<id>  (admin only) ──────────────────────────
@employees_bp.route("/<emp_id>", methods=["DELETE"])
@require_auth
@require_role("admin")
def delete_employee(emp_id):
    """
    Delete an employee. The corresponding UserCredentials row is removed
    automatically via ON DELETE CASCADE on the EmployeeID foreign key,
    maintaining strict data integrity.
    """
    db  = get_db()
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM Employee WHERE EmployeeID = %s", (emp_id,))
        if cur.rowcount == 0:
            return jsonify({"error": "Employee not found"}), 404
        db.commit()
        u = g.current_user
        audit_log(u["username"], u["role"], "DELETE", "Employee", emp_id)
        return jsonify({"message": f"Employee {emp_id} and credentials deleted"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# ── GET /api/employees/<id>/portfolio  ────────────────────────────────
@employees_bp.route("/<employee_id>/portfolio", methods=["GET"])
@require_auth
def get_employee_portfolio(employee_id):
    """
    Admin: can view any employee's portfolio.
    Regular user: can only view their own portfolio (matched via UserCredentials.EmployeeID).
    This mirrors the same self-view pattern used in members.py.
    """
    u = g.current_user
    if u["role"] != "admin":
        # Look up which EmployeeID belongs to this logged-in user
        db  = get_db()
        cur = db.cursor()
        cur.execute(
            "SELECT EmployeeID FROM UserCredentials WHERE UserID = %s",
            (u["user_id"],)
        )
        row = cur.fetchone()
        if not row or row["EmployeeID"] != employee_id:
            audit_log(u["username"], u["role"], "FORBIDDEN",
                      record_id=f"/api/employees/{employee_id}/portfolio",
                      status="DENIED")
            return jsonify({"error": "Forbidden – can only view your own portfolio"}), 403

    db  = get_db()
    cur = db.cursor()

    # Basic employee info
    cur.execute("""
        SELECT e.*, m.Name AS ManagerName
        FROM Employee e
        LEFT JOIN Employee m ON e.ManagerID = m.EmployeeID
        WHERE e.EmployeeID = %s
    """, (employee_id,))
    employee = cur.fetchone()
    if not employee:
        return jsonify({"error": "Employee not found"}), 404

    # Sales processed by this employee
    cur.execute("""
        SELECT COUNT(*) as total_sales,
               SUM(FinalAmount) as total_revenue,
               AVG(FinalAmount) as avg_sale_value,
               MAX(SaleDate) as last_sale
        FROM Sale WHERE EmployeeID = %s
    """, (employee_id,))
    sales_summary = cur.fetchone()

    # Top products sold by this employee
    cur.execute("""
        SELECT p.ProductName, SUM(si.Quantity) as total_qty,
               SUM(si.Subtotal) as total_revenue
        FROM Sale s
        JOIN SaleItem si ON s.SaleID = si.SaleID
        JOIN Product p  ON si.ProductID = p.ProductID
        WHERE s.EmployeeID = %s
        GROUP BY p.ProductID ORDER BY total_revenue DESC LIMIT 5
    """, (employee_id,))
    top_products = cur.fetchall()

    # Recent sales handled
    cur.execute("""
        SELECT SaleID, SaleDate, FinalAmount, PaymentMethod
        FROM Sale WHERE EmployeeID = %s
        ORDER BY SaleDate DESC LIMIT 5
    """, (employee_id,))
    recent_sales = cur.fetchall()

    return jsonify({
        "employee":      employee,
        "sales_summary": sales_summary,
        "top_products":  top_products,
        "recent_sales":  recent_sales,
        "type":          "employee"
    }), 200
