# -*- coding: utf-8 -*-

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash, send_file
)
from io import BytesIO
import os
import json
from datetime import datetime

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Table,
    TableStyle,
    Image,
    Spacer
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
# 🔐 ABONAR (ADMIN)
# ======================
@creditos_bp.route("/abonar/<int:id>", methods=["POST"])
def abonar(id):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    if session.get("rol") != "admin":
        flash("⛔ Solo el administrador puede realizar abonos", "danger")
        return redirect(url_for("creditos.index"))

    abono = float(request.form["abono"])
    fecha_abono = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT abonado, pendiente FROM creditos WHERE id = %s",
        (id,)
    )
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return redirect(url_for("creditos.index"))

    abonado = float(row["abonado"])
    pendiente = float(row["pendiente"])

    if abono <= 0 or abono > pendiente:
        flash("Monto de abono inválido", "danger")
        return redirect(url_for("creditos.index"))

    nuevo_abonado = abonado + abono
    nuevo_pendiente = pendiente - abono
    estado = "Pagado" if nuevo_pendiente == 0 else "Pendiente"

    cur.execute("""
        UPDATE creditos
        SET abonado = %s,
            pendiente = %s,
            estado = %s,
            fecha_ultimo_abono = %s
        WHERE id = %s
    """, (
        nuevo_abonado,
        nuevo_pendiente,
        estado,
        fecha_abono,
        id
    ))

    conn.commit()
    cur.close()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Abonó RD${abono:,.2f} al crédito #{id}",
        modulo="Créditos"
    )

    flash("✅ Abono realizado correctamente", "success")
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
               abonado, pendiente, fecha, estado,
               fecha_ultimo_abono
        FROM creditos
        WHERE numero_factura = %s
    """, (numero_factura,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return redirect(url_for("creditos.index"))

    # Normalizar fecha último abono
    fecha_ultimo_abono = (
        str(row["fecha_ultimo_abono"])
        if row.get("fecha_ultimo_abono")
        else "Sin abonos"
    )

    numero_factura = row["numero_factura"]
    cliente = row["cliente"]
    monto = float(row["monto"])
    abonado = float(row["abonado"])
    pendiente = float(row["pendiente"])
    fecha = row["fecha"]
    estado = row.get("estado", "Pendiente")

    # ======================
    # PRODUCTOS DE LA VENTA
    # ======================
    items = []
    ruta_ventas = "app/data/ventas.json"
    if os.path.exists(ruta_ventas):
        with open(ruta_ventas, "r", encoding="utf-8") as f:
            ventas = json.load(f)
            venta = next(
                (v for v in ventas if v.get("numero_factura") == numero_factura),
                None
            )
            if venta:
                items = venta.get("items", [])

    # ======================
    # PDF
    # ======================
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    elementos = []

    logo = "app/static/logo.png"
    if os.path.exists(logo):
        elementos.append(Image(logo, 100, 60))

    elementos.append(Spacer(1, 15))
    elementos.append(Paragraph("<b>YOLENNY STORE</b>", styles["Title"]))
    elementos.append(Paragraph("Comprobante de Crédito", styles["Heading2"]))
    elementos.append(Spacer(1, 20))

    datos = [
        ["Factura No.", numero_factura],
        ["Cliente", cliente],
        ["Fecha", fecha],
        ["Estado del crédito", estado],
    ]

    tabla_datos = Table(datos, colWidths=[150, 300])
    tabla_datos.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
    ]))

    elementos.append(tabla_datos)
    elementos.append(Spacer(1, 20))

    elementos.append(Paragraph("<b>Resumen del Crédito</b>", styles["Heading3"]))
    elementos.append(Spacer(1, 10))

    detalle = "<br/>".join([
        f"{i['nombre']} ({i['cantidad']} x RD$ {i['precio']:,.2f}) = RD$ {i['total']:,.2f}"
        for i in items
    ]) if items else "—"

    tabla_resumen = Table(
        [
            ["Detalle", "Monto Total", "Total Abonado", "Saldo Pendiente", "Último Abono"],
            [
                Paragraph(detalle, styles["Normal"]),
                f"RD$ {monto:,.2f}",
                f"RD$ {abonado:,.2f}",
                f"RD$ {pendiente:,.2f}",
                Paragraph(fecha_ultimo_abono.replace(" ", "<br/>"), styles["Normal"])
            ]
        ],
        colWidths=[200, 90, 90, 90, 110]
    )

    tabla_resumen.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    elementos.append(tabla_resumen)
    elementos.append(Spacer(1, 30))

    elementos.append(Paragraph(
        "Este documento certifica el estado actual del crédito del cliente.",
        styles["Normal"]
    ))

    elementos.append(Spacer(1, 30))
    elementos.append(Paragraph("______________________________", styles["Normal"]))
    elementos.append(Paragraph("<b>Firma del Cliente</b>", styles["Normal"]))
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph("<i>¡Gracias por confiar en nosotros!</i>", styles["Italic"]))

    doc.build(elementos)

    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"credito_{numero_factura}.pdf"
    )

# ======================
# 🗑 ELIMINAR CRÉDITO
# ======================
@creditos_bp.route("/eliminar/<int:id>")
def eliminar_credito(id):
    if session.get("rol") != "admin":
        return redirect(url_for("creditos.index"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT numero_factura FROM creditos WHERE id = %s", (id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return redirect(url_for("creditos.index"))

    cur.execute("DELETE FROM creditos WHERE id = %s", (id,))
    conn.commit()

    cur.close()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Eliminó crédito factura {row['numero_factura']}",
        modulo="Créditos"
    )

    flash("🗑 Crédito eliminado correctamente", "success")
    return redirect(url_for("creditos.index"))
