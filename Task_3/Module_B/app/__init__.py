"""
app/__init__.py  –  Flask application factory for ShopStop Module B
CS 432 Assignment 2
"""

import os
import logging
from flask import Flask


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # ── config ───────────────────────────────────────────────────────
    app.config["SECRET_KEY"]       = os.environ.get("SECRET_KEY", "shopstop-dev-secret-2026")
    app.config["JWT_EXPIRY_HOURS"] = 2

    # MySQL connection (update with your local credentials)
    app.config["MYSQL_HOST"]     = os.environ.get("MYSQL_HOST",     "localhost")
    app.config["MYSQL_USER"]     = os.environ.get("MYSQL_USER",     "root")
    app.config["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD", "")
    app.config["MYSQL_DB"]       = os.environ.get("MYSQL_DB",       "ShopStop")
    app.config["MYSQL_PORT"]     = int(os.environ.get("MYSQL_PORT", 3306))

    # Audit log path
    app.config["AUDIT_LOG"] = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "logs", "audit.log"
    )

    # ── logging ──────────────────────────────────────────────────────
    logging.basicConfig(level=logging.INFO)

    # ── register blueprints ──────────────────────────────────────────
    from app.routes.auth      import auth_bp
    from app.routes.products  import products_bp
    from app.routes.members   import members_bp
    from app.routes.sales     import sales_bp
    from app.routes.orders    import orders_bp
    from app.routes.employees import employees_bp
    from app.routes.ui        import ui_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(ui_bp)

    return app
