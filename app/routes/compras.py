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
# LISTAR COMPRAS
# ======================
@compras_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    compras = cargar_compras()

    return render_template(
        "compras/index.html",
        compras=compras
    )


# ======================
# AGREGAR COMPRA
# ======================
@compras_bp.route("/agregar", methods=["POST"])
def agregar():
    if session.get("rol") != "admin":
        return redirect(url_for("compras.index"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO compras
        (id_producto, producto, cantidad, costo, total, tipo_pago, abonado, pendiente, fecha)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """, (
        request.form.get("id_producto"),
        request.form.get("producto"),
        int(request.form.get("cantidad")),
        float(request.form.get("costo")),
        float(request.form.get("total")),
        request.form.get("tipo_pago"),
        float(request.form.get("abonado", 0)),
        float(request.form.get("pendiente", 0)),
    ))

    conn.commit()
    cur.close()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion="Registró una compra",
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
