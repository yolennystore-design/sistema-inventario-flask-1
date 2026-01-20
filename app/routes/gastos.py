from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, send_file
)
from app.db import get_db
from datetime import date
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

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
        SELECT id, fecha, concepto, categoria, monto
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
@gastos_bp.route("/eliminar/<int:id>")
def eliminar(id):
    if session.get("rol") != "admin":
        return redirect(url_for("dashboard"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM gastos WHERE id = %s", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for("gastos.index"))
@gastos_bp.route("/imprimir")
def imprimir():
    if session.get("rol") != "admin":
        return redirect(url_for("dashboard"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT fecha, concepto, categoria, monto
        FROM gastos
        ORDER BY fecha DESC
    """)
    gastos = cur.fetchall()
    conn.close()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    y = 750
    c.setFont("Helvetica-Bold", 14)
    c.drawString(200, y, "REPORTE DE GASTOS")
    y -= 30

    c.setFont("Helvetica", 9)
    total = 0

    for g in gastos:
        linea = f"{g['fecha']} - {g['concepto']} ({g['categoria']}) - ${g['monto']}"
        c.drawString(40, y, linea)
        y -= 15
        total += g["monto"]

        if y < 50:
            c.showPage()
            y = 750
            c.setFont("Helvetica", 9)

    y -= 20
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, f"TOTAL GENERAL: ${total}")

    c.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="reporte_gastos.pdf",
        mimetype="application/pdf"
    )
