# -*- coding: utf-8 -*-

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session
)
from app.db import get_db
from app.utils.auditoria import registrar_log

clientes_bp = Blueprint("clientes", __name__, url_prefix="/clientes")


# ======================
# 📋 LISTAR CLIENTES
# ======================
@clientes_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nombre, direccion, telefono
        FROM clientes
        ORDER BY id DESC
    """)
    clientes = cur.fetchall()

    conn.close()

    return render_template(
        "clientes/index.html",
        clientes=clientes
    )


# ======================
# ➕ AGREGAR CLIENTE
# ======================
@clientes_bp.route("/agregar", methods=["POST"])
def agregar():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    nombre = request.form.get("nombre", "").strip()
    direccion = request.form.get("direccion", "").strip()
    telefono = request.form.get("telefono", "").strip()

    if not nombre:
        return redirect(url_for("clientes.index"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO clientes (nombre, direccion, telefono)
        VALUES (%s, %s, %s)
    """, (nombre, direccion, telefono))

    conn.commit()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Agregó cliente: {nombre}",
        modulo="Clientes"
    )

    return redirect(url_for("clientes.index"))


# ======================
# 🗑 ELIMINAR CLIENTE
# ======================
@clientes_bp.route("/eliminar/<int:id>")
def eliminar(id):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM clientes WHERE id = %s", (id,))
    conn.commit()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Eliminó cliente ID {id}",
        modulo="Clientes"
    )

    return redirect(url_for("clientes.index"))
