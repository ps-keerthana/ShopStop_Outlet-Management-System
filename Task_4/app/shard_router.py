"""
app/shard_router.py  –  ShopStop Sharding Layer
CS 432 Assignment 4 | Group: Nexus

This module replaces app/db.py for sharded queries.
It manages connections to all 3 shards and routes operations
to the correct shard based on MemberID.

SHARD STRATEGY: Hash-based on MemberID
  shard_id = MD5(member_id)[:8] (as hex int) % 3
  NULL MemberID (guest) → shard 0

TOPOLOGY:
  Shard 0  →  10.0.116.184 : 3307
  Shard 1  →  10.0.116.184 : 3308
  Shard 2  →  10.0.116.184 : 3309
"""

import hashlib
import pymysql
from flask import g, current_app


NUM_SHARDS = 3

SHARD_CONFIG = {
    0: {"host": "10.0.116.184", "port": 3307},
    1: {"host": "10.0.116.184", "port": 3308},
    2: {"host": "10.0.116.184", "port": 3309},
}


# ── Core routing function ─────────────────────────────────────────────

def get_shard_id(member_id) -> int:
    """
    Determine which shard (0, 1, or 2) a MemberID belongs to.
    Uses MD5 hash of the member_id string for even distribution.
    Guest checkouts (NULL member) are always routed to shard 0.
    """
    if member_id is None:
        return 0
    digest = hashlib.md5(str(member_id).encode()).hexdigest()[:8]
    return int(digest, 16) % NUM_SHARDS


# ── Connection management ─────────────────────────────────────────────

def _get_shard_conn(shard_id: int):
    """
    Return a per-request connection to the given shard.
    Connections are stored in Flask's g object so they are
    reused within a request and closed at the end.
    """
    key = f"shard_conn_{shard_id}"
    if key not in g:
        cfg = SHARD_CONFIG[shard_id]
        g._shard_keys = getattr(g, "_shard_keys", [])
        if key not in g._shard_keys:
            g._shard_keys.append(key)
        setattr(g, key, pymysql.connect(
            host        = cfg["host"],
            port        = cfg["port"],
            user        = current_app.config["SHARD_USER"],
            password    = current_app.config["SHARD_PASSWORD"],
            database    = current_app.config["SHARD_DB"],
            cursorclass = pymysql.cursors.DictCursor,
            autocommit  = False,
            connect_timeout = 10,
        ))
    return getattr(g, key)


def get_shard(member_id) -> pymysql.connections.Connection:
    """
    Get the shard connection for a given MemberID.
    This is the main function your route handlers will call.

    Usage:
        conn = get_shard(member_id)
        cur  = conn.cursor()
        cur.execute("SELECT * FROM Member WHERE MemberID = %s", (member_id,))
    """
    return _get_shard_conn(get_shard_id(member_id))


def get_all_shards() -> list:
    """
    Return (shard_id, conn_or_None, error_or_None) tuples for ALL 3 shards.
    A dead shard yields (shard_id, None, "error message") instead of raising.

    Usage:
        results = []
        shard_errors = []
        for shard_id, conn, err in get_all_shards():
            if conn is None:
                shard_errors.append({"shard": shard_id, "error": err})
                continue
            cur = conn.cursor()
            cur.execute("SELECT * FROM Member WHERE MembershipType = %s", (t,))
            results.extend(cur.fetchall())
    """
    result = []
    for i in range(NUM_SHARDS):
        try:
            conn = _get_shard_conn(i)
            result.append((i, conn, None))
        except Exception as e:
            result.append((i, None, str(e)))
    return result


def close_all_shards(e=None):
    """Tear-down hook: close all open shard connections at end of request."""
    keys = getattr(g, "_shard_keys", [])
    for key in keys:
        conn = g.pop(key, None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def init_app(app):
    """Register the shard close hook with the Flask app."""
    app.teardown_appcontext(close_all_shards)