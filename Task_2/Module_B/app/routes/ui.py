"""
app/routes/ui.py  –  Serves HTML pages (login, dashboard, portfolio)
"""

from flask import Blueprint, render_template

ui_bp = Blueprint("ui", __name__)


@ui_bp.route("/login-page")
def login_page():
    return render_template("login.html")


@ui_bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@ui_bp.route("/portfolio")
def portfolio_page():
    return render_template("portfolio.html")
