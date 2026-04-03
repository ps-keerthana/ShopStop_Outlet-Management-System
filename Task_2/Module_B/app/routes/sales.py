"""
app/routes/sales.py  -  Sales CRUD API
OrderType: 'In-Store' (cashier) | 'Online' (customer cart checkout)
"""

from flask import Blueprint, request, jsonify, g
from app.db   import get_db
from app.auth import require_auth, require_role, audit_log

sales_bp = Blueprint("sales", __name__, url_prefix="/api/sales")


@sales_bp.route("", methods=["GET"])
@require_auth
def list_sales():
    db  = get_db()
    cur = db.cursor()
    date_from  = request.args.get("from")
    date_to    = request.args.get("to")
    member_id  = request.args.get("member")
    order_type = request.args.get("order_type")   # 'In-Store' | 'Online' | '' = all

    sql    = ("SELECT s.*, m.Name as MemberName, e.Name as EmployeeName "
              "FROM Sale s "
              "LEFT JOIN Member   m ON s.MemberID   = m.MemberID "
              "LEFT JOIN Employee e ON s.EmployeeID = e.EmployeeID ")
    params = []
    where  = []

    if date_from:  where.append("s.SaleDate >= %s");  params.append(date_from)
    if date_to:    where.append("s.SaleDate <= %s");  params.append(date_to)
    if member_id:  where.append("s.MemberID = %s");   params.append(member_id)
    if order_type: where.append("s.OrderType = %s");  params.append(order_type)

    if where:
        sql += "WHERE " + " AND ".join(where)
    sql += " ORDER BY s.SaleDate DESC LIMIT 200"
    cur.execute(sql, params)
    return jsonify({"sales": cur.fetchall()}), 200


@sales_bp.route("/<sale_id>", methods=["GET"])
@require_auth
def get_sale(sale_id):
    db  = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT s.*, m.Name as MemberName, e.Name as EmployeeName "
        "FROM Sale s "
        "LEFT JOIN Member   m ON s.MemberID   = m.MemberID "
        "JOIN    Employee e ON s.EmployeeID = e.EmployeeID "
        "WHERE s.SaleID = %s", (sale_id,)
    )
    sale = cur.fetchone()
    if not sale:
        return jsonify({"error": "Sale not found"}), 404
    cur.execute(
        "SELECT si.*, p.ProductName FROM SaleItem si "
        "JOIN Product p ON si.ProductID = p.ProductID "
        "WHERE si.SaleID = %s", (sale_id,)
    )
    sale["items"] = cur.fetchall()
    return jsonify(sale), 200


@sales_bp.route("", methods=["POST"])
@require_auth
@require_role("admin")
def create_sale():
    data = request.get_json(silent=True) or {}
    required = ["SaleID", "EmployeeID", "SaleDate",
                "TotalAmount", "DiscountAmount", "FinalAmount",
                "PaymentMethod", "items"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing: {missing}"}), 400
    db  = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "INSERT INTO Sale (SaleID, MemberID, EmployeeID, SaleDate, "
            "TotalAmount, DiscountAmount, FinalAmount, PaymentMethod, OrderType) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'In-Store')",
            (data["SaleID"], data.get("MemberID"), data["EmployeeID"],
             data["SaleDate"], data["TotalAmount"], data["DiscountAmount"],
             data["FinalAmount"], data["PaymentMethod"])
        )
        for item in data["items"]:
            cur.execute(
                "INSERT INTO SaleItem (SaleItemID, SaleID, ProductID, "
                "Quantity, UnitPrice, Subtotal) VALUES (%s,%s,%s,%s,%s,%s)",
                (item["SaleItemID"], data["SaleID"], item["ProductID"],
                 item["Quantity"], item["UnitPrice"], item["Subtotal"])
            )
        db.commit()
        u = g.current_user
        audit_log(u["username"], u["role"], "INSERT", "Sale", data["SaleID"])
        return jsonify({"message": "Sale created"}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


@sales_bp.route("/<sale_id>", methods=["DELETE"])
@require_auth
@require_role("admin")
def delete_sale(sale_id):
    db  = get_db()
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM Sale WHERE SaleID = %s", (sale_id,))
        if cur.rowcount == 0:
            return jsonify({"error": "Sale not found"}), 404
        db.commit()
        u = g.current_user
        audit_log(u["username"], u["role"], "DELETE", "Sale", sale_id)
        return jsonify({"message": "Sale deleted"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


@sales_bp.route("/checkout", methods=["POST"])
@require_auth
def checkout():
    """Customer places an online order via cart - OrderType = Online."""
    data = request.get_json(silent=True) or {}
    required = ["items", "payment_method"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing: {missing}"}), 400
    items = data["items"]
    if not items:
        return jsonify({"error": "Cart is empty"}), 400
    db  = get_db()
    cur = db.cursor()
    try:
        total_amount = 0
        enriched = []
        for item in items:
            cur.execute(
                "SELECT ProductID, ProductName, Price, StockQuantity "
                "FROM Product WHERE ProductID = %s", (item["product_id"],)
            )
            prod = cur.fetchone()
            if not prod:
                return jsonify({"error": f"Product {item['product_id']} not found"}), 404
            if prod["StockQuantity"] < item["qty"]:
                return jsonify({"error": f"Insufficient stock for {prod['ProductName']}"}), 400
            subtotal = float(prod["Price"]) * item["qty"]
            total_amount += subtotal
            enriched.append({"product_id": prod["ProductID"], "product_name": prod["ProductName"],
                              "unit_price": float(prod["Price"]), "qty": item["qty"], "subtotal": subtotal})

        member_id = data.get("member_id")
        if not member_id:
            cur.execute("SELECT MemberID FROM UserCredentials WHERE UserID = %s",
                        (g.current_user["user_id"],))
            row = cur.fetchone()
            if row:
                member_id = row["MemberID"]

        cur.execute("SELECT EmployeeID FROM Employee LIMIT 1")
        emp = cur.fetchone()
        if not emp:
            return jsonify({"error": "No employee found"}), 400
        employee_id = emp["EmployeeID"]

        cur.execute("SELECT COUNT(*) as cnt FROM Sale")
        cnt = cur.fetchone()["cnt"]
        sale_id = f"SAL{str(cnt + 1).zfill(3)}"

        discount     = 0
        final_amount = total_amount - discount

        # KEY CHANGE: OrderType = 'Online'
        cur.execute(
            "INSERT INTO Sale (SaleID, MemberID, EmployeeID, SaleDate, "
            "TotalAmount, DiscountAmount, FinalAmount, PaymentMethod, OrderType) "
            "VALUES (%s, %s, %s, NOW(), %s, %s, %s, %s, 'Online')",
            (sale_id, member_id, employee_id,
             total_amount, discount, final_amount, data["payment_method"])
        )

        for i, item in enumerate(enriched):
            sale_item_id = f"{sale_id}-{str(i+1).zfill(2)}"
            cur.execute(
                "INSERT INTO SaleItem (SaleItemID, SaleID, ProductID, Quantity, UnitPrice, Subtotal) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (sale_item_id, sale_id, item["product_id"],
                 item["qty"], item["unit_price"], item["subtotal"])
            )
            cur.execute(
                "UPDATE Product SET StockQuantity = StockQuantity - %s WHERE ProductID = %s",
                (item["qty"], item["product_id"])
            )

        if member_id:
            points_earned = int(final_amount // 10)
            cur.execute(
                "UPDATE Member SET LoyaltyPoints = LoyaltyPoints + %s WHERE MemberID = %s",
                (points_earned, member_id)
            )

        db.commit()
        u = g.current_user
        audit_log(u["username"], u["role"], "ONLINE_CHECKOUT", "Sale", sale_id)
        return jsonify({"message": "Order placed successfully!", "sale_id": sale_id,
                        "total_amount": total_amount, "final_amount": final_amount,
                        "items_count": len(enriched)}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# ── PUT /api/sales/<id>  (admin only) ─────────────────────────────────
@sales_bp.route("/<sale_id>", methods=["PUT"])
@require_auth
@require_role("admin")
def update_sale(sale_id):
    """
    Update header-level fields of an existing sale (e.g. PaymentMethod,
    DiscountAmount, FinalAmount).  Line-items are not editable here —
    delete and recreate the sale for item-level changes.
    """
    data = request.get_json(silent=True) or {}
    allowed = {"PaymentMethod", "DiscountAmount", "FinalAmount",
               "TotalAmount", "MemberID"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    db  = get_db()
    cur = db.cursor()
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values     = list(updates.values()) + [sale_id]
    try:
        cur.execute(f"UPDATE Sale SET {set_clause} WHERE SaleID = %s", values)
        if cur.rowcount == 0:
            return jsonify({"error": "Sale not found"}), 404
        db.commit()
        u = g.current_user
        audit_log(u["username"], u["role"], "UPDATE", "Sale", sale_id)
        return jsonify({"message": f"Sale {sale_id} updated"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
