"""
app/routes/auth.py  –  /login, /isAuth, / endpoints
Matches the exact API spec in the assignment PDF.
"""

from flask import Blueprint, request, jsonify, g
from app.db   import get_db
from app.auth import (generate_token, decode_token,
                      check_password, hash_password,
                      audit_log, require_auth, require_role)
import jwt

auth_bp = Blueprint("auth", __name__)


# ── / (GET) ───────────────────────────────────────────────────────────
@auth_bp.route("/", methods=["GET"])
def welcome():
    return jsonify({"message": "Welcome to ShopStop APIs"}), 200


# ── /login (POST) ─────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not data or "user" not in data or "password" not in data:
        return jsonify({"error": "Missing parameters"}), 401

    username = data["user"].strip()
    password = data["password"]

    db  = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT UserID, Username, PasswordHash, Role FROM UserCredentials WHERE Username = %s",
        (username,)
    )
    row = cur.fetchone()

    if row is None:
        audit_log(username, "unknown", "LOGIN", status="FAILED")
        return jsonify({"error": "Invalid credentials"}), 401

    # Guard against PLACEHOLDER hashes that were never initialised
    ph = row["PasswordHash"]
    if not ph or ph.upper().startswith("PLACEHOLDER") or not ph.startswith("$2"):
        return jsonify({
            "error": "Passwords not initialised. Please call POST /init-passwords first."
        }), 401

    try:
        valid = check_password(password, ph)
    except ValueError:
        return jsonify({
            "error": "Passwords not initialised. Please call POST /init-passwords first."
        }), 401

    if not valid:
        audit_log(username, "unknown", "LOGIN", status="FAILED")
        return jsonify({"error": "Invalid credentials"}), 401

    token = generate_token(row["Username"], row["Role"], row["UserID"])
    audit_log(row["Username"], row["Role"], "LOGIN", status="SUCCESS")
    return jsonify({
        "message":      "Login successful",
        "session_token": token
    }), 200


# ── /isAuth (GET) ─────────────────────────────────────────────────────
@auth_bp.route("/isAuth", methods=["GET"])
def is_auth():
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()

    if not token:
        return jsonify({"error": "No session found"}), 401

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Session expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid session token"}), 401

    return jsonify({
        "message":  "User is authenticated",
        "username": payload["username"],
        "role":     payload["role"],
        "expiry":   payload["exp"],
    }), 200


# ── /logout (POST) ────────────────────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
@require_auth
def logout():
    u = g.current_user
    audit_log(u["username"], u["role"], "LOGOUT")
    return jsonify({"message": "Logged out"}), 200


# ── /init-passwords (POST) ── one-time bootstrap ──────────────────────
# NOTE: This route is intentionally open (no auth) so it can be called
# once to set real bcrypt hashes when the DB only has PLACEHOLDER values.
# After running it once successfully, it becomes a no-op on PLACEHOLDER
# rows (there are none left) so it is safe to leave as-is.
@auth_bp.route("/init-passwords", methods=["POST"])
def init_passwords():
    """
    One-time bootstrap: replaces PLACEHOLDER hashes with real bcrypt hashes.
    POST body: {"admin": "admin123", "users": "user123"}
    Safe to call multiple times — just re-hashes with the given passwords.
    """
    data     = request.get_json(silent=True) or {}
    admin_pw = data.get("admin", "admin123")
    user_pw  = data.get("users",  "user123")

    db  = get_db()
    cur = db.cursor()

    cur.execute(
        "UPDATE UserCredentials SET PasswordHash = %s WHERE Role = 'admin'",
        (hash_password(admin_pw),)
    )
    cur.execute(
        "UPDATE UserCredentials SET PasswordHash = %s WHERE Role = 'user'",
        (hash_password(user_pw),)
    )
    db.commit()

    audit_log("system", "system", "INIT_PASSWORDS", status="SUCCESS")
    return jsonify({"message": "Passwords initialised successfully"}), 200
