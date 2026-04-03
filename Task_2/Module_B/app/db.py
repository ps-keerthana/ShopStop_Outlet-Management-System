"""
app/db.py  –  MySQL connection helper using Flask g context
"""

import pymysql
from flask import g, current_app


def get_db():
    """Return a reusable per-request database connection."""
    if "db" not in g:
        g.db = pymysql.connect(
            host     = current_app.config["MYSQL_HOST"],
            user     = current_app.config["MYSQL_USER"],
            password = current_app.config["MYSQL_PASSWORD"],
            database = current_app.config["MYSQL_DB"],
            port     = current_app.config["MYSQL_PORT"],
            cursorclass = pymysql.cursors.DictCursor,
            autocommit  = False,
        )
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)
