# -*- coding: utf-8 -*-

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, send_file
)
import json
from io import BytesIO
import os
from datetime import datetime
import tempfile

from reportlab.pdfgen import canvas

from app.routes.productos import cargar_productos
from app.routes.clientes import cargar_clientes
from app.routes.categorias import cargar_categorias
from app.utils.auditoria import registrar_log
from app.db import get_db


# ======================
# GOOGLE DRIVE (SOLO PRODUCCIÓN)
# ======================
if os.getenv("FLASK_ENV") != "development":
    from app.utils.google_drive import subir_pdf_a_drive
else:
    subir_pdf_a_drive = None


NOMBRE_EMPRESA = "Yolenny Store"

ventas_bp = Blueprint("ventas", __name__, url_prefix="/ventas")

VENTAS_FILE = "app/data/ventas.json"
CARRITO_FILE = "app/data/carrito.json"
CREDITOS_FILE = "app/data/creditos.json"
SOLICITUDES_FILE = "app/data/solicitudes_precio.json"


# ======================
# UTILIDADES JSON
# ======================
def cargar_json(ruta):
    if not os.path.exists(ruta) or os.stat(ruta).st_size == 0:
        return []
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_json(ruta, data):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def obtener_items(venta):
    return venta.get("items") or venta.get("elementos") or []


# ======================
# VISTA PRINCIPAL
# ======================
@ventas_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    productos = cargar_productos()
    categorias = cargar_categorias()
    clientes = cargar_clientes()
    carrito = cargar_json(CARRITO_FILE)
    ventas = cargar_json(VENTAS_FILE)

    total = sum(i["total"] for i in carrito)

    return render_template(
        "ventas/index.html",
        productos=productos,
        categorias=categorias,
        clientes=clientes,
        carrito=carrito,
        ventas=ventas,
        total=total
    )


# ======================
# CONFIRMAR VENTA
# ======================
@ventas_bp.route("/confirmar", methods=["POST"])
def confirmar():
    ventas = cargar_json(VENTAS_FILE)
    carrito = cargar_json(CARRITO_FILE)

    if not carrito:
        return redirect(url_for("ventas.index"))

    cliente = request.form["cliente"]
    tipo_pago = request.form.get("tipo_pago", "contado").lower()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = sum(i["total"] for i in carrito)

    conn = get_db()
    cur = conn.cursor()

    for item in carrito:
        cur.execute(
            "UPDATE productos SET cantidad = cantidad - %s WHERE id = %s",
            (item["cantidad"], item["id"])
        )

    conn.commit()
    conn.close()

    numero_factura = f"YS-{len(ventas)+1:05d}"

    venta = {
        "cliente": cliente,
        "tipo_pago": tipo_pago,
        "items": carrito,
        "total": total,
        "fecha": fecha,
        "numero_factura": numero_factura
    }

    ventas.append(venta)

    guardar_json(VENTAS_FILE, ventas)
    guardar_json(CARRITO_FILE, [])

    return redirect(url_for("ventas.index"))


# ======================
# FACTURA PDF (LOCAL / DRIVE)
# ======================
@ventas_bp.route("/factura/<int:index>")
def factura(index):
    ventas = cargar_json(VENTAS_FILE)
    venta = ventas[index]
    items = obtener_items(venta)

    buffer = BytesIO()
    ANCHO, ALTO = 165, 800
    c = canvas.Canvas(buffer, pagesize=(ANCHO, ALTO))
    y = ALTO - 20

    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(ANCHO / 2, y, NOMBRE_EMPRESA)
    y -= 15

    c.setFont("Helvetica", 7)
    c.drawString(5, y, f"Cliente: {venta['cliente']}")
    y -= 10
    c.drawString(5, y, f"Fecha: {venta['fecha']}")
    y -= 15

    for item in items:
        c.drawString(5, y, f"{item['nombre']} x{item['cantidad']}")
        c.drawRightString(ANCHO - 5, y, f"${item['total']}")
        y -= 10

    y -= 10
    c.setFont("Helvetica-Bold", 8)
    c.drawString(5, y, "TOTAL:")
    c.drawRightString(ANCHO - 5, y, f"${venta['total']}")

    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()

    # ======================
    # DESARROLLO → DESCARGA LOCAL
    # ======================
    if not subir_pdf_a_drive:
        return send_file(
            BytesIO(pdf_bytes),
            download_name=f"factura_{venta['numero_factura']}.pdf",
            as_attachment=True,
            mimetype="application/pdf"
        )

    # ======================
    # PRODUCCIÓN → GOOGLE DRIVE
    # ======================
    file_id, link = subir_pdf_a_drive(
        nombre_archivo=f"factura_{venta['numero_factura']}.pdf",
        pdf_bytes=pdf_bytes,
        folder_id=os.environ["DRIVE_FOLDER_ID"]
    )

    return redirect(link)
