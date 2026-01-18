# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, request, redirect, url_for, session
import os
from werkzeug.utils import secure_filename

from app.utils.auditoria import registrar_log
from app.routes.categorias import cargar_categorias
from app.db import get_db

productos_bp = Blueprint("productos", __name__, url_prefix="/productos")

# ======================
# CONFIGURACIÓN FOTOS
# ======================
UPLOAD_FOLDER = "app/static/uploads/productos"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def archivo_permitido(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ======================
# CONSULTAS DB
# ======================
def cargar_productos():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM productos ORDER BY id DESC")
    productos = cur.fetchall()
    conn.close()
    return productos


# ======================
# LISTAR PRODUCTOS
# ======================
@productos_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    productos = cargar_productos()
    categorias = cargar_categorias()

    return render_template(
        "productos/index.html",
        productos=productos,
        categorias=categorias
    )


# ======================
# AGREGAR PRODUCTO
# ======================
@productos_bp.route("/agregar", methods=["POST"])
def agregar():
    if session.get("rol") != "admin":
        return redirect(url_for("productos.index"))

    foto = request.files.get("foto")
    nombre_foto = ""

    if foto and foto.filename and archivo_permitido(foto.filename):
        filename = secure_filename(foto.filename)
        nombre_foto = filename
        foto.save(os.path.join(UPLOAD_FOLDER, nombre_foto))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO productos
        (nombre, categoria, subcategoria, item, precio, cantidad, foto)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        request.form["nombre"],
        request.form["categoria"],
        request.form["subcategoria"],
        request.form["item"],
        float(request.form["precio"]),
        0,
        nombre_foto
    ))

    nuevo_id = cur.fetchone()["id"]
    conn.commit()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Agregó producto ID {nuevo_id}",
        modulo="Productos"
    )

    return redirect(url_for("productos.index"))


# ======================
# FORMULARIO EDITAR
# ======================
@productos_bp.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"]
        precio = request.form["precio"]
        cantidad = request.form["cantidad"]
        categoria = request.form["categoria"]
        subcategoria = request.form["subcategoria"]
        item = request.form["item"]

        cur.execute("""
            UPDATE productos
            SET nombre=%s, precio=%s, cantidad=%s,
                categoria=%s, subcategoria=%s, item=%s
            WHERE id=%s
        """, (nombre, precio, cantidad, categoria, subcategoria, item, id))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("productos.index"))

    # GET → mostrar formulario
    cur.execute("SELECT * FROM productos WHERE id=%s", (id,))
    producto = cur.fetchone()
    cur.close()
    conn.close()

    return render_template("productos/editar.html", producto=producto)


# ======================
# ACTUALIZAR PRODUCTO
# ======================
@productos_bp.route("/actualizar/<int:id>", methods=["POST"])
def actualizar(id):
    if session.get("rol") != "admin":
        return redirect(url_for("productos.index"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT foto FROM productos WHERE id = %s", (id,))
    actual = cur.fetchone()
    nombre_foto = actual["foto"] if actual else ""

    foto = request.files.get("foto")

    if foto and foto.filename and archivo_permitido(foto.filename):
        if nombre_foto:
            ruta_anterior = os.path.join(UPLOAD_FOLDER, nombre_foto)
            if os.path.exists(ruta_anterior):
                os.remove(ruta_anterior)

        filename = secure_filename(foto.filename)
        nombre_foto = f"{id}_{filename}"
        foto.save(os.path.join(UPLOAD_FOLDER, nombre_foto))

    cur.execute("""
        UPDATE productos
        SET nombre=%s, categoria=%s, subcategoria=%s,
            item=%s, precio=%s, foto=%s
        WHERE id=%s
    """, (
        request.form["nombre"],
        request.form["categoria"],
        request.form["subcategoria"],
        request.form["item"],
        float(request.form["precio"]),
        nombre_foto,
        id
    ))

    conn.commit()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Editó producto ID {id}",
        modulo="Productos"
    )

    return redirect(url_for("productos.index"))


# ======================
# ELIMINAR PRODUCTO
# ======================
@productos_bp.route("/eliminar/<int:id>")
def eliminar(id):
    if session.get("rol") != "admin":
        return redirect(url_for("productos.index"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT foto FROM productos WHERE id = %s", (id,))
    producto = cur.fetchone()

    if producto and producto["foto"]:
        ruta = os.path.join(UPLOAD_FOLDER, producto["foto"])
        if os.path.exists(ruta):
            os.remove(ruta)

    cur.execute("DELETE FROM productos WHERE id = %s", (id,))
    conn.commit()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Eliminó producto ID {id}",
        modulo="Productos"
    )

    return redirect(url_for("productos.index"))
