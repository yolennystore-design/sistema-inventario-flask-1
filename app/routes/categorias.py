# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, request, redirect, url_for, session
import json, os
from app.utils.auditoria import registrar_log

categorias_bp = Blueprint("categorias", __name__, url_prefix="/categorias")

DATA_FILE = "app/data/categorias.json"

# ======================
# UTILIDADES
# ======================
def cargar_categorias():
    if not os.path.exists(DATA_FILE) or os.stat(DATA_FILE).st_size == 0:
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_categorias(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ======================
# VISTA PRINCIPAL
# ======================
@categorias_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    categorias = cargar_categorias()
    return render_template("categorias/index.html", categorias=categorias)

# ======================
# AGREGAR CATEGORIA
# ======================
@categorias_bp.route("/agregar", methods=["POST"])
def agregar():
    categorias = cargar_categorias()

    nombre = request.form["nombre"].strip()

    if nombre and nombre not in [c["nombre"] for c in categorias]:
        categorias.append({
            "id": len(categorias) + 1,
            "nombre": nombre
        })
        guardar_categorias(categorias)

        registrar_log(
            usuario=session["usuario"],
            accion=f"Categoría creada: {nombre}",
            modulo="Categorias"
        )

    return redirect(url_for("categorias.index"))

# ======================
# ELIMINAR CATEGORIA
# ======================
@categorias_bp.route("/eliminar/<int:id>")
def eliminar(id):
    categorias = cargar_categorias()
    categorias = [c for c in categorias if c["id"] != id]
    guardar_categorias(categorias)

    registrar_log(
        usuario=session["usuario"],
        accion="Categoría eliminada",
        modulo="Categorias"
    )

    return redirect(url_for("categorias.index"))
