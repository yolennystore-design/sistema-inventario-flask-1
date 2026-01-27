# -*- coding: utf-8 -*-

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, send_file
)
import os
import unicodedata
from datetime import datetime
from io import BytesIO

from app.db import get_db
from app.utils.auditoria import registrar_log
from app.routes.clientes import cargar_clientes

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph,
    Table, TableStyle, Image
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

creditos_bp = Blueprint("creditos", __name__, url_prefix="/creditos")

# ======================================================
# UTILIDADES
# ======================================================
def normalizar(texto):
    return unicodedata.normalize("NFKD", texto or "") \
        .encode("ascii", "ignore") \
        .decode("ascii") \
        .lower() \
        .strip()


def cargar_creditos():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            numero_factura,
            cliente,
            monto,
            abonado,
            pendiente,
            estado,
            fecha
        FROM creditos
        ORDER BY fecha DESC
    """)

    columnas = [c[0] for c in cur.description]
    creditos = []

    def to_float(valor):
        try:
            return float(valor)
        except (TypeError, ValueError):
            return 0.0

    for fila in cur.fetchall():
        c = dict(zip(columnas, fila))

        c["monto"] = to_float(c.get("monto"))
        c["abonado"] = to_float(c.get("abonado"))
        c["pendiente"] = to_float(c.get("pendiente"))

        creditos.append(c)

    cur.close()
    conn.close()
    return creditos



# ======================================================
# LISTAR + FILTRAR CRÉDITOS
# ======================================================
@creditos_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    creditos = cargar_creditos()

    clientes = sorted({
        c.get("nombre", "").strip()
        for c in cargar_clientes()
        if c.get("nombre")
    })

    filtro_cliente = request.args.get("cliente", "").strip()

    if filtro_cliente:
        f = normalizar(filtro_cliente)
        creditos = [
            c for c in creditos
            if normalizar(c["cliente"]) == f
        ]

    return render_template(
        "creditos/index.html",
        creditos=creditos,
        clientes=clientes,
        filtro_cliente=filtro_cliente
    )


# ======================================================
# ABONAR CRÉDITO (POR NUMERO_FACTURA)
# ======================================================
@creditos_bp.route("/abonar/<numero_factura>", methods=["POST"])
def abonar(numero_factura):
    if session.get("rol") != "admin":
        return redirect(url_for("creditos.index"))

    try:
        monto = float(request.form.get("monto", 0))
    except ValueError:
        return redirect(url_for("creditos.index"))

    if monto <= 0:
        return redirect(url_for("creditos.index"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT abonado, pendiente
        FROM creditos
        WHERE numero_factura = %s
    """, (numero_factura,))

    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return redirect(url_for("creditos.index"))

    abonado, pendiente = map(float, row)

    if monto > pendiente:
        cur.close()
        conn.close()
        return redirect(url_for("creditos.index"))

    nuevo_abonado = abonado + monto
    nuevo_pendiente = pendiente - monto
    estado = "Pagado" if nuevo_pendiente == 0 else "Pendiente"

    cur.execute("""
        UPDATE creditos
        SET abonado = %s,
            pendiente = %s,
            estado = %s,
            fecha = %s
        WHERE numero_factura = %s
    """, (
        nuevo_abonado,
        nuevo_pendiente,
        estado,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        numero_factura
    ))

    conn.commit()
    cur.close()
    conn.close()

    registrar_log(
        usuario=session.get("usuario", "admin"),
        accion=f"Abonó ${monto:.2f} al crédito {numero_factura}",
        modulo="Créditos"
    )

    return redirect(url_for("creditos.index"))


# ======================================================
# PDF DEL CRÉDITO
# ======================================================
@creditos_bp.route("/pdf/<numero_factura>")
def pdf_credito(numero_factura):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT numero_factura, cliente, monto, abonado, pendiente, fecha
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

    logo_path = "app/static/logo.png"
    if os.path.exists(logo_path):
        elementos.append(Image(logo_path, width=90, height=60))

    elementos.append(Paragraph("<b>Yolenny Store</b>", styles["Heading1"]))
    elementos.append(Paragraph("<b>COMPROBANTE DE CRÉDITO</b><br/>", styles["Heading2"]))

    data = [
        ["Factura", numero_factura],
        ["Cliente", cliente],
        ["Fecha", fecha],
        ["Monto", f"${float(monto):,.2f}"],
        ["Abonado", f"${float(abonado):,.2f}"],
        ["Pendiente", f"${float(pendiente):,.2f}"],
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
        as_attachment=False,
        download_name=f"credito_{numero_factura}.pdf"
    )


# ======================================================
# ELIMINAR CRÉDITO
# ======================================================
@creditos_bp.route("/eliminar/<numero_factura>")
def eliminar(numero_factura):
    if session.get("rol") != "admin":
        return redirect(url_for("creditos.index"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM creditos WHERE numero_factura = %s",
        (numero_factura,)
    )
    conn.commit()
    cur.close()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Eliminó crédito {numero_factura}",
        modulo="Créditos"
    )

    return redirect(url_for("creditos.index"))
