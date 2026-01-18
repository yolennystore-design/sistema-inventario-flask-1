# -*- coding: utf-8 -*-

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, send_file
)
import json
import os
import tempfile
from datetime import datetime

from app.routes.productos import cargar_productos
from app.routes.clientes import cargar_clientes
from app.routes.categorias import cargar_categorias
from app.utils.auditoria import registrar_log
from app.db import get_db

from reportlab.lib.pagesizes import letter
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

    ventas_filtradas = ventas
    total = sum(i["total"] for i in carrito)

    return render_template(
        "ventas/index.html",
        productos=productos_filtrados,
        categorias=categorias,
        clientes=clientes,
        carrito=carrito,
        ventas=ventas_filtradas,
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

    ventas.append({
        "cliente": cliente,
        "tipo_pago": tipo_pago,
        "items": carrito,
        "total": total,
        "fecha": fecha
    })

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
            "numero_factura": f"YS-{len(creditos)+1:05d}"
        })

        guardar_json(CREDITOS_FILE, creditos)

    registrar_log(
        usuario=session["usuario"],
        accion=f"Venta a {cliente} por ${total}",
        modulo="Ventas"
    )

    return redirect(url_for("ventas.index"))


# ======================
# FACTURA PDF
# ======================
@ventas_bp.route("/factura/<int:index>")
def factura(index):
    ventas = cargar_json(VENTAS_FILE)
    venta = ventas[index]
    items = obtener_items(venta)

    archivo = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(archivo.name, pagesize=letter)

    y = 750
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(300, y, NOMBRE_EMPRESA)

    y -= 40
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Cliente: {venta['cliente']}")
    y -= 15
    c.drawString(50, y, f"Fecha: {venta['fecha']}")
    y -= 25

    for item in items:
        c.drawString(
            50, y,
            f"{item['nombre']} x{item['cantidad']} - ${item['total']}"
        )
        y -= 15

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, f"TOTAL: ${venta['total']}")

    c.save()
    return send_file(archivo.name, as_attachment=False)


# ======================
# ELIMINAR VENTA
# ======================
@ventas_bp.route("/eliminar/<int:index>")
def eliminar_venta(index):
    if session.get("rol") != "admin":
        return redirect(url_for("ventas.index"))

    ventas = cargar_json(VENTAS_FILE)
    venta = ventas[index]
    items = obtener_items(venta)

    conn = get_db()
    cur = conn.cursor()

    for item in items:
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


# ======================
# CANCELAR VENTA
# ======================
@ventas_bp.route("/cancelar")
def cancelar():
    guardar_json(CARRITO_FILE, [])
    return redirect(url_for("ventas.index"))


# ======================
# ELIMINAR TODAS
# ======================
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
