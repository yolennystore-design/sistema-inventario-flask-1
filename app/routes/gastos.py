from flask import Blueprint, render_template, session, redirect, url_for

gastos_bp = Blueprint("gastos", __name__, url_prefix="/gastos")


@gastos_bp.route("/")
def index():
    if session.get("rol") != "admin":
        return redirect(url_for("dashboard"))

    return render_template("gastos/index.html")
