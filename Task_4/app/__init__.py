"""
app/__init__.py  –  Flask application factory for ShopStop Assignment 4
Adds shard configuration on top of existing Assignment 3 setup.
"""

import os
import logging
import datetime
import decimal
from flask import Flask
from flask.json.provider import DefaultJSONProvider


class ShopStopJSONProvider(DefaultJSONProvider):
    """
    Custom JSON provider so pymysql types serialize cleanly:
      datetime.datetime → "2026-02-10 18:45:00"  (ISO, sortable)
      datetime.date     → "2026-02-10"
      decimal.Decimal   → float  (for currency columns)
    Without this, Flask 3.x encodes datetimes as RFC-2822 strings
    ("Tue, 10 Feb 2026 18:45:00 GMT") which breaks date comparisons.
    """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d")
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super().default(obj)


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Register custom JSON provider before anything else
    app.json_provider_class = ShopStopJSONProvider
    app.json = ShopStopJSONProvider(app)

    # ── Existing config (unchanged) ──────────────────────────────────
    app.config["SECRET_KEY"]       = os.environ.get("SECRET_KEY", "shopstop-dev-secret-2026")
    app.config["JWT_EXPIRY_HOURS"] = 2

    # Local MySQL (still used for non-sharded tables: Product, Employee, etc.)
    app.config["MYSQL_HOST"]     = os.environ.get("MYSQL_HOST",     "localhost")
    app.config["MYSQL_USER"]     = os.environ.get("MYSQL_USER",     "root")
    app.config["MYSQL_PASSWORD"] = "Thrisha@12"
    app.config["MYSQL_DB"]       = os.environ.get("MYSQL_DB",       "ShopStop")
    app.config["MYSQL_PORT"]     = int(os.environ.get("MYSQL_PORT", 3306))

    # ── NEW: Remote shard config ─────────────────────────────────────
    app.config["SHARD_USER"]     = os.environ.get("SHARD_USER",     "Nexus")
    app.config["SHARD_PASSWORD"] = os.environ.get("SHARD_PASSWORD", "password@123")
    app.config["SHARD_DB"]       = os.environ.get("SHARD_DB",       "Nexus")

    # Audit log path
    app.config["AUDIT_LOG"] = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "logs", "audit.log"
    )

    # ── Logging ──────────────────────────────────────────────────────
    logging.basicConfig(level=logging.INFO)

    # ── Init DB helpers ──────────────────────────────────────────────
    from app.db           import init_app as init_local_db
    from app.shard_router import init_app as init_shards
    init_local_db(app)
    init_shards(app)

    # ── Register blueprints ──────────────────────────────────────────
    from app.routes.auth      import auth_bp
    from app.routes.products  import products_bp
    from app.routes.members   import members_bp      # ← sharded version
    from app.routes.sales     import sales_bp        # ← sharded version
    from app.routes.orders    import orders_bp
    from app.routes.employees import employees_bp
    from app.routes.ui        import ui_bp
    from app.routes.shards    import shards_bp       # ← NEW: shard diagnostic routes

    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(ui_bp)
    app.register_blueprint(shards_bp)

    return app