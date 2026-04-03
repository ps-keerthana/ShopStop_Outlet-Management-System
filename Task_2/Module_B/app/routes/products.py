"""
app/routes/products.py  –  CRUD for Product table
GET (all users) | POST, PUT, DELETE (admin only)
"""

from flask import Blueprint, request, jsonify, g
from app.db   import get_db
from app.auth import require_auth, require_role, audit_log

products_bp = Blueprint("products", __name__, url_prefix="/api/products")


# ── GET /api/products  (list / filter) ───────────────────────────────
@products_bp.route("", methods=["GET"])
@require_auth
def list_products():
    db  = get_db()
    cur = db.cursor()

    category = request.args.get("category")
    supplier = request.args.get("supplier")
    low_stock = request.args.get("low_stock")       # ?low_stock=1

    sql    = "SELECT p.*, c.CategoryName, s.SupplierName FROM Product p "
    sql   += "JOIN Category c ON p.CategoryID = c.CategoryID "
    sql   += "JOIN Supplier s ON p.SupplierID = s.SupplierID "
    params = []
    where  = []

    if category:
        where.append("p.CategoryID = %s");  params.append(category)
    if supplier:
        where.append("p.SupplierID = %s");  params.append(supplier)
    if low_stock:
        where.append("p.StockQuantity < p.ReorderLevel")

    if where:
        sql += "WHERE " + " AND ".join(where)

    sql += " ORDER BY p.ProductName"
    cur.execute(sql, params)
    rows = cur.fetchall()
    return jsonify({"products": rows, "count": len(rows)}), 200


# ── GET /api/products/<id>  (single) ─────────────────────────────────
@products_bp.route("/<product_id>", methods=["GET"])
@require_auth
def get_product(product_id):
    db  = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT p.*, c.CategoryName, s.SupplierName FROM Product p "
        "JOIN Category c ON p.CategoryID = c.CategoryID "
        "JOIN Supplier s ON p.SupplierID = s.SupplierID "
        "WHERE p.ProductID = %s",
        (product_id,)
    )
    row = cur.fetchone()
    if not row:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(row), 200


# ── POST /api/products  (admin only) ─────────────────────────────────
@products_bp.route("", methods=["POST"])
@require_auth
@require_role("admin")
def create_product():
    data = request.get_json(silent=True) or {}
    required = ["ProductID", "ProductName", "CategoryID", "SupplierID",
                "Price", "StockQuantity", "ReorderLevel", "ManufactureDate"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    db  = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "INSERT INTO Product (ProductID, ProductName, CategoryID, SupplierID, "
            "Price, StockQuantity, ReorderLevel, ExpiryDate, ManufactureDate, Barcode) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (data["ProductID"], data["ProductName"], data["CategoryID"],
             data["SupplierID"], data["Price"], data["StockQuantity"],
             data["ReorderLevel"], data.get("ExpiryDate"),
             data["ManufactureDate"], data.get("Barcode"))
        )
        db.commit()
        u = g.current_user
        audit_log(u["username"], u["role"], "INSERT", "Product", data["ProductID"])
        return jsonify({"message": "Product created", "ProductID": data["ProductID"]}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# ── PUT /api/products/<id>  (admin only) ─────────────────────────────
@products_bp.route("/<product_id>", methods=["PUT"])
@require_auth
@require_role("admin")
def update_product(product_id):
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "No update data provided"}), 400

    allowed = {"ProductName", "Price", "StockQuantity", "ReorderLevel",
               "ExpiryDate", "CategoryID", "SupplierID", "Barcode"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    db  = get_db()
    cur = db.cursor()
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values     = list(updates.values()) + [product_id]

    try:
        cur.execute(f"UPDATE Product SET {set_clause} WHERE ProductID = %s", values)
        if cur.rowcount == 0:
            return jsonify({"error": "Product not found"}), 404
        db.commit()
        u = g.current_user
        audit_log(u["username"], u["role"], "UPDATE", "Product", product_id)
        return jsonify({"message": "Product updated"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# ── DELETE /api/products/<id>  (admin only) ───────────────────────────
@products_bp.route("/<product_id>", methods=["DELETE"])
@require_auth
@require_role("admin")
def delete_product(product_id):
    db  = get_db()
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM Product WHERE ProductID = %s", (product_id,))
        if cur.rowcount == 0:
            return jsonify({"error": "Product not found"}), 404
        db.commit()
        u = g.current_user
        audit_log(u["username"], u["role"], "DELETE", "Product", product_id)
        return jsonify({"message": "Product deleted"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
