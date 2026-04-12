"""
app/routes/members.py  –  Member CRUD + Member Portfolio
Admin: full access. Regular user: own record only.
"""

from flask import Blueprint, request, jsonify, g
from app.db   import get_db
from app.auth import require_auth, require_role, audit_log, hash_password

members_bp = Blueprint("members", __name__, url_prefix="/api/members")


# ── GET /api/members  (admin only) ───────────────────────────────────
@members_bp.route("", methods=["GET"])
@require_auth
@require_role("admin")
def list_members():
    db  = get_db()
    cur = db.cursor()
    membership_type = request.args.get("type")
    if membership_type:
        cur.execute(
            "SELECT MemberID, Name, Email, MembershipType, LoyaltyPoints, RegistrationDate "
            "FROM Member WHERE MembershipType = %s ORDER BY LoyaltyPoints DESC",
            (membership_type,)
        )
    else:
        cur.execute(
            "SELECT MemberID, Name, Email, MembershipType, LoyaltyPoints, RegistrationDate "
            "FROM Member ORDER BY LoyaltyPoints DESC"
        )
    return jsonify({"members": cur.fetchall()}), 200


# ── GET /api/members/<id>  (own record or admin) ──────────────────────
@members_bp.route("/<member_id>", methods=["GET"])
@require_auth
def get_member(member_id):
    u = g.current_user
    # Regular users can only view their own profile
    if u["role"] != "admin":
        db  = get_db()
        cur = db.cursor()
        cur.execute(
            "SELECT MemberID FROM UserCredentials WHERE UserID = %s", (u["user_id"],)
        )
        row = cur.fetchone()
        if not row or row["MemberID"] != member_id:
            audit_log(u["username"], u["role"], "FORBIDDEN",
                      table="Member", record_id=member_id, status="DENIED")
            return jsonify({"error": "Forbidden – can only view your own profile"}), 403

    db  = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM Member WHERE MemberID = %s", (member_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({"error": "Member not found"}), 404
    return jsonify(row), 200


# ── GET /api/members/<id>/portfolio  ──────────────────────────────────
@members_bp.route("/<member_id>/portfolio", methods=["GET"])
@require_auth
def get_portfolio(member_id):
    u = g.current_user
    # Regular users: own portfolio only
    if u["role"] != "admin":
        db  = get_db()
        cur = db.cursor()
        cur.execute(
            "SELECT MemberID FROM UserCredentials WHERE UserID = %s", (u["user_id"],)
        )
        row = cur.fetchone()
        if not row or row["MemberID"] != member_id:
            audit_log(u["username"], u["role"], "FORBIDDEN",
                      table="Member", record_id=member_id, status="DENIED")
            return jsonify({"error": "Forbidden – can only view your own portfolio"}), 403

    db  = get_db()
    cur = db.cursor()

    # Member basic info
    cur.execute("SELECT * FROM Member WHERE MemberID = %s", (member_id,))
    member = cur.fetchone()
    if not member:
        return jsonify({"error": "Member not found"}), 404

    # Purchase history summary
    cur.execute(
        "SELECT COUNT(*) as total_orders, "
        "SUM(FinalAmount) as total_spent, "
        "AVG(FinalAmount) as avg_order_value, "
        "MAX(SaleDate) as last_purchase "
        "FROM Sale WHERE MemberID = %s",
        (member_id,)
    )
    purchase_summary = cur.fetchone()

    # Top purchased products
    cur.execute(
        "SELECT p.ProductName, SUM(si.Quantity) as total_qty, "
        "SUM(si.Subtotal) as total_spent "
        "FROM Sale s "
        "JOIN SaleItem si ON s.SaleID = si.SaleID "
        "JOIN Product  p  ON si.ProductID = p.ProductID "
        "WHERE s.MemberID = %s "
        "GROUP BY p.ProductID ORDER BY total_spent DESC LIMIT 5",
        (member_id,)
    )
    top_products = cur.fetchall()

    # Group membership
    cur.execute(
        "SELECT GroupName, JoinedAt FROM GroupMapping WHERE MemberID = %s",
        (member_id,)
    )
    groups = cur.fetchall()

    # Active promotions available to this member
    cur.execute(
        "SELECT pr.PromotionName, pr.DiscountPercentage, pr.EndDate "
        "FROM Promotion pr WHERE pr.IsActive = TRUE "
        "AND CURDATE() BETWEEN pr.StartDate AND pr.EndDate "
        "ORDER BY pr.DiscountPercentage DESC LIMIT 5"
    )
    promos = cur.fetchall()

    portfolio = {
        "member":           member,
        "purchase_summary": purchase_summary,
        "top_products":     top_products,
        "groups":           groups,
        "available_promos": promos,
    }
    return jsonify(portfolio), 200


# ── POST /api/members  (admin only) ──────────────────────────────────
@members_bp.route("", methods=["POST"])
@require_auth
@require_role("admin")
def create_member():
    data = request.get_json(silent=True) or {}
    required = ["MemberID", "Name", "Age", "Email", "ContactNumber",
                "Address", "RegistrationDate"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing: {missing}"}), 400

    db  = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "INSERT INTO Member (MemberID, Name, Age, Email, ContactNumber, "
            "Address, MembershipType, RegistrationDate, LoyaltyPoints) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (data["MemberID"], data["Name"], data["Age"], data["Email"],
             data["ContactNumber"], data["Address"],
             data.get("MembershipType", "Silver"),
             data["RegistrationDate"],
             data.get("LoyaltyPoints", 0))
        )
        # Optionally create login credentials
        if data.get("Username") and data.get("Password"):
            cur.execute(
                "INSERT INTO UserCredentials (MemberID, Username, PasswordHash, Role) "
                "VALUES (%s, %s, %s, 'user')",
                (data["MemberID"], data["Username"], hash_password(data["Password"]))
            )
        db.commit()
        u = g.current_user
        audit_log(u["username"], u["role"], "INSERT", "Member", data["MemberID"])
        return jsonify({"message": "Member created"}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# ── PUT /api/members/<id>  (admin, or own record for regular user) ────
@members_bp.route("/<member_id>", methods=["PUT"])
@require_auth
def update_member(member_id):
    u = g.current_user
    # Regular users can only update their own record & only safe fields
    if u["role"] != "admin":
        db  = get_db()
        cur = db.cursor()
        cur.execute(
            "SELECT MemberID FROM UserCredentials WHERE UserID = %s", (u["user_id"],)
        )
        row = cur.fetchone()
        if not row or row["MemberID"] != member_id:
            audit_log(u["username"], u["role"], "FORBIDDEN",
                      table="Member", record_id=member_id, status="DENIED")
            return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(silent=True) or {}
    # Regular users cannot update loyalty points or membership type
    if u["role"] != "admin":
        data.pop("LoyaltyPoints", None)
        data.pop("MembershipType", None)

    allowed = {"Name", "ContactNumber", "Address", "MembershipType",
               "LoyaltyPoints", "Image"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({"error": "No valid fields"}), 400

    db  = get_db()
    cur = db.cursor()
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values     = list(updates.values()) + [member_id]
    try:
        cur.execute(f"UPDATE Member SET {set_clause} WHERE MemberID = %s", values)
        if cur.rowcount == 0:
            return jsonify({"error": "Member not found"}), 404
        db.commit()
        audit_log(u["username"], u["role"], "UPDATE", "Member", member_id)
        return jsonify({"message": "Member updated"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


# ── DELETE /api/members/<id>  (admin only) ───────────────────────────
@members_bp.route("/<member_id>", methods=["DELETE"])
@require_auth
@require_role("admin")
def delete_member(member_id):
    db  = get_db()
    cur = db.cursor()
    try:
        # UserCredentials row deleted by CASCADE
        cur.execute("DELETE FROM Member WHERE MemberID = %s", (member_id,))
        if cur.rowcount == 0:
            return jsonify({"error": "Member not found"}), 404
        db.commit()
        u = g.current_user
        audit_log(u["username"], u["role"], "DELETE", "Member", member_id)
        return jsonify({"message": "Member and credentials deleted"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400


@members_bp.route("/me/member-id", methods=["GET"])
@require_auth
def my_member_id():
    db  = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT MemberID FROM UserCredentials WHERE UserID = %s",
        (g.current_user["user_id"],)
    )
    row = cur.fetchone()
    if not row or not row["MemberID"]:
        return jsonify({"member_id": None}), 200
    return jsonify({"member_id": row["MemberID"]}), 200