# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, session
import json, os
from app.utils.auditoria import registrar_log
from flask import session


clientes_bp = Blueprint("clientes", __name__, url_prefix="/clientes")

DATA_FILE = "app/data/clientes.json"


def cargar_clientes():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_clientes(clientes):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(clientes, f, indent=4, ensure_ascii=False)


@clientes_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    clientes = cargar_clientes()
    return render_template("clientes/index.html", clientes=clientes)


@clientes_bp.route("/agregar", methods=["POST"])
def agregar():
    clientes = cargar_clientes()

    nuevo = {
        "id": len(clientes) + 1,
        "nombre": request.form["nombre"],
        "direccion": request.form["direccion"],
        "telefono": request.form["telefono"]
    }

    clientes.append(nuevo)
    guardar_clientes(clientes)

    return redirect(url_for("clientes.index"))


@clientes_bp.route("/eliminar/<int:id>")
def eliminar(id):
    clientes = cargar_clientes()
    clientes = [c for c in clientes if c["id"] != id]
    guardar_clientes(clientes)
    return redirect(url_for("clientes.index"))





