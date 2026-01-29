# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, request, redirect, url_for, session
from app.db import get_db
from app.utils.auditoria import registrar_log

compras_bp = Blueprint("compras", __name__, url_prefix="/compras")

# ======================
# NORMALIZAR TIPO DE PAGO
# ======================
def normalizar_pago(tipo):
    if not tipo:
        return "contado"

    tipo = tipo.lower().strip()

    if "credit" in tipo:
        return "credito"
    return "contado"


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

    # 🔥 NORMALIZADO
    tipo_pago = normalizar_pago(request.form["tipo_pago"])

    abonado = 0
    pendiente = total if tipo_pago == "credito" else 0

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO compras
        (id_producto, producto, cantidad, costo, total,
         tipo_pago, abonado, pendiente, fecha)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW())
    """, (
        id_producto,
        producto,
        cantidad,
        costo,
        total,
        tipo_pago,
        abonado,
        pendiente
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
        accion=f"Registró compra ({tipo_pago}) de {producto}",
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


# ======================
# ABONAR A COMPRA A CRÉDITO
# ======================
@compras_bp.route("/abonar/<int:id>", methods=["GET", "POST"])
def abonar(id):
    if session.get("rol") != "admin":
        return redirect(url_for("compras.index"))

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        monto = float(request.form["monto"])

        cur.execute("""
            UPDATE compras
            SET abonado = abonado + %s,
                pendiente = total - (abonado + %s)
            WHERE id = %s
        """, (monto, monto, id))

        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("compras.index"))

    cur.execute("SELECT * FROM compras WHERE id = %s", (id,))
    compra = cur.fetchone()

    cur.close()
    conn.close()

    return render_template("compras/abonar.html", compra=compra)
