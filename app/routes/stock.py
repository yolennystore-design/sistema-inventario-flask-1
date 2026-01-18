# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, request, redirect, url_for, session
from app.db import get_db
from app.routes.categorias import cargar_categorias
from app.utils.auditoria import registrar_log

stock_bp = Blueprint("stock", __name__, url_prefix="/stock")

# ======================
# LISTAR STOCK
# ======================
@stock_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    filtro_nombre = request.args.get("nombre", "").lower()
    filtro_categoria = request.args.get("categoria", "")
    filtro_item = request.args.get("item", "")

    cur.execute("SELECT * FROM productos")
    productos_db = cur.fetchall()

    cur.close()
    conn.close()

    productos = []
    for p in productos_db:
        p = dict(p)

        if filtro_nombre and filtro_nombre not in p["nombre"].lower():
            continue
        if filtro_categoria and p["categoria"] != filtro_categoria:
            continue
        if filtro_item and p["item"] != filtro_item:
            continue

        productos.append(p)

    categorias = cargar_categorias()

    return render_template(
        "stock/index.html",
        productos=productos,
        categorias=categorias,
        filtro_nombre=filtro_nombre,
        filtro_categoria=filtro_categoria,
        filtro_item=filtro_item
    )

# ======================
# AJUSTAR STOCK (ADMIN)
# ======================
@stock_bp.route("/ajustar/<int:id>", methods=["POST"])
def ajustar_stock(id):
    if session.get("rol") != "admin":
        return redirect(url_for("stock.index"))

    cantidad = request.form.get("cantidad")
    if cantidad is None:
        return redirect(url_for("stock.index"))

    cantidad = int(cantidad)

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE productos SET cantidad = %s WHERE id = %s",
        (cantidad, id)
    )

    conn.commit()
    cur.close()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Ajustó stock del producto ID {id} a {cantidad}",
        modulo="Stock"
    )

    return redirect(url_for("stock.index"))
