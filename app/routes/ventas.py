# -*- coding: utf-8 -*-

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, send_file
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
# CONFIGURACIÓN
# ======================
NOMBRE_EMPRESA = "Yolenny Store"

ventas_bp = Blueprint("ventas", __name__, url_prefix="/ventas")

VENTAS_FILE = "app/data/ventas.json"
CARRITO_FILE = "app/data/carrito.json"
CREDITOS_FILE = "app/data/creditos.json"

def normalizar_pago(tipo):
    if not tipo:
        return "contado"

    tipo = tipo.lower().strip()
    tipo = tipo.replace("é", "e")

    if "credit" in tipo:
        return "credito"
    return "contado"

# ======================
# UTILIDADES JSON
# ======================
def cargar_json(ruta):
    if not os.path.exists(ruta):
        return []
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)

def cargar_ventas_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM ventas
        ORDER BY fecha DESC
    """)

    ventas = cur.fetchall()
    cur.close()
    conn.close()
    return ventas

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

    # ======================
    # DATOS BASE
    # ======================
    productos = cargar_productos()
    categorias = cargar_categorias()
    clientes = cargar_clientes()

    # Carrito (SE MANTIENE EN JSON)
    carrito = cargar_json(CARRITO_FILE)
    total_carrito = sum(i["total"] for i in carrito)

    # ======================
    # VENTAS DESDE LA BD
    # ======================
    conn = get_db()
    cur = conn.cursor()

    # 🔹 Ventas CONTADO
    cur.execute("""
        SELECT
            numero_factura,
            cliente,
            'Contado' AS tipo,
            MAX(fecha) AS fecha,
            SUM(total) AS total,
            FALSE AS eliminado
        FROM ventas
        WHERE tipo = 'contado'
          AND eliminado = FALSE
        GROUP BY numero_factura, cliente
        ORDER BY fecha DESC
    """)

    ventas_contado = cur.fetchall()

    # 🔹 Ventas CRÉDITO
    cur.execute("""
        SELECT
            cliente,
            'Crédito' AS tipo,
            fecha,
            monto AS total,
            numero_factura
        FROM creditos
        WHERE eliminado = FALSE
        ORDER BY fecha DESC
    """)
    ventas_credito = cur.fetchall()
    
    cur.execute("""
        SELECT
            numero_factura,
            cliente,
            tipo,
            eliminado,
            MAX(fecha) AS fecha,
            SUM(total) AS total
        FROM ventas
        GROUP BY numero_factura, cliente, eliminado, tipo
        ORDER BY fecha DESC
    """)
    ventas = cur.fetchall()

    ventas_eliminadas = cur.fetchall()

    cur.close()
    conn.close()

    # 🔥 UNIFICAR TODAS LAS VENTAS
    ventas = ventas_contado + ventas_credito

    # ======================
    # RENDER
    # ======================
    return render_template(
        "ventas/index.html",
        productos=productos,
        categorias=categorias,
        clientes=clientes,
        carrito=carrito,
        ventas=ventas,
        ventas_eliminadas=ventas_eliminadas,  # 👈 ESTA ES LA CLAVE
        total=total_carrito
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
# ✏️ EDITAR PRECIO
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
# CONFIRMAR VENTA (CONTADO / CRÉDITO)
# ======================
@ventas_bp.route("/confirmar", methods=["POST"])
def confirmar():
    carrito = cargar_json(CARRITO_FILE)

    if not carrito:
        return redirect(url_for("ventas.index"))

    cliente_manual = request.form.get("cliente_manual", "").strip()
    cliente_select = request.form.get("cliente_select", "").strip()

    cliente = cliente_manual or cliente_select or "Público General"

    tipo_venta_raw = request.form.get("tipo_venta", "Contado")
    tipo_pago = normalizar_pago(tipo_venta_raw)

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = sum(i["total"] for i in carrito)
    numero_factura = f"YS-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # ✅ ABONO INICIAL (NUEVO)
    abono = float(request.form.get("abono", 0) or 0)
    if abono < 0:
        abono = 0
    if abono > total:
        abono = total

    pendiente = total - abono
    estado = "Pagado" if pendiente == 0 else "Pendiente"

    conn = get_db()
    cur = conn.cursor()

    # ======================
    # GUARDAR VENTAS
    # ======================
    for item in carrito:
        cur.execute("""
            INSERT INTO ventas
            (numero_factura, cliente, tipo, id_producto, producto, cantidad, precio, total, fecha)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            numero_factura,
            cliente,
            tipo_pago,
            item["id"],
            item["nombre"],
            item["cantidad"],
            item["precio"],
            item["total"],
            fecha
        ))

        # DESCONTAR STOCK
        cur.execute("""
            UPDATE productos
            SET cantidad = cantidad - %s
            WHERE id = %s
        """, (item["cantidad"], item["id"]))

    # ======================
    # REGISTRAR CRÉDITO (CORREGIDO)
    # ======================
    if tipo_pago == "credito":
        cur.execute("""
            INSERT INTO creditos
            (numero_factura, cliente, monto, abonado, pendiente, estado, fecha)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            numero_factura,
            cliente,
            total,
            abono,        # ✅ ABONADO REAL
            pendiente,    # ✅ PENDIENTE REAL
            estado,       # ✅ ESTADO CORRECTO
            fecha
        ))

    conn.commit()
    cur.close()
    conn.close()

    guardar_json(CARRITO_FILE, [])

    registrar_log(
        usuario=session.get("usuario", "sistema"),
        accion=f"Venta {numero_factura} ({tipo_venta_raw})",
        modulo="Ventas"
    )

    return redirect(url_for("ventas.index"))

# ======================
# 🧾 FACTURA PDF TÉRMICA
# ======================
@ventas_bp.route("/factura/<numero_factura>")
def factura(numero_factura):
    conn = get_db()
    cur = conn.cursor()

    # ======================
    # ITEMS DE LA FACTURA
    # ======================
    cur.execute("""
        SELECT producto, cantidad, precio, total, fecha
        FROM ventas
        WHERE numero_factura = %s
        ORDER BY id
    """, (numero_factura,))
    items = cur.fetchall()

    # ======================
    # DATOS GENERALES DE LA VENTA
    # ======================
    cur.execute("""
        SELECT cliente, tipo, fecha
        FROM ventas
        WHERE numero_factura = %s
        LIMIT 1
    """, (numero_factura,))
    venta = cur.fetchone()

    # 🔹 SI ES CRÉDITO, BUSCAR ABONO Y PENDIENTE
    abono = 0
    pendiente = 0

    if venta["tipo"] == "credito":
        cur.execute("""
            SELECT abonado, pendiente
            FROM creditos
            WHERE numero_factura = %s
        """, (numero_factura,))
        credito = cur.fetchone()

        if credito:
            abono = float(credito["abonado"])
            pendiente = float(credito["pendiente"])


    cur.close()
    conn.close()

    if not items or not venta:
        return redirect(url_for("ventas.index"))

    cliente = venta["cliente"]
    tipo = "Crédito" if venta["tipo"] == "credito" else "Contado"
    fecha = venta["fecha"]
    total = sum(i["total"] for i in items)

    # ======================
    # PDF TÉRMICO
    # ======================
    buffer = BytesIO()
    ANCHO, ALTO = 165, 800
    c = canvas.Canvas(buffer, pagesize=(ANCHO, ALTO))
    y = ALTO - 20

    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(ANCHO / 2, y, NOMBRE_EMPRESA)
    y -= 15

    c.setFont("Helvetica", 7)
    c.drawCentredString(ANCHO / 2, y, "Moda y estilo que te acompaña")
    y -= 15

    c.line(5, y, ANCHO - 5, y)
    y -= 10

    c.drawString(5, y, f"Factura: {numero_factura}")
    y -= 10
    c.drawString(5, y, f"Cliente: {cliente}")
    y -= 10
    c.drawString(5, y, f"Tipo: {tipo}")
    y -= 10
    c.drawString(5, y, f"Fecha: {fecha}")
    y -= 10

    # 🔹 MOSTRAR ABONO SOLO SI ES CRÉDITO
    if tipo == "Crédito":
        c.drawString(5, y, f"Abono: ${abono:,.2f}")
        y -= 10
        c.drawString(5, y, f"Pendiente: ${pendiente:,.2f}")
        y -= 10

    y -= 5

    c.line(5, y, ANCHO - 5, y)
    y -= 10

    c.setFont("Helvetica", 7)
    for i in items:
        c.drawString(5, y, i["producto"][:18])
        y -= 9
        c.drawString(10, y, f'{i["cantidad"]} x ${i["precio"]}')
        c.drawRightString(ANCHO - 5, y, f'${i["total"]}')
        y -= 10

    c.line(5, y, ANCHO - 5, y)
    y -= 12

    c.setFont("Helvetica-Bold", 8)
    c.drawString(5, y, "TOTAL:")
    c.drawRightString(ANCHO - 5, y, f"${total}")
    y -= 18

    c.line(5, y, ANCHO - 5, y)
    y -= 15

    c.setFont("Helvetica", 7)
    c.drawCentredString(ANCHO / 2, y, "Gracias por su compra")
    y -= 10
    c.drawCentredString(ANCHO / 2, y, "Conserve este comprobante")

    c.save()

    buffer.seek(0)
    return send_file(
        buffer,
        download_name=f"factura_{numero_factura}.pdf",
        as_attachment=True,
        mimetype="application/pdf"
    )

# ======================
# 🗑 ELIMINAR FACTURA
# ======================
@ventas_bp.route("/eliminar/<numero_factura>")
def eliminar_factura(numero_factura):
    if session.get("rol") != "admin":
        return redirect(url_for("ventas.index"))

    conn = get_db()
    cur = conn.cursor()

    # ======================
    # 1️⃣ VERIFICAR SI YA ESTÁ ELIMINADA
    # ======================
    cur.execute("""
        SELECT eliminado
        FROM ventas
        WHERE numero_factura = %s
        LIMIT 1
    """, (numero_factura,))
    venta = cur.fetchone()

    if not venta or venta["eliminado"]:
        # Ya estaba eliminada → no tocar stock otra vez
        cur.close()
        conn.close()
        return redirect(url_for("ventas.index"))

    # ======================
    # 2️⃣ OBTENER ITEMS DE LA VENTA
    # ======================
    cur.execute("""
        SELECT id_producto, cantidad
        FROM ventas
        WHERE numero_factura = %s
    """, (numero_factura,))
    items = cur.fetchall()

    # ======================
    # 3️⃣ DEVOLVER STOCK
    # ======================
    for item in items:
        cur.execute("""
            UPDATE productos
            SET cantidad = cantidad + %s
            WHERE id = %s
        """, (item["cantidad"], item["id_producto"]))

    # ======================
    # 4️⃣ MARCAR COMO ELIMINADA (SOFT DELETE)
    # ======================
    cur.execute("""
        UPDATE ventas
        SET eliminado = TRUE
        WHERE numero_factura = %s
    """, (numero_factura,))


    cur.execute("""
        UPDATE creditos
        SET eliminado = TRUE
        WHERE numero_factura = %s
    """, (numero_factura,))


    conn.commit()
    cur.close()
    conn.close()

    registrar_log(
        usuario=session.get("usuario"),
        accion=f"Venta {numero_factura} eliminada y stock devuelto",
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

    conn = get_db()
    cur = conn.cursor()

    # 1️⃣ Devolver stock
    cur.execute("""
        SELECT id_producto, cantidad
        FROM ventas
    """)
    items = cur.fetchall()

    for i in items:
        cur.execute("""
            UPDATE productos
            SET cantidad = cantidad + %s
            WHERE id = %s
        """, (i["cantidad"], i["id_producto"]))

    # 2️⃣ Eliminar ventas
    cur.execute("DELETE FROM ventas")

    # 3️⃣ Eliminar créditos
    cur.execute("DELETE FROM creditos")

    conn.commit()
    cur.close()
    conn.close()

    registrar_log(
        usuario=session.get("usuario"),
        accion="Eliminó TODAS las ventas",
        modulo="Ventas"
    )

    return redirect(url_for("ventas.index"))

# ======================
# ❌ ELIMINAR ITEM DEL CARRITO
# ======================
@ventas_bp.route("/eliminar_item/<int:producto_id>")
def eliminar_item(producto_id):
    carrito = cargar_json(CARRITO_FILE)

    carrito = [i for i in carrito if i["id"] != producto_id]

    guardar_json(CARRITO_FILE, carrito)

    return redirect(url_for("ventas.index"))
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
@ventas_bp.route("/abonar/<numero_factura>", methods=["POST"])
def abonar_desde_ventas(numero_factura):
    if "usuario" not in session or session.get("rol") != "admin":
        return redirect(url_for("ventas.index"))

    abono = float(request.form.get("abono", 0))
    if abono <= 0:
        return redirect(url_for("ventas.index"))

    fecha_abono = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = get_db()
    cur = conn.cursor()

    # Obtener crédito
    cur.execute("""
        SELECT abonado, pendiente
        FROM creditos
        WHERE numero_factura = %s
    """, (numero_factura,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return redirect(url_for("ventas.index"))

    abonado = float(row["abonado"])
    pendiente = float(row["pendiente"])

    if abono > pendiente:
        abono = pendiente

    nuevo_abonado = abonado + abono
    nuevo_pendiente = pendiente - abono
    estado = "Pagado" if nuevo_pendiente == 0 else "Pendiente"

    cur.execute("""
        UPDATE creditos
        SET abonado = %s,
            pendiente = %s,
            estado = %s,
            fecha_ultimo_abono = %s
        WHERE numero_factura = %s
    """, (
        nuevo_abonado,
        nuevo_pendiente,
        estado,
        fecha_abono,
        numero_factura
    ))

    conn.commit()
    cur.close()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Abono RD${abono:,.2f} a factura {numero_factura}",
        modulo="Ventas"
    )

    return redirect(url_for("ventas.index"))
@ventas_bp.route("/recuperar/<numero_factura>")
def recuperar_venta(numero_factura):
    if session.get("rol") != "admin":
        return redirect(url_for("ventas.index"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE ventas
        SET eliminado = FALSE
        WHERE numero_factura = %s
    """, (numero_factura,))

    cur.execute("""
        UPDATE creditos
        SET eliminado = FALSE
        WHERE numero_factura = %s
    """, (numero_factura,))

    conn.commit()
    cur.close()
    conn.close()

    registrar_log(
        usuario=session.get("usuario"),
        accion=f"Venta {numero_factura} recuperada",
        modulo="Ventas"
    )

    return redirect(url_for("ventas.index"))
