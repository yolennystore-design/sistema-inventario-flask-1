# -*- coding: utf-8 -*-

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, send_file
)
import json
from io import BytesIO
import os
from app.utils.google_drive import subir_pdf_a_drive
import tempfile
from datetime import datetime

from app.routes.productos import cargar_productos
from app.routes.clientes import cargar_clientes
from app.routes.categorias import cargar_categorias
from app.utils.auditoria import registrar_log
from app.db import get_db

from reportlab.pdfgen import canvas


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

    filtro_nombre = request.args.get("nombre", "").lower()
    filtro_categoria = request.args.get("categoria", "")
    filtro_subcategoria = request.args.get("subcategoria", "")
    filtro_item = request.args.get("item", "")

    productos_filtrados = []
    for p in productos:
        if filtro_nombre and filtro_nombre not in p["nombre"].lower():
            continue
        if filtro_categoria and p["categoria"] != filtro_categoria:
            continue
        if filtro_subcategoria and p["subcategoria"] != filtro_subcategoria:
            continue
        if filtro_item and p["item"] != filtro_item:
            continue
        productos_filtrados.append(p)

    total = sum(i["total"] for i in carrito)

    return render_template(
        "ventas/index.html",
        productos=productos_filtrados,
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
# ACTUALIZAR PRECIO
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
# CONFIRMAR VENTA
# ======================
@ventas_bp.route("/confirmar", methods=["POST"])
def confirmar():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

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
    cur.close()
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

    if tipo_pago == "credito":
        creditos = cargar_json(CREDITOS_FILE)
        creditos.append({
            "cliente": cliente,
            "fecha": fecha,
            "monto": total,
            "abonado": 0.0,
            "pendiente": total,
            "productos": carrito,
            "numero_factura": numero_factura
        })
        guardar_json(CREDITOS_FILE, creditos)

    registrar_log(
        usuario=session["usuario"],
        accion=f"Venta a {cliente} por ${total}",
        modulo="Ventas"
    )

    return redirect(url_for("ventas.index"))


# ======================
# FACTURA PDF TÉRMICA
# ======================
@ventas_bp.route("/factura/<int:index>")
def factura(index):
    ventas = cargar_json(VENTAS_FILE)
    venta = ventas[index]
    items = obtener_items(venta)

    # 📌 PDF EN MEMORIA (NO ARCHIVO)
    buffer = BytesIO()

    ANCHO = 165  # 58mm
    ALTO = 800
    c = canvas.Canvas(buffer, pagesize=(ANCHO, ALTO))
    y = ALTO - 20

    titulo = "COMPROBANTE DE CRÉDITO" if venta["tipo_pago"] == "credito" else "Moda y estilo que te acompaña"
    numero = venta.get("numero_factura", f"{index + 1}")

    # ENCABEZADO
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(ANCHO / 2, y, NOMBRE_EMPRESA)
    y -= 12

    c.setFont("Helvetica", 8)
    c.drawCentredString(ANCHO / 2, y, titulo)
    y -= 15

    c.line(5, y, ANCHO - 5, y)
    y -= 10

    # DATOS
    c.setFont("Helvetica", 7)
    c.drawString(5, y, f"Factura: {numero}")
    y -= 10
    c.drawString(5, y, f"Cliente: {venta['cliente']}")
    y -= 10
    c.drawString(5, y, f"Fecha: {venta['fecha']}")
    y -= 12

    c.line(5, y, ANCHO - 5, y)
    y -= 10

    # PRODUCTOS
    c.setFont("Helvetica-Bold", 7)
    c.drawString(5, y, "Producto")
    c.drawRightString(ANCHO - 5, y, "Total")
    y -= 10

    c.setFont("Helvetica", 7)
    for item in items:
        c.drawString(5, y, item["nombre"][:18])
        y -= 9
        c.drawString(10, y, f"{item['cantidad']} x ${item['precio']}")
        c.drawRightString(ANCHO - 5, y, f"${item['total']}")
        y -= 10

    c.line(5, y, ANCHO - 5, y)
    y -= 12

    # TOTALES
    abonado = venta.get("abonado", 0)
    pendiente = venta["total"] - abonado

    c.setFont("Helvetica", 8)
    c.drawString(5, y, "TOTAL:")
    c.drawRightString(ANCHO - 5, y, f"${venta['total']}")
    y -= 10

    c.drawString(5, y, "ABONADO:")
    c.drawRightString(ANCHO - 5, y, f"${abonado}")
    y -= 10

    c.setFont("Helvetica-Bold", 8)
    c.drawString(5, y, "PENDIENTE:")
    c.drawRightString(ANCHO - 5, y, f"${pendiente}")
    y -= 15

    c.line(5, y, ANCHO - 5, y)
    y -= 15

    # PIE
    c.setFont("Helvetica", 7)
    c.drawCentredString(ANCHO / 2, y, "Gracias por su compra")
    y -= 10
    c.drawCentredString(ANCHO / 2, y, "Conserve este comprobante")

    c.save()

    # 📌 OBTENER BYTES DEL PDF
    pdf_bytes = buffer.getvalue()
    buffer.close()

    # 📌 SUBIR A GOOGLE DRIVE
    file_id, link = subir_pdf_a_drive(
        nombre_archivo=f"factura_{numero}.pdf",
        pdf_bytes=pdf_bytes,
        folder_id=os.environ["DRIVE_FOLDER_ID"]
    )

    # 👉 OPCIÓN A: redirigir al PDF en Drive
    return redirect(link)

# ======================
# ELIMINAR / CANCELAR
# ======================
@ventas_bp.route("/eliminar/<int:index>")
def eliminar_venta(index):
    if session.get("rol") != "admin":
        return redirect(url_for("ventas.index"))

    ventas = cargar_json(VENTAS_FILE)
    venta = ventas[index]

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

    ventas.pop(index)
    guardar_json(VENTAS_FILE, ventas)

    registrar_log(
        usuario=session["usuario"],
        accion=f"Eliminó venta de {venta['cliente']} por ${venta['total']}",
        modulo="Ventas"
    )

    return redirect(url_for("ventas.index"))


@ventas_bp.route("/cancelar")
def cancelar():
    guardar_json(CARRITO_FILE, [])
    return redirect(url_for("ventas.index"))


@ventas_bp.route("/eliminar_todas")
def eliminar_todas_las_ventas():
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
    guardar_json(CREDITOS_FILE, [])

    registrar_log(
        usuario=session["usuario"],
        accion="Eliminó todas las ventas",
        modulo="Ventas"
    )

    return redirect(url_for("ventas.index"))


# ======================
# SOLICITAR CAMBIO DE PRECIO
# ======================
@ventas_bp.route("/solicitar_precio", methods=["POST"])
def solicitar_precio():
    solicitudes = cargar_json(SOLICITUDES_FILE)

    solicitudes.append({
        "producto_id": int(request.form["id"]),
        "precio_solicitado": float(request.form["precio_solicitado"]),
        "motivo": request.form["motivo"],
        "usuario": session["usuario"],
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    guardar_json(SOLICITUDES_FILE, solicitudes)

    registrar_log(
        usuario=session["usuario"],
        accion="Envió solicitud de cambio de precio",
        modulo="Ventas"
    )

    return redirect(url_for("ventas.index"))
