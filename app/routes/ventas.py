# -*- coding: utf-8 -*-

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, send_file
)
import json
from io import BytesIO
import os
from datetime import datetime

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
    return venta.get("items", [])


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
# AGREGAR AL CARRITO
# ======================
@ventas_bp.route("/agregar_carrito", methods=["POST"])
def agregar_carrito():
    carrito = cargar_json(CARRITO_FILE)
    productos = cargar_productos()

    producto_id = int(request.form["id"])
    cantidad = int(request.form["cantidad"])

    producto = next((p for p in productos if p["id"] == producto_id), None)
    if not producto or cantidad > producto["cantidad"]:
        return redirect(url_for("ventas.index"))

    for item in carrito:
        if item["id"] == producto_id:
            item["cantidad"] += cantidad
            item["total"] = item["cantidad"] * item["precio"]
            guardar_json(CARRITO_FILE, carrito)
            return redirect(url_for("ventas.index"))

    carrito.append({
        "id": producto["id"],
        "nombre": producto["nombre"],
        "cantidad": cantidad,
        "precio": producto["precio"],
        "total": cantidad * producto["precio"]
    })

    guardar_json(CARRITO_FILE, carrito)
    return redirect(url_for("ventas.index"))


# ======================
# ✏️ EDITAR PRECIO EN CARRITO
# ======================
@ventas_bp.route("/actualizar_precio", methods=["POST"])
def actualizar_precio():
    carrito = cargar_json(CARRITO_FILE)

    producto_id = int(request.form["id"])
    nuevo_precio = float(request.form["precio"])

    for item in carrito:
        if item["id"] == producto_id:
            item["precio"] = nuevo_precio
            item["total"] = item["cantidad"] * nuevo_precio
            break

    guardar_json(CARRITO_FILE, carrito)
    return redirect(url_for("ventas.index"))


# ======================
# 🧹 VACIAR CARRITO
# ======================
@ventas_bp.route("/vaciar_carrito")
def vaciar_carrito():
    guardar_json(CARRITO_FILE, [])
    return redirect(url_for("ventas.index"))


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
    cur.close()
    conn.close()

    numero_factura = f"YS-{len(ventas) + 1:05d}"

    ventas.append({
        "cliente": cliente,
        "items": carrito,
        "total": total,
        "fecha": fecha,
        "numero_factura": numero_factura
    })

    guardar_json(VENTAS_FILE, ventas)
    guardar_json(CARRITO_FILE, [])

    registrar_log(
        usuario=session.get("usuario", "sistema"),
        accion=f"Registró venta {numero_factura}",
        modulo="Ventas"
    )

    return redirect(url_for("ventas.index"))


# ======================
# 🧾 FACTURA PDF
# ======================
@ventas_bp.route("/factura/<int:index>")
def factura(index):
    ventas = cargar_json(VENTAS_FILE)
    if index < 0 or index >= len(ventas):
        return redirect(url_for("ventas.index"))

    venta = ventas[index]
    items = obtener_items(venta)
    numero = venta.get("numero_factura", index + 1)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(165, 800))
    y = 780

    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(82, y, NOMBRE_EMPRESA)
    y -= 15

    c.setFont("Helvetica", 7)
    c.drawString(5, y, f"Factura: {numero}")
    y -= 10
    c.drawString(5, y, f"Cliente: {venta['cliente']}")
    y -= 10
    c.drawString(5, y, f"Fecha: {venta['fecha']}")
    y -= 15

    for i in items:
        c.drawString(5, y, f"{i['nombre']} x{i['cantidad']}")
        c.drawRightString(160, y, f"${i['total']}")
        y -= 10

    y -= 10
    c.setFont("Helvetica-Bold", 8)
    c.drawString(5, y, "TOTAL:")
    c.drawRightString(160, y, f"${venta['total']}")

    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()

    # LOCAL
    if not subir_pdf_a_drive:
        return send_file(
            BytesIO(pdf_bytes),
            download_name=f"factura_{numero}.pdf",
            as_attachment=True,
            mimetype="application/pdf"
        )

    # PRODUCCIÓN (Drive)
    _, link = subir_pdf_a_drive(
        f"factura_{numero}.pdf",
        pdf_bytes,
        os.environ["DRIVE_FOLDER_ID"]
    )

    return redirect(link)


# ======================
# 🗑 ELIMINAR UNA FACTURA
# ======================
@ventas_bp.route("/eliminar/<int:index>")
def eliminar_factura(index):
    if session.get("rol") != "admin":
        return redirect(url_for("ventas.index"))

    ventas = cargar_json(VENTAS_FILE)
    if index < 0 or index >= len(ventas):
        return redirect(url_for("ventas.index"))

    venta = ventas.pop(index)

    conn = get_db()
    cur = conn.cursor()

    for item in obtener_items(venta):
        cur.execute(
            "UPDATE productos SET cantidad = cantidad + %s WHERE id = %s",
            (item["cantidad"], item["id"])
        )

    conn.commit()
    cur.close()
    conn.close()

    guardar_json(VENTAS_FILE, ventas)

    registrar_log(
        usuario=session["usuario"],
        accion=f"Eliminó factura {venta.get('numero_factura')}",
        modulo="Ventas"
    )

    return redirect(url_for("ventas.index"))


# ======================
# ❌ ELIMINAR TODAS LAS VENTAS
# ======================
@ventas_bp.route("/eliminar_todas")
def eliminar_todas():
    if session.get("rol") != "admin":
        return redirect(url_for("ventas.index"))

    ventas = cargar_json(VENTAS_FILE)

    conn = get_db()
    cur = conn.cursor()

    for venta in ventas:
        for item in obtener_items(venta):
            cur.execute(
                "UPDATE productos SET cantidad = cantidad + %s WHERE id = %s",
                (item["cantidad"], item["id"])
            )

    conn.commit()
    cur.close()
    conn.close()

    guardar_json(VENTAS_FILE, [])
    guardar_json(CARRITO_FILE, [])

    registrar_log(
        usuario=session["usuario"],
        accion="Eliminó todas las ventas",
        modulo="Ventas"
    )

    return redirect(url_for("ventas.index"))
