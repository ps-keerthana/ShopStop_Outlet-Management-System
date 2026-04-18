"""
app/routes/sales.py  –  Sales API with Shard-Aware Routing
CS 432 Assignment 4 | Group: Nexus

Changes from Assignment 3:
  - Sale and SaleItem reads/writes go to remote shards
  - Single MemberID lookup → 1 shard
  - Date-range queries → fan-out to all 3 shards, merge
"""

from flask import Blueprint, request, jsonify, g
from app.shard_router import get_shard, get_all_shards, get_shard_id
from app.auth         import require_auth, require_role, audit_log

sales_bp = Blueprint("sales", __name__, url_prefix="/api/sales")


# ── GET /api/sales  ───────────────────────────────────────────────────
# If member_id is given → single shard.  Otherwise → all shards.
@sales_bp.route("", methods=["GET"])
@require_auth
def list_sales():
    date_from  = request.args.get("from")
    date_to    = request.args.get("to")
    member_id  = request.args.get("member")
    order_type = request.args.get("order_type")

    # Build the WHERE clause
    where, params = [], []
    if date_from:  where.append("SaleDate >= %s");  params.append(date_from)
    if date_to:    where.append("SaleDate <= %s");  params.append(date_to)
    if member_id:  where.append("MemberID = %s");   params.append(member_id)
    if order_type: where.append("OrderType = %s");  params.append(order_type)

    sql = "SELECT * FROM Sale"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY SaleDate DESC LIMIT 200"

    results = []

    if member_id:
        # ── SINGLE-SHARD LOOKUP ──────────────────────────────────────
        # We know exactly which shard this member is on
        conn = get_shard(member_id)
        cur  = conn.cursor()
        cur.execute(sql, params)
        results = cur.fetchall()
    else:
        # ── RANGE / UNFILTERED QUERY: fan-out to all 3 shards ────────
        shard_errors = []
        for i, conn, conn_err in get_all_shards():
            if conn is None:
                shard_errors.append({"shard": i, "error": conn_err})
                continue
            try:
                cur = conn.cursor()
                cur.execute(sql, params)
                results.extend(cur.fetchall())
            except Exception as e:
                shard_errors.append({"shard": i, "error": str(e)})
        # Re-sort merged results
        results.sort(key=lambda r: str(r.get("SaleDate", "")), reverse=True)
        results = results[:200]  # cap at 200 after merge
        resp = {"sales": results, "total": len(results)}
        if shard_errors:
            resp["degraded"] = True
            resp["shard_errors"] = shard_errors
        return jsonify(resp), 200

    return jsonify({"sales": results, "total": len(results)}), 200


# ── GET /api/sales/<sale_id>  ─────────────────────────────────────────
# sale_id alone doesn't tell us the shard; we need to search all shards.
@sales_bp.route("/<sale_id>", methods=["GET"])
@require_auth
def get_sale(sale_id):
    # Fan-out: check every shard for this SaleID
    for shard_id, conn, conn_err in get_all_shards():
        if conn is None:
            continue  # shard unreachable, try the next one
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM Sale WHERE SaleID = %s", (sale_id,))
            sale = cur.fetchone()
            if sale:
                cur.execute(
                    "SELECT * FROM SaleItem WHERE SaleID = %s", (sale_id,)
                )
                sale["items"]    = cur.fetchall()
                sale["_shard_id"] = sale.get("shard_id")
                return jsonify(sale), 200
        except Exception:
            continue  # shard unreachable, try the next one

    return jsonify({"error": "Sale not found"}), 404


# ── POST /api/sales  ──────────────────────────────────────────────────
@sales_bp.route("", methods=["POST"])
@require_auth
def create_sale():
    data = request.get_json(silent=True) or {}
    required = ["SaleID", "EmployeeID", "SaleDate", "TotalAmount",
                "FinalAmount", "PaymentMethod"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing: {missing}"}), 400

    member_id = data.get("MemberID")  # may be None for guest
    sid       = get_shard_id(member_id)
    conn      = get_shard(member_id)   # ← routed insert
    cur       = conn.cursor()

    try:
        cur.execute(
            """INSERT INTO Sale
               (SaleID, MemberID, EmployeeID, SaleDate, TotalAmount,
                DiscountAmount, FinalAmount, PaymentMethod, OrderType, shard_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (data["SaleID"], member_id, data["EmployeeID"],
             data["SaleDate"], data["TotalAmount"],
             data.get("DiscountAmount", 0), data["FinalAmount"],
             data["PaymentMethod"], data.get("OrderType", "In-Store"), sid)
        )

        # Insert SaleItems into the same shard
        for item in data.get("items", []):
            cur.execute(
                """INSERT INTO SaleItem
                   (SaleItemID, SaleID, ProductID, Quantity,
                    UnitPrice, Subtotal, shard_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (item["SaleItemID"], data["SaleID"], item["ProductID"],
                 item["Quantity"], item["UnitPrice"], item["Subtotal"], sid)
            )

        conn.commit()
        u = g.current_user
        audit_log(u["username"], u["role"], "INSERT", "Sale", data["SaleID"])
        return jsonify({"message": "Sale created", "shard_id": sid}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400


# ── GET /api/sales/range  ─────────────────────────────────────────────
# Explicit range query that fans out across all shards and merges results
@sales_bp.route("/range", methods=["GET"])
@require_auth
def sales_range():
    """
    Date-range query across all shards.
    Usage: GET /api/sales/range?from=2024-01-01&to=2024-06-30
    This demonstrates multi-shard range query with merge.
    """
    date_from = request.args.get("from")
    date_to   = request.args.get("to")

    if not date_from or not date_to:
        return jsonify({"error": "Both 'from' and 'to' date params required"}), 400

    all_results  = []
    shard_counts = {}
    shard_errors = []

    # Fan-out: query every shard for the date range
    for i, conn, conn_err in get_all_shards():
        if conn is None:
            shard_counts[f"shard_{i}"] = 0
            shard_errors.append({"shard": i, "error": conn_err})
            continue
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM Sale WHERE SaleDate >= %s AND SaleDate <= %s "
                "ORDER BY SaleDate",
                (date_from, date_to + " 23:59:59")
            )
            rows = cur.fetchall()
            shard_counts[f"shard_{i}"] = len(rows)
            all_results.extend(rows)
        except Exception as e:
            shard_counts[f"shard_{i}"] = 0
            shard_errors.append({"shard": i, "error": str(e)})

    # Merge: sort by date
    all_results.sort(key=lambda r: str(r.get("SaleDate", "")))

    resp = {
        "sales":        all_results,
        "total":        len(all_results),
        "shard_counts": shard_counts,
        "date_range":   {"from": date_from, "to": date_to},
    }
    if shard_errors:
        resp["degraded"] = True
        resp["shard_errors"] = shard_errors
    return jsonify(resp), 200