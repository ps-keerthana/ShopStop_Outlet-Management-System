"""
app/routes/orders.py  –  PurchaseOrder CRUD API
"""

from flask import Blueprint, request, jsonify, g
from app.db   import get_db
from app.auth import require_auth, require_role, audit_log

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")


@orders_bp.route("", methods=["GET"])
@require_auth
def list_orders():
    db  = get_db()
    cur = db.cursor()
    status = request.args.get("status")
    if status:
        cur.execute(
            "SELECT po.*, s.SupplierName, e.Name as EmployeeName "
            "FROM PurchaseOrder po "
            "JOIN Supplier s ON po.SupplierID = s.SupplierID "
            "JOIN Employee e ON po.EmployeeID = e.EmployeeID "
            "WHERE po.OrderStatus = %s ORDER BY po.ExpectedDeliveryDate",
            (status,)
        )
    else:
        cur.execute(
            "SELECT po.*, s.SupplierName, e.Name as EmployeeName "
            "FROM PurchaseOrder po "
            "JOIN Supplier s ON po.SupplierID = s.SupplierID "
            "JOIN Employee e ON po.EmployeeID = e.EmployeeID "
            "ORDER BY po.OrderDate DESC LIMIT 100"
        )
    return jsonify({"orders": cur.fetchall()}), 200


@orders_bp.route("/<order_id>", methods=["GET"])
@require_auth
def get_order(order_id):
    db  = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT po.*, s.SupplierName FROM PurchaseOrder po "
        "JOIN Supplier s ON po.SupplierID = s.SupplierID "
        "WHERE po.OrderID = %s", (order_id,)
    )
    order = cur.fetchone()
    if not order:
        return jsonify({"error": "Order not found"}), 404
    cur.execute(
        "SELECT oi.*, p.ProductName FROM OrderItem oi "
        "JOIN Product p ON oi.ProductID = p.ProductID "
        "WHERE oi.OrderID = %s", (order_id,)
    )
    order["items"] = cur.fetchall()
    return jsonify(order), 200


@orders_bp.route("/<order_id>/status", methods=["PUT"])
@require_auth
@require_role("admin")
def update_order_status(order_id):
    data   = request.get_json(silent=True) or {}
    status = data.get("OrderStatus")
    valid  = {"Pending", "Confirmed", "Delivered", "Cancelled"}
    if status not in valid:
        return jsonify({"error": f"Status must be one of {valid}"}), 400

    db  = get_db()
    cur = db.cursor()
    try:
        extra = ""
        params = [status]
        if status == "Delivered":
            from datetime import date
            extra = ", ActualDeliveryDate = %s"
            params.append(str(date.today()))
        params.append(order_id)
        cur.execute(
            f"UPDATE PurchaseOrder SET OrderStatus = %s{extra} WHERE OrderID = %s",
            params
        )
        if cur.rowcount == 0:
            return jsonify({"error": "Order not found"}), 404
        db.commit()
        u = g.current_user
        audit_log(u["username"], u["role"], f"UPDATE_STATUS_{status}", "PurchaseOrder", order_id)
        return jsonify({"message": f"Order status updated to {status}"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
