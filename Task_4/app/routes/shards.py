"""
app/routes/shards.py  –  Shard Diagnostic & Verification Endpoints
CS 432 Assignment 4 | Group: Nexus

These endpoints are for:
  1. Demonstrating that routing works (for the video)
  2. Verifying data distribution across shards
  3. Showing which shard a given MemberID hashes to
"""

import hashlib
import pymysql

from flask import Blueprint, jsonify, request, current_app
from app.shard_router import (
    get_shard_id,
    NUM_SHARDS, SHARD_CONFIG
)
from app.auth import require_auth, require_role

shards_bp = Blueprint("shards", __name__, url_prefix="/api/shards")


# ── helper: open a fresh direct connection to a specific shard ────────
def _direct_conn(sid: int, dict_cursor: bool = True):
    """
    Open a fresh direct pymysql connection to the given shard.
    Used by diagnostic endpoints that need raw access independent
    of Flask's per-request g-based connection pool.
    """
    kwargs = dict(
        host            = SHARD_CONFIG[sid]["host"],
        port            = SHARD_CONFIG[sid]["port"],
        user            = current_app.config["SHARD_USER"],
        password        = current_app.config["SHARD_PASSWORD"],
        database        = current_app.config["SHARD_DB"],
        connect_timeout = 5,
    )
    if dict_cursor:
        kwargs["cursorclass"] = pymysql.cursors.DictCursor
    return pymysql.connect(**kwargs)


# ── GET /api/shards/status  ───────────────────────────────────────────
@shards_bp.route("/status", methods=["GET"])
def shard_status():
    """
    Returns the connection status of all 3 shards.
    Use this first to verify you can reach all shards.
    Queries each shard independently — no dependency on Flask g.
    """
    status = {}

    for sid in range(NUM_SHARDS):
        port = SHARD_CONFIG[sid]["port"]
        try:
            # Open a fresh direct connection to THIS specific shard
            conn = _direct_conn(sid, dict_cursor=False)  # tuple cursor for sys vars
            cur  = conn.cursor()

            # Separate query for server variables (no table dependency)
            cur.execute("SELECT @@hostname, @@port")
            srv      = cur.fetchone()          # (hostname, port) tuple
            hostname = srv[0] if srv else "?"
            db_port  = srv[1] if srv else port

            # Separate query for member count — catches missing table gracefully
            try:
                cur.execute("SELECT COUNT(*) FROM Member")
                count_row    = cur.fetchone()
                member_count = count_row[0] if count_row else 0
            except Exception:
                member_count = 0   # table not yet created on this shard

            conn.close()

            status[f"shard_{sid}"] = {
                "port":         port,
                "reachable":    True,
                "hostname":     hostname,
                "db_port":      db_port,
                "member_count": member_count,
            }

        except Exception as e:
            status[f"shard_{sid}"] = {
                "port":      port,
                "reachable": False,
                "error":     str(e),
            }

    return jsonify({"shards": status, "total_shards": NUM_SHARDS}), 200


# ── GET /api/shards/route?member_id=MEM001  ───────────────────────────
@shards_bp.route("/route", methods=["GET"])
def show_route():
    """
    Demonstrates the routing decision for a given MemberID.
    No auth required — used for demo purposes.
    Usage: GET /api/shards/route?member_id=MEM001
    """
    member_id = request.args.get("member_id")
    if not member_id:
        return jsonify({"error": "member_id query param required"}), 400

    sid    = get_shard_id(member_id)
    digest = hashlib.md5(member_id.encode()).hexdigest()[:8]

    return jsonify({
        "member_id":  member_id,
        "md5_prefix": digest,
        "int_value":  int(digest, 16),
        "shard_id":   sid,
        "shard_port": SHARD_CONFIG[sid]["port"],
        "formula":    f"int(MD5('{member_id}')[:8], 16) % {NUM_SHARDS} = {sid}",
    }), 200


# ── GET /api/shards/distribution  ─────────────────────────────────────
@shards_bp.route("/distribution", methods=["GET"])
@require_auth
@require_role("admin")
def distribution():
    """
    Shows data distribution across all shards.
    Verifies: no data loss, no duplication.
    Requires admin token.
    """
    result        = {}
    total_members = 0
    total_sales   = 0

    for sid in range(NUM_SHARDS):
        try:
            conn = _direct_conn(sid, dict_cursor=True)
            cur  = conn.cursor()

            cur.execute("SELECT COUNT(*) AS cnt FROM Member")
            m_cnt = cur.fetchone()["cnt"]

            cur.execute("SELECT COUNT(*) AS cnt FROM Sale")
            s_cnt = cur.fetchone()["cnt"]

            cur.execute(
                "SELECT MembershipType, COUNT(*) AS cnt "
                "FROM Member GROUP BY MembershipType"
            )
            breakdown = cur.fetchall()

            cur.execute("SELECT @@hostname AS h")
            hostname = cur.fetchone()["h"]

            conn.close()

            total_members += m_cnt
            total_sales   += s_cnt

            result[f"shard_{sid}"] = {
                "port":             SHARD_CONFIG[sid]["port"],
                "hostname":         hostname,
                "member_count":     m_cnt,
                "sale_count":       s_cnt,
                "member_breakdown": breakdown,
            }

        except Exception as e:
            result[f"shard_{sid}"] = {
                "port":  SHARD_CONFIG[sid]["port"],
                "error": str(e),
            }

    result["summary"] = {
        "total_members_across_shards": total_members,
        "total_sales_across_shards":   total_sales,
        "num_shards":                  NUM_SHARDS,
    }

    return jsonify(result), 200


# ── GET /api/shards/verify/<member_id>  ───────────────────────────────
@shards_bp.route("/verify/<member_id>", methods=["GET"])
@require_auth
def verify_member_shard(member_id):
    """
    Checks all 3 shards and reports which shard(s) the member exists on.
    Should always be exactly ONE shard — proves no duplication.
    Usage: GET /api/shards/verify/MEM001
    """
    found_on = []

    for sid in range(NUM_SHARDS):
        try:
            conn = _direct_conn(sid, dict_cursor=True)
            cur  = conn.cursor()
            cur.execute(
                "SELECT MemberID, Name, shard_id FROM Member WHERE MemberID = %s",
                (member_id,)
            )
            row = cur.fetchone()
            conn.close()
            if row:
                found_on.append({
                    "shard_id": sid,
                    "port":     SHARD_CONFIG[sid]["port"],
                    "data":     row,
                })
        except Exception:
            pass  # shard unreachable — skip silently

    expected_shard = get_shard_id(member_id)

    return jsonify({
        "member_id":       member_id,
        "expected_shard":  expected_shard,
        "found_on_shards": found_on,
        "is_correct":      (
            len(found_on) == 1 and
            found_on[0]["shard_id"] == expected_shard
        ),
        "no_duplication":  len(found_on) <= 1,
    }), 200