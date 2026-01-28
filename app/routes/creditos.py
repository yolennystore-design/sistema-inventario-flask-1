# -*- coding: utf-8 -*-

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash, send_file
)
from datetime import datetime
from io import BytesIO
import os

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Image
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

from app.db import get_db
from app.utils.auditoria import registrar_log

creditos_bp = Blueprint("creditos", __name__, url_prefix="/creditos")


# ======================
# 📋 LISTADO + FILTROS
# ======================
@creditos_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    cliente = request.args.get("cliente", "")
    estado = request.args.get("estado", "")

    conn = get_db()
    cur = conn.cursor()

    # ✅ FIX AQUÍ
    cur.execute("SELECT DISTINCT cliente FROM creditos ORDER BY cliente")
    clientes = [c["cliente"] for c in cur.fetchall()]

    query = """
        SELECT id, numero_factura, cliente, monto,
               abonado, pendiente, estado, fecha
        FROM creditos
        WHERE 1=1
    """
    params = []

    if cliente:
        query += " AND cliente = %s"
        params.append(cliente)

    if estado:
        query += " AND estado = %s"
        params.append(estado)

    query += " ORDER BY fecha DESC"

    cur.execute(query, params)
    creditos = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "creditos/index.html",
        creditos=creditos,
        clientes=clientes,
        cliente_sel=cliente,
        estado=estado
    )

# ======================
# 🔐 ABONAR (SOLO ADMIN)
# ======================
@creditos_bp.route("/abonar/<int:id>", methods=["POST"])
def abonar(id):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    if session.get("rol") != "admin":
        flash("⛔ Solo el administrador puede realizar abonos", "danger")
        return redirect(url_for("creditos.index"))

    abono = float(request.form["abono"])

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT abonado, pendiente
        FROM creditos
        WHERE id = %s
    """, (id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return redirect(url_for("creditos.index"))

    abonado, pendiente = row

    if abono <= 0 or abono > pendiente:
        flash("Monto de abono inválido", "danger")
        return redirect(url_for("creditos.index"))

    nuevo_abonado = abonado + abono
    nuevo_pendiente = pendiente - abono
    estado = "Pagado" if nuevo_pendiente == 0 else "Pendiente"

    cur.execute("""
        UPDATE creditos
        SET abonado=%s, pendiente=%s, estado=%s
        WHERE id=%s
    """, (nuevo_abonado, nuevo_pendiente, estado, id))

    conn.commit()
    cur.close()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Abonó RD${abono} al crédito #{id}",
        modulo="Créditos"
    )

    flash("✅ Abono realizado correctamente", "success")
    return redirect(url_for("creditos.index"))


# ======================
# 📝 SOLICITAR PERMISO (EMPLEADO)
# ======================
@creditos_bp.route("/solicitar_abono/<int:id>", methods=["POST"])
def solicitar_abono(id):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    monto = request.form["abono"]
    usuario = session["usuario"]

    registrar_log(
        usuario=usuario,
        accion=f"Solicitó permiso para abonar RD${monto} al crédito #{id}",
        modulo="Créditos"
    )

    flash(
        "📨 Solicitud enviada al administrador. "
        "El abono será aplicado tras aprobación.",
        "info"
    )

    return redirect(url_for("creditos.index"))


# ======================
# 🧾 PDF DEL CRÉDITO
# ======================
@creditos_bp.route("/pdf/<numero_factura>")
def pdf_credito(numero_factura):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT numero_factura, cliente, monto,
               abonado, pendiente, fecha
        FROM creditos
        WHERE numero_factura = %s
    """, (numero_factura,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return redirect(url_for("creditos.index"))

    numero_factura, cliente, monto, abonado, pendiente, fecha = row

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elementos = []

    logo = "app/static/logo.png"
    if os.path.exists(logo):
        elementos.append(Image(logo, 90, 60))

    elementos.append(Paragraph("<b>Yolenny Store</b>", styles["Heading1"]))
    elementos.append(Paragraph("<b>COMPROBANTE DE CRÉDITO</b><br/><br/>", styles["Heading2"]))

    data = [
        ["Factura", numero_factura],
        ["Cliente", cliente],
        ["Fecha", fecha],
        ["Monto", f"RD$ {monto:,.2f}"],
        ["Abonado", f"RD$ {abonado:,.2f}"],
        ["Pendiente", f"RD$ {pendiente:,.2f}"],
    ]

    tabla = Table(data, colWidths=[150, 300])
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ]))

    elementos.append(tabla)
    doc.build(elementos)

    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"credito_{numero_factura}.pdf"
    )


# ======================
# 🗑 ELIMINAR CRÉDITO (ADMIN)
# ======================
@creditos_bp.route("/eliminar/<int:id>")
def eliminar_credito(id):
    if session.get("rol") != "admin":
        return redirect(url_for("creditos.index"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT numero_factura FROM creditos WHERE id=%s", (id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return redirect(url_for("creditos.index"))

    numero_factura = row[0]

    cur.execute("DELETE FROM creditos WHERE id=%s", (id,))
    conn.commit()

    cur.close()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Eliminó crédito factura {numero_factura}",
        modulo="Créditos"
    )

    return redirect(url_for("creditos.index"))
