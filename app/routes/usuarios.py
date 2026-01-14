from flask import Blueprint, render_template, request, redirect, url_for
import json
import os
from flask import session, redirect, url_for
from app.utils.roles import requiere_login, requiere_admin

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")

DATA_FILE = "app/data/usuarios.json"

def cargar_usuarios():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_usuarios(usuarios):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, indent=4, ensure_ascii=False)

@usuarios_bp.route("/")
def index():
        if not requiere_login():
            return redirect(url_for("auth.login"))

        if not requiere_admin():
            return "Acceso denegado", 403

        usuarios = cargar_usuarios()
        return render_template("usuarios/index.html", usuarios=usuarios)

@usuarios_bp.route("/agregar", methods=["POST"])
def agregar():
    usuarios = cargar_usuarios()

    username = request.form["username"]
    password = request.form["password"]
    rol = request.form["rol"]

    usuarios.append({
        "username": username,
        "password": password,
        "rol": rol
    })

    guardar_usuarios(usuarios)
    return redirect(url_for("usuarios.index"))

@usuarios_bp.route("/eliminar/<username>")
def eliminar(username):
    usuarios = cargar_usuarios()
    usuarios = [u for u in usuarios if u["username"] != username]
    guardar_usuarios(usuarios)
    return redirect(url_for("usuarios.index"))