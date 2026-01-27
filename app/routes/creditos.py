# -*- coding: utf-8 -*-
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, send_file
)
import json
import os
from datetime import datetime
from io import BytesIO

from app.utils.auditoria import registrar_log
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph,
    Table, TableStyle, Image
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

creditos_bp = Blueprint("creditos", __name__, url_prefix="/creditos")

DATA_FILE = "app/data/creditos.json"

# ======================
# UTILIDADES
# ======================
def cargar_creditos():
    if not os.path.exists(DATA_FILE) or os.stat(DATA_FILE).st_size == 0:
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_creditos(creditos):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(creditos, f, indent=4, ensure_ascii=False)

# ======================
# CREAR CRÉDITO
# ======================
@creditos_bp.route("/crear", methods=["POST"])
def crear_credito():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    creditos = cargar_creditos()

    cliente = request.form.get("cliente")
    productos = json.loads(request.form.get("productos"))  # viene del frontend

    monto = sum(p["cantidad"] * p["precio"] for p in productos)

    nuevo_credito = {
        "cliente": cliente,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "monto": monto,
        "abonado": 0.0,
        "pendiente": monto,
        "productos": productos,
        "numero_factura": f"YS-{len(creditos)+1:05d}"
    }

    creditos.append(nuevo_credito)
    guardar_creditos(creditos)

    registrar_log(
        usuario=session["usuario"],
        accion=f"Creó crédito para {cliente}",
        modulo="Créditos"
    )

    return redirect(url_for("creditos.index"))

# ======================
# LISTAR + FILTRAR CRÉDITOS
# ======================
@creditos_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    creditos = cargar_creditos()

    clientes = sorted({
        c.get("cliente", "").strip()
        for c in creditos
        if c.get("cliente")
    })

    filtro_cliente = request.args.get("cliente", "").strip()

    if filtro_cliente:
        creditos = [
            c for c in creditos
            if c.get("cliente") == filtro_cliente
        ]

    return render_template(
        "creditos/index.html",
        creditos=creditos,
        clientes=clientes,
        filtro_cliente=filtro_cliente
    )

# ======================
# ABONAR CRÉDITO
# ======================
@creditos_bp.route("/abonar/<int:index>", methods=["POST"])
def abonar(index):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    creditos = cargar_creditos()

    if index < 0 or index >= len(creditos):
        return redirect(url_for("creditos.index"))

    try:
        monto = float(request.form.get("monto", 0))
    except ValueError:
        return redirect(url_for("creditos.index"))

    credito = creditos[index]

    if monto <= 0 or monto > credito.get("pendiente", 0):
        return redirect(url_for("creditos.index"))

    credito["abonado"] += monto
    credito["pendiente"] -= monto
    credito["fecha"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    guardar_creditos(creditos)

    registrar_log(
        usuario=session["usuario"],
        accion=f"Abonó ${monto:.2f} al crédito de {credito.get('cliente','')}",
        modulo="Créditos"
    )

    return redirect(url_for("creditos.index"))

# ======================
# PDF DETALLADO DEL CRÉDITO
# ======================
@creditos_bp.route("/pdf/<int:index>")
def pdf_credito(index):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    creditos = cargar_creditos()

    if index < 0 or index >= len(creditos):
        return redirect(url_for("creditos.index"))

    credito = creditos[index]
    productos = credito.get("productos", [])

    cliente = credito.get("cliente", "")
    fecha = credito.get("fecha", "")
    monto = credito.get("monto", 0)
    abonado = credito.get("abonado", 0)
    pendiente = credito.get("pendiente", 0)

    numero_factura = credito.get(
        "numero_factura",
        f"YS-{index+1:05d}"
    )

    # 🔥 PDF EN MEMORIA (Render safe)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elementos = []

    # LOGO
    logo_path = "app/static/logo.png"
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=90, height=60)
        logo.hAlign = "CENTER"
        elementos.append(logo)
        elementos.append(Paragraph("<br/>", styles["Normal"]))

    # TITULOS
    elementos.append(Paragraph("<b>Yolenny Store</b>", styles["Heading1"]))
    elementos.append(Paragraph("<b>COMPROBANTE DE CRÉDITO</b><br/>", styles["Heading2"]))

    # DATOS DEL CRÉDITO
    data_credito = [
        ["N° Factura", numero_factura],
        ["Cliente", cliente],
        ["Fecha", fecha],
        ["Monto Total", f"${monto:,.2f}"],
        ["Abonado", f"${abonado:,.2f}"],
        ["Pendiente", f"${pendiente:,.2f}"],
    ]

    tabla_credito = Table(data_credito, colWidths=[150, 300])
    tabla_credito.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ]))

    elementos.append(tabla_credito)

    # PRODUCTOS
    elementos.append(Paragraph("<br/><b>Detalle de Productos</b><br/>", styles["Heading3"]))

    data_productos = [["Producto", "Cantidad", "Precio Unit.", "Subtotal"]]
    total = 0

    for p in productos:
        subtotal = p["cantidad"] * p["precio"]
        total += subtotal
        data_productos.append([p["nombre"], str(p["cantidad"]), f"${p['precio']:,.2f}", f"${subtotal:,.2f}"])

    if not productos:
        data_productos.append(["Sin productos", "", "", ""])

    tabla_productos = Table(data_productos, colWidths=[200, 80, 100, 100])
    tabla_productos.setStyle(TableStyle([  # <- Cambio a lista
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))

   

    elementos.append(tabla_productos)

    elementos.append(
        Paragraph(f"<br/><b>Total Productos: ${total:,.2f}</b><br/>", styles["Normal"])
    )

    elementos.append(
        Paragraph("Firma del Cliente: ________________________________", styles["Normal"])
    )

    doc.build(elementos)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"credito_{numero_factura}.pdf"
    )

# ======================
# ELIMINAR CRÉDITO (ADMIN)
# ======================
@creditos_bp.route("/eliminar/<int:index>")
def eliminar(index):
    if session.get("rol") != "admin":
        return redirect(url_for("creditos.index"))

    creditos = cargar_creditos()

    if index < 0 or index >= len(creditos):
        return redirect(url_for("creditos.index"))

    eliminado = creditos.pop(index)
    guardar_creditos(creditos)

    registrar_log(
        usuario=session["usuario"],
        accion=f"Eliminó crédito de {eliminado.get('cliente','')}",
        modulo="Créditos"
    )

    return redirect(url_for("creditos.index"))
@ventas_bp.route("/factura/numero/<numero>")
def factura_por_numero(numero):
    ventas = cargar_json(VENTAS_FILE)

    venta = next(
        (v for v in ventas if v.get("numero_factura") == numero),
        None
    )

    if not venta:
        return redirect(url_for("ventas.index"))

    index = ventas.index(venta)
    return redirect(url_for("ventas.factura", index=index))
