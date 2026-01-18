# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, request, redirect, url_for, session
from app.db import get_db
from app.utils.auditoria import registrar_log

compras_bp = Blueprint("compras", __name__, url_prefix="/compras")

# ======================
# CARGAR COMPRAS
# ======================
def cargar_compras():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM compras
        ORDER BY id DESC
    """)
    compras = cur.fetchall()

    cur.close()
    conn.close()
    return compras


# ======================
# CARGAR PRODUCTOS (CON STOCK)
# ======================
def cargar_productos():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nombre, cantidad
        FROM productos
        ORDER BY nombre
    """)
    productos = cur.fetchall()

    cur.close()
    conn.close()
    return productos


# ======================
# LISTAR COMPRAS
# ======================
@compras_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    compras = cargar_compras()
    productos = cargar_productos()

    return render_template(
        "compras/index.html",
        compras=compras,
        productos=productos
    )


# ======================
# AGREGAR COMPRA
# ======================
@compras_bp.route("/agregar", methods=["POST"])
def agregar():
    if session.get("rol") != "admin":
        return redirect(url_for("compras.index"))

    id_producto = int(request.form["id_producto"])
    producto = request.form["producto"]
    cantidad = int(request.form["cantidad"])
    costo = float(request.form["costo"])
    total = cantidad * costo
    tipo_pago = request.form["tipo_pago"]

    conn = get_db()
    cur = conn.cursor()

    # Registrar compra
    cur.execute("""
        INSERT INTO compras
        (id_producto, producto, cantidad, costo, total, tipo_pago, fecha)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
    """, (
        id_producto,
        producto,
        cantidad,
        costo,
        total,
        tipo_pago
    ))

    # AUMENTAR STOCK
    cur.execute("""
        UPDATE productos
        SET cantidad = cantidad + %s
        WHERE id = %s
    """, (cantidad, id_producto))

    conn.commit()
    cur.close()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Registró compra de {cantidad} unidades de {producto}",
        modulo="Compras"
    )

    return redirect(url_for("compras.index"))


# ======================
# ELIMINAR COMPRA
# ======================
@compras_bp.route("/eliminar/<int:id>")
def eliminar(id):
    if session.get("rol") != "admin":
        return redirect(url_for("compras.index"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM compras WHERE id = %s", (id,))
    conn.commit()

    cur.close()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Eliminó compra ID {id}",
        modulo="Compras"
    )

    return redirect(url_for("compras.index"))
