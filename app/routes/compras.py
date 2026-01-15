# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, request, redirect, url_for, session
from datetime import datetime

from app.routes.productos import cargar_productos
from app.db import get_db
from app.utils.auditoria import registrar_log

compras_bp = Blueprint("compras", __name__, url_prefix="/compras")

# ======================
# CARGAR COMPRAS
# ======================
def cargar_compras():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS compras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_producto INTEGER,
            producto TEXT,
            cantidad INTEGER,
            costo REAL,
            total REAL,
            tipo_pago TEXT,
            abonado REAL,
            pendiente REAL,
            fecha TEXT
        )
    """)
    compras = conn.execute(
        "SELECT * FROM compras ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return compras

# ======================
# LISTAR
# ======================
@compras_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    productos = cargar_productos()
    compras = cargar_compras()

    filtro_tipo_pago = request.args.get("tipo_pago", "")

    compras_filtradas = []
    for c in compras:
        if filtro_tipo_pago and c["tipo_pago"] != filtro_tipo_pago:
            continue
        compras_filtradas.append(c)

    return render_template(
        "compras/index.html",
        productos=productos,
        compras=compras_filtradas,
        filtro_tipo_pago=filtro_tipo_pago
    )

# ======================
# AGREGAR
# ======================
@compras_bp.route("/agregar", methods=["POST"])
def agregar():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    producto_id = int(request.form["id"])
    cantidad = int(request.form["cantidad"])
    costo = float(request.form["costo"])
    tipo_pago = request.form.get("tipo_pago", "contado")
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    productos = cargar_productos()
    producto = next((p for p in productos if p["id"] == producto_id), None)

    total = cantidad * costo
    abonado = total if tipo_pago == "contado" else 0
    pendiente = 0 if tipo_pago == "contado" else total

    conn = get_db()

    conn.execute("""
        UPDATE productos
        SET cantidad = cantidad + ?
        WHERE id = ?
    """, (cantidad, producto_id))

    conn.execute("""
        INSERT INTO compras
        (id_producto, producto, cantidad, costo, total,
         tipo_pago, abonado, pendiente, fecha)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        producto_id,
        producto["nombre"],
        cantidad,
        costo,
        total,
        tipo_pago,
        abonado,
        pendiente,
        fecha
    ))

    conn.commit()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Compra {tipo_pago}: {producto['nombre']} (${total})",
        modulo="Compras"
    )

    return redirect(url_for("compras.index"))

# ======================
# ABONAR
# ======================
@compras_bp.route("/abonar/<int:id>", methods=["POST"])
def abonar(id):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    monto = float(request.form["monto"])
    conn = get_db()

    compra = conn.execute(
        "SELECT * FROM compras WHERE id = ?",
        (id,)
    ).fetchone()

    if not compra:
        conn.close()
        return redirect(url_for("compras.index"))

    nuevo_abonado = compra["abonado"] + monto
    nuevo_pendiente = max(0, compra["total"] - nuevo_abonado)

    conn.execute("""
        UPDATE compras
        SET abonado = ?, pendiente = ?
        WHERE id = ?
    """, (nuevo_abonado, nuevo_pendiente, id))

    conn.commit()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Abono ${monto} a compra #{id}",
        modulo="Compras"
    )

    return redirect(url_for("compras.index"))

# ======================
# ELIMINAR
# ======================
@compras_bp.route("/eliminar/<int:id>", methods=["POST"])
def eliminar(id):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    compra = conn.execute(
        "SELECT * FROM compras WHERE id = ?",
        (id,)
    ).fetchone()

    conn.execute("""
        UPDATE productos
        SET cantidad = cantidad - ?
        WHERE id = ?
    """, (compra["cantidad"], compra["id_producto"]))

    conn.execute("DELETE FROM compras WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Compra eliminada: {compra['producto']}",
        modulo="Compras"
    )

    return redirect(url_for("compras.index"))
@compras_bp.route("/editar/<int:id>")
def editar(id):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    compra = conn.execute(
        "SELECT * FROM compras WHERE id = ?",
        (id,)
    ).fetchone()
    conn.close()

    return render_template("compras/editar.html", compra=dict(compra))
# ======================
# ACTUALIZAR COMPRA
# ======================
@compras_bp.route("/actualizar/<int:id>", methods=["POST"])
def actualizar(id):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    nueva_cantidad = int(request.form["cantidad"])
    nuevo_costo = float(request.form["costo"])
    nuevo_total = nueva_cantidad * nuevo_costo

    conn = get_db()

    compra = conn.execute(
        "SELECT * FROM compras WHERE id = ?",
        (id,)
    ).fetchone()

    if not compra:
        conn.close()
        return redirect(url_for("compras.index"))

    # Ajustar stock según diferencia
    diferencia = nueva_cantidad - compra["cantidad"]

    conn.execute("""
        UPDATE productos
        SET cantidad = cantidad + ?
        WHERE id = ?
    """, (diferencia, compra["id_producto"]))

    # Recalcular pagos
    if compra["tipo_pago"] == "contado":
        abonado = nuevo_total
        pendiente = 0
    else:
        abonado = min(compra["abonado"], nuevo_total)
        pendiente = nuevo_total - abonado

    conn.execute("""
        UPDATE compras
        SET cantidad = ?, costo = ?, total = ?, abonado = ?, pendiente = ?
        WHERE id = ?
    """, (
        nueva_cantidad,
        nuevo_costo,
        nuevo_total,
        abonado,
        pendiente,
        id
    ))

    conn.commit()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Compra actualizada #{id}",
        modulo="Compras"
    )

    return redirect(url_for("compras.index"))
