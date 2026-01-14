# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, request, redirect, url_for, session
from app.db import get_db
from app.routes.categorias import cargar_categorias
from app.utils.auditoria import registrar_log

stock_bp = Blueprint("stock", __name__, url_prefix="/stock")

STOCK_MINIMO = 5  # 🔔 alerta de stock bajo


# ======================
# LISTAR STOCK
# ======================
@stock_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()

    # 🔎 Filtros
    filtro_nombre = request.args.get("nombre", "").strip().lower()
    filtro_categoria = request.args.get("categoria", "").strip()
    filtro_item = request.args.get("item", "").strip()

    productos_db = conn.execute("SELECT * FROM productos").fetchall()
    conn.close()

    productos = []

    for row in productos_db:
        p = dict(row)

        # 🔍 Aplicar filtros
        if filtro_nombre and filtro_nombre not in p["nombre"].lower():
            continue
        if filtro_categoria and p["categoria"] != filtro_categoria:
            continue
        if filtro_item and p["item"] != filtro_item:
            continue

        # 🚨 Estado del stock
        if p["cantidad"] <= 0:
            p["estado_stock"] = "agotado"
        elif p["cantidad"] <= STOCK_MINIMO:
            p["estado_stock"] = "bajo"
        else:
            p["estado_stock"] = "normal"

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

    try:
        cantidad = int(request.form.get("cantidad", 0))
        if cantidad < 0:
            cantidad = 0
    except ValueError:
        return redirect(url_for("stock.index"))

    conn = get_db()
    conn.execute(
        "UPDATE productos SET cantidad = ? WHERE id = ?",
        (cantidad, id)
    )
    conn.commit()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Ajustó stock del producto ID {id} a {cantidad}",
        modulo="Stock"
    )

    return redirect(url_for("stock.index"))
# Ruta para generar el PDF del stock
@stock_bp.route("/imprimir_stock")
def imprimir_stock():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    # Crear un archivo en memoria
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    c.setFont("Helvetica", 12)

    # Agregar un título
    c.drawString(100, 750, "Stock de Productos")

    # Obtener los productos de la base de datos
    conn = get_db()
    productos_db = conn.execute("SELECT * FROM productos").fetchall()
    conn.close()

    # Configurar la tabla
    y_position = 730
    c.drawString(100, y_position, "ID")
    c.drawString(150, y_position, "Producto")
    c.drawString(300, y_position, "Categoría")
    c.drawString(450, y_position, "Item")
    c.drawString(550, y_position, "Stock")

    y_position -= 20

    for row in productos_db:
        p = dict(row)
        c.drawString(100, y_position, str(p['id']))
        c.drawString(150, y_position, p['nombre'])
        c.drawString(300, y_position, p['categoria'])
        c.drawString(450, y_position, p['item'])
        c.drawString(550, y_position, str(p['cantidad']))
        y_position -= 20

        if y_position < 100:  # Si llegamos al final de la página, creamos una nueva página
            c.showPage()
            y_position = 750
            c.drawString(100, y_position, "ID")
            c.drawString(150, y_position, "Producto")
            c.drawString(300, y_position, "Categoría")
            c.drawString(450, y_position, "Item")
            c.drawString(550, y_position, "Stock")
            y_position -= 20

    c.showPage()
    c.save()

    # Regresar al navegador como archivo PDF
    buffer.seek(0)
    return Response(buffer, mimetype="application/pdf", headers={"Content-Disposition": "attachment;filename=stock_productos.pdf"})