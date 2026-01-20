from flask import Blueprint, render_template, request, redirect, url_for, session
from app.db import get_db
from datetime import date

gastos_bp = Blueprint("gastos", __name__, url_prefix="/gastos")


def solo_admin():
    return session.get("rol") == "admin"


@gastos_bp.route("/")
def index():
    if not solo_admin():
        return redirect(url_for("dashboard"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT concepto, categoria, monto, fecha
        FROM gastos
        ORDER BY fecha DESC
    """)
    gastos = cur.fetchall()
    conn.close()

    return render_template("gastos/index.html", gastos=gastos)


@gastos_bp.route("/agregar", methods=["POST"])
def agregar():
    if not solo_admin():
        return redirect(url_for("dashboard"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO gastos (concepto, categoria, monto, fecha, usuario)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        request.form["concepto"],
        request.form["categoria"],
        float(request.form["monto"]),
        request.form["fecha"],
        session.get("usuario")
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("gastos.index"))
@gastos_bp.route("/resumen")
def resumen():
    if not solo_admin():
        return redirect(url_for("dashboard"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            TO_CHAR(fecha, 'YYYY-MM') AS mes,
            SUM(monto) AS total
        FROM gastos
        GROUP BY mes
        ORDER BY mes DESC
    """)
    resumen = cur.fetchall()
    conn.close()

    return render_template("gastos/resumen.html", resumen=resumen)
