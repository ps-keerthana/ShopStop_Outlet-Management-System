"""
app/auth.py  –  JWT session management + audit logging
CS 432 Assignment 2 – Module B
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify, g, current_app


# ──────────────────────────────────────────────
#  JWT helpers
# ──────────────────────────────────────────────

def _secret():
    return current_app.config["SECRET_KEY"]


def generate_token(username: str, role: str, user_id: int) -> str:
    expiry = datetime.now(timezone.utc) + timedelta(
        hours=current_app.config.get("JWT_EXPIRY_HOURS", 2)
    )
    payload = {
        "username": username,
        "role":     role,
        "user_id":  user_id,
        "exp":      expiry,
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decode and verify JWT. Raises jwt exceptions on failure."""
    return jwt.decode(token, _secret(), algorithms=["HS256"])


# ──────────────────────────────────────────────
#  Audit logging
# ──────────────────────────────────────────────

def audit_log(username: str, role: str, action: str,
              table: str = "-", record_id: str = "-",
              status: str = "SUCCESS"):
    """Append a structured line to audit.log."""
    log_path = current_app.config.get("AUDIT_LOG", "logs/audit.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    line = (
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"user={username} role={role} action={action} "
        f"table={table} id={record_id} status={status}\n"
    )
    with open(log_path, "a") as f:
        f.write(line)


# ──────────────────────────────────────────────
#  Decorators
# ──────────────────────────────────────────────

def require_auth(f):
    """Validate the JWT token from Authorization header and attach user to g."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip()

        if not token:
            return jsonify({"error": "No session found"}), 401
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Session expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid session token"}), 401

        g.current_user = {
            "username": payload["username"],
            "role":     payload["role"],
            "user_id":  payload["user_id"],
            "expiry":   datetime.fromtimestamp(payload["exp"], tz=timezone.utc).isoformat(),
        }
        return f(*args, **kwargs)
    return decorated


def require_role(*roles):
    """RBAC decorator – must be applied AFTER @require_auth."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = g.current_user
            if user["role"] not in roles:
                audit_log(user["username"], user["role"],
                          "FORBIDDEN", record_id=request.path, status="DENIED")
                return jsonify({"error": "Forbidden – insufficient role"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ──────────────────────────────────────────────
#  Password helpers
# ──────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
