"""
app/routes/members.py  –  Member CRUD with Shard-Aware Routing
CS 432 Assignment 4 | Group: Nexus

Changes from Assignment 3:
  - All Member reads/writes go to the correct REMOTE shard
  - get_shard(member_id)  → single-key lookup  → 1 shard
  - get_all_shards()      → listing / range query → all 3 shards, merge results
"""

from flask import Blueprint, request, jsonify, g
from app.db           import get_db          # local DB (UserCredentials, etc.)
from app.shard_router import get_shard, get_all_shards, get_shard_id, NUM_SHARDS
from app.auth         import require_auth, require_role, audit_log, hash_password

members_bp = Blueprint("members", __name__, url_prefix="/api/members")


# ── GET /api/members  (admin) – fan-out to all shards, merge ─────────
@members_bp.route("", methods=["GET"])
@require_auth
@require_role("admin")
def list_members():
    membership_type = request.args.get("type")
    results = []
    shard_errors = []

    for i, conn, conn_err in get_all_shards():
        if conn is None:
            shard_errors.append({"shard": i, "error": conn_err})
            continue
        try:
            cur = conn.cursor()
            if membership_type:
                cur.execute(
                    "SELECT MemberID, Name, Email, MembershipType, LoyaltyPoints, "
                    "RegistrationDate FROM Member "
                    "WHERE MembershipType = %s ORDER BY LoyaltyPoints DESC",
                    (membership_type,)
                )
            else:
                cur.execute(
                    "SELECT MemberID, Name, Email, MembershipType, LoyaltyPoints, "
                    "RegistrationDate FROM Member ORDER BY LoyaltyPoints DESC"
                )
            results.extend(cur.fetchall())
        except Exception as e:
            shard_errors.append({"shard": i, "error": str(e)})

    # Merge: sort combined results by LoyaltyPoints descending
    results.sort(key=lambda r: r["LoyaltyPoints"], reverse=True)
    resp = {"members": results, "total": len(results)}
    if shard_errors:
        resp["degraded"] = True
        resp["shard_errors"] = shard_errors
    return jsonify(resp), 200


# ── GET /api/members/<id> – route to single shard ────────────────────
@members_bp.route("/<member_id>", methods=["GET"])
@require_auth
def get_member(member_id):
    u = g.current_user
    if u["role"] != "admin":
        local_cur = get_db().cursor()
        local_cur.execute(
            "SELECT MemberID FROM UserCredentials WHERE UserID = %s", (u["user_id"],)
        )
        row = local_cur.fetchone()
        if not row or row["MemberID"] != member_id:
            return jsonify({"error": "Forbidden – can only view your own profile"}), 403

    conn = get_shard(member_id)            # ← routed to correct shard
    cur  = conn.cursor()
    cur.execute("SELECT * FROM Member WHERE MemberID = %s", (member_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({"error": "Member not found"}), 404

    # Annotate response with shard info (useful for demo/debugging)
    row["_shard_id"] = get_shard_id(member_id)
    return jsonify(row), 200


# ── POST /api/members  (admin) – insert into correct shard ───────────
@members_bp.route("", methods=["POST"])
@require_auth
@require_role("admin")
def create_member():
    data = request.get_json(silent=True) or {}
    required = ["MemberID", "Name", "Age", "Email", "ContactNumber",
                "Address", "RegistrationDate"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    member_id = data["MemberID"]
    sid       = get_shard_id(member_id)
    conn      = get_shard(member_id)       # ← routed insert
    cur       = conn.cursor()

    try:
        cur.execute(
            """INSERT INTO Member
               (MemberID, Name, Age, Email, ContactNumber, Address,
                MembershipType, RegistrationDate, LoyaltyPoints, shard_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (member_id, data["Name"], data["Age"], data["Email"],
             data["ContactNumber"], data["Address"],
             data.get("MembershipType", "Silver"),
             data["RegistrationDate"],
             data.get("LoyaltyPoints", 0),
             sid)
        )
        # Also create UserCredentials locally if provided
        if data.get("Username") and data.get("Password"):
            local_db  = get_db()
            local_cur = local_db.cursor()
            local_cur.execute(
                "INSERT INTO UserCredentials (MemberID, Username, PasswordHash, Role) "
                "VALUES (%s, %s, %s, 'user')",
                (member_id, data["Username"], hash_password(data["Password"]))
            )
            local_db.commit()

        conn.commit()
        u = g.current_user
        audit_log(u["username"], u["role"], "INSERT", "Member", member_id)
        return jsonify({"message": "Member created", "shard_id": sid}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400


# ── PUT /api/members/<id> – update on correct shard ──────────────────
@members_bp.route("/<member_id>", methods=["PUT"])
@require_auth
def update_member(member_id):
    u = g.current_user
    if u["role"] != "admin":
        local_cur = get_db().cursor()
        local_cur.execute(
            "SELECT MemberID FROM UserCredentials WHERE UserID = %s", (u["user_id"],)
        )
        row = local_cur.fetchone()
        if not row or row["MemberID"] != member_id:
            return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(silent=True) or {}
    if u["role"] != "admin":
        data.pop("LoyaltyPoints", None)
        data.pop("MembershipType", None)

    allowed  = {"Name", "ContactNumber", "Address", "MembershipType", "LoyaltyPoints"}
    updates  = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({"error": "No valid fields provided"}), 400

    conn       = get_shard(member_id)     # ← routed to correct shard
    cur        = conn.cursor()
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values     = list(updates.values()) + [member_id]

    try:
        cur.execute(f"UPDATE Member SET {set_clause} WHERE MemberID = %s", values)
        if cur.rowcount == 0:
            return jsonify({"error": "Member not found"}), 404
        conn.commit()
        audit_log(u["username"], u["role"], "UPDATE", "Member", member_id)
        return jsonify({"message": "Member updated"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400


# ── DELETE /api/members/<id> – delete from correct shard ─────────────
@members_bp.route("/<member_id>", methods=["DELETE"])
@require_auth
@require_role("admin")
def delete_member(member_id):
    conn = get_shard(member_id)            # ← routed to correct shard
    cur  = conn.cursor()
    try:
        cur.execute("DELETE FROM Member WHERE MemberID = %s", (member_id,))
        if cur.rowcount == 0:
            return jsonify({"error": "Member not found"}), 404
        conn.commit()
        u = g.current_user
        audit_log(u["username"], u["role"], "DELETE", "Member", member_id)
        return jsonify({"message": "Member deleted"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400


# ── GET /api/members/<id>/portfolio ──────────────────────────────────
@members_bp.route("/<member_id>/portfolio", methods=["GET"])
@require_auth
def get_portfolio(member_id):
    u = g.current_user
    if u["role"] != "admin":
        local_cur = get_db().cursor()
        local_cur.execute(
            "SELECT MemberID FROM UserCredentials WHERE UserID = %s", (u["user_id"],)
        )
        row = local_cur.fetchone()
        if not row or row["MemberID"] != member_id:
            return jsonify({"error": "Forbidden"}), 403

    conn = get_shard(member_id)
    cur  = conn.cursor()

    cur.execute("SELECT * FROM Member WHERE MemberID = %s", (member_id,))
    member = cur.fetchone()
    if not member:
        return jsonify({"error": "Member not found"}), 404

    cur.execute(
        "SELECT COUNT(*) as total_orders, SUM(FinalAmount) as total_spent, "
        "AVG(FinalAmount) as avg_order_value, MAX(SaleDate) as last_purchase "
        "FROM Sale WHERE MemberID = %s",
        (member_id,)
    )
    purchase_summary = cur.fetchone()

    return jsonify({
        "member":           member,
        "purchase_summary": purchase_summary,
        "_shard_id":        get_shard_id(member_id),
    }), 200