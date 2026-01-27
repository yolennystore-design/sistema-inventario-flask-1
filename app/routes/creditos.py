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

# ======================
# UTILIDADES
# ======================
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

    for fila in cur.fetchall():
        c = dict(zip(columnas, fila))

        def to_float(valor):
            try:
                return float(valor)
            except (TypeError, ValueError):
                return 0.0

        c["monto"] = to_float(c.get("monto"))
        c["abonado"] = to_float(c.get("abonado"))
        c["pendiente"] = to_float(c.get("pendiente"))

        creditos.append(c)

    cur.close()
    conn.close()
    return creditos



def normalizar(texto):
    return unicodedata.normalize("NFKD", texto)\
        .encode("ascii", "ignore")\
        .decode("ascii")\
        .lower()\
        .strip()

# ======================
# CREAR CRÉDITO (BD)
# ======================
@creditos_bp.route("/crear", methods=["POST"])
def crear_credito():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    cliente = request.form.get("cliente")
    monto = float(request.form.get("monto", 0))

    if not cliente or monto <= 0:
        return redirect(url_for("creditos.index"))

    conn = get_db()
    cur = conn.cursor()

    numero_factura = datetime.now().strftime("YS-%Y%m%d%H%M%S")

    cur.execute("""
        INSERT INTO creditos
        (numero_factura, cliente, monto, abonado, pendiente, estado, fecha)
        VALUES (%s, %s, %s, 0, %s, 'Pendiente', %s)
    """, (
        numero_factura,
        cliente,
        monto,
        monto,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    conn.commit()
    cur.close()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Creó crédito para {cliente}",
        modulo="Créditos"
    )

    return redirect(url_for("creditos.index"))

# ======================
# LISTAR + FILTRAR
# ======================
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
        filtro = normalizar(filtro_cliente)
        creditos = [
            c for c in creditos
            if normalizar(c["cliente"]) == filtro
        ]

    return render_template(
        "creditos/index.html",
        creditos=creditos,
        clientes=clientes,
        filtro_cliente=filtro_cliente
    )

# ======================
# ABONAR CRÉDITO (BD)
# ======================
@creditos_bp.route("/abonar/<int:index>", methods=["POST"])
def abonar(index):
    if session.get("rol") != "admin":
        return redirect(url_for("creditos.index"))

    creditos = cargar_creditos()
    if index < 0 or index >= len(creditos):
        return redirect(url_for("creditos.index"))

    credito = creditos[index]

    try:
        monto = float(request.form.get("monto", 0))
    except ValueError:
        return redirect(url_for("creditos.index"))

    if monto <= 0 or monto > credito["pendiente"]:
        return redirect(url_for("creditos.index"))

    nuevo_abonado = credito["abonado"] + monto
    nuevo_pendiente = credito["pendiente"] - monto
    estado = "Pagado" if nuevo_pendiente == 0 else "Pendiente"

    conn = get_db()
    cur = conn.cursor()

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
        credito["numero_factura"]
    ))

    conn.commit()
    cur.close()
    conn.close()

    registrar_log(
        usuario=session.get("usuario", "admin"),
        accion=f"Abonó ${monto:.2f} al crédito {credito['numero_factura']}",
        modulo="Créditos"
    )

    return redirect(url_for("creditos.index"))

# ======================
# PDF DEL CRÉDITO
# ======================
@creditos_bp.route("/pdf/<int:index>")
def pdf_credito(index):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    creditos = cargar_creditos()
    if index < 0 or index >= len(creditos):
        return redirect(url_for("creditos.index"))

    c = creditos[index]

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
        ["Factura", c["numero_factura"]],
        ["Cliente", c["cliente"]],
        ["Fecha", c["fecha"]],
        ["Monto", f"${c['monto']:,.2f}"],
        ["Abonado", f"${c['abonado']:,.2f}"],
        ["Pendiente", f"${c['pendiente']:,.2f}"],
    ]

    tabla = Table(data, colWidths=[150, 300])
    tabla.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold")
    ]))

    elementos.append(tabla)
    doc.build(elementos)

    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"credito_{c['numero_factura']}.pdf"
    )

# ======================
# ELIMINAR CRÉDITO (BD)
# ======================
@creditos_bp.route("/eliminar/<int:index>")
def eliminar(index):
    if session.get("rol") != "admin":
        return redirect(url_for("creditos.index"))

    creditos = cargar_creditos()
    if index < 0 or index >= len(creditos):
        return redirect(url_for("creditos.index"))

    numero_factura = creditos[index]["numero_factura"]

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM creditos WHERE numero_factura = %s", (numero_factura,))
    conn.commit()
    cur.close()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Eliminó crédito {numero_factura}",
        modulo="Créditos"
    )

    return redirect(url_for("creditos.index"))
