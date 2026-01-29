# -*- coding: utf-8 -*-

import os
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash, abort
)
from werkzeug.utils import secure_filename

from app.utils.auditoria import registrar_log
from app.routes.categorias import cargar_categorias
from app.db import get_db

productos_bp = Blueprint("productos", __name__, url_prefix="/productos")

# ======================
# CONFIGURACIÓN IMÁGENES
# ======================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(
    BASE_DIR, "static", "uploads", "productos"
)

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
# LISTADO
# ======================
@productos_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    return render_template(
        "productos/index.html",
        productos=cargar_productos(),
        categorias=cargar_categorias()
    )


# ======================
# AGREGAR PRODUCTO
# ======================
@productos_bp.route("/agregar", methods=["POST"])
def agregar():
    if session.get("rol") != "admin":
        abort(403)

    conn = get_db()
    cur = conn.cursor()

    # Crear producto SIN foto primero
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
        ""
    ))

    producto_id = cur.fetchone()["id"]

    # Guardar foto
    foto = request.files.get("foto")
    nombre_foto = ""

    if foto and foto.filename and archivo_permitido(foto.filename):
        ext = secure_filename(foto.filename).rsplit(".", 1)[1]
        nombre_foto = f"producto_{producto_id}.{ext}"
        foto.save(os.path.join(UPLOAD_FOLDER, nombre_foto))

        cur.execute(
            "UPDATE productos SET foto=%s WHERE id=%s",
            (nombre_foto, producto_id)
        )

    conn.commit()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Agregó producto ID {producto_id}",
        modulo="Productos"
    )

    flash("Producto agregado correctamente", "success")
    return redirect(url_for("productos.index"))


# ======================
# EDITAR PRODUCTO
# ======================
@productos_bp.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    if session.get("rol") != "admin":
        abort(403)

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        try:
            nombre = request.form["nombre"].strip()
            precio = float(request.form["precio"])

            cur.execute("SELECT foto FROM productos WHERE id=%s", (id,))
            actual = cur.fetchone()
            nombre_foto = actual["foto"] if actual else ""

            foto = request.files.get("foto")

            if foto and foto.filename and archivo_permitido(foto.filename):
                if nombre_foto:
                    ruta_vieja = os.path.join(UPLOAD_FOLDER, nombre_foto)
                    if os.path.exists(ruta_vieja):
                        os.remove(ruta_vieja)

                ext = secure_filename(foto.filename).rsplit(".", 1)[1]
                nombre_foto = f"producto_{id}.{ext}"
                foto.save(os.path.join(UPLOAD_FOLDER, nombre_foto))

            cur.execute("""
                UPDATE productos
                SET nombre=%s, categoria=%s, subcategoria=%s,
                    item=%s, precio=%s, foto=%s
                WHERE id=%s
            """, (
                nombre,
                request.form["categoria"],
                request.form["subcategoria"],
                request.form["item"],
                precio,
                nombre_foto,
                id
            ))

            conn.commit()

            registrar_log(
                usuario=session["usuario"],
                accion=f"Editó producto ID {id}",
                modulo="Productos"
            )

            flash("Producto actualizado correctamente", "success")

        except Exception as e:
            conn.rollback()
            print("ERROR EDITAR PRODUCTO:", e)
            flash("Error al actualizar producto", "danger")

        conn.close()
        return redirect(url_for("productos.index"))

    # GET
    cur.execute("SELECT * FROM productos WHERE id=%s", (id,))
    producto = cur.fetchone()
    conn.close()

    return render_template("productos/editar.html", producto=producto)


# ======================
# ELIMINAR PRODUCTO
# ======================
@productos_bp.route("/eliminar/<int:id>")
def eliminar(id):
    if session.get("rol") != "admin":
        abort(403)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT foto FROM productos WHERE id=%s", (id,))
    producto = cur.fetchone()

    if producto and producto["foto"]:
        ruta = os.path.join(UPLOAD_FOLDER, producto["foto"])
        if os.path.exists(ruta):
            os.remove(ruta)

    cur.execute("DELETE FROM productos WHERE id=%s", (id,))
    conn.commit()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Eliminó producto ID {id}",
        modulo="Productos"
    )

    flash("Producto eliminado", "success")
    return redirect(url_for("productos.index"))
@productos_bp.route("/historial/<int:id>")
def historial(id):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT usuario, accion, fecha
        FROM productos_historial
        WHERE producto_id = %s
        ORDER BY fecha DESC
    """, (id,))

    historial = cur.fetchall()

    cur.execute("SELECT nombre FROM productos WHERE id=%s", (id,))
    producto = cur.fetchone()

    conn.close()

    return render_template(
        "productos/historial.html",
        historial=historial,
        producto=producto
    )
