from flask import Blueprint, render_template, request, redirect, url_for, session
import json
import os

auth_bp = Blueprint("auth", __name__)

DATA_FILE = "app/data/usuarios.json"

def cargar_usuarios():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        usuarios = cargar_usuarios()

        for u in usuarios:
            if u["username"] == username and u["password"] == password:
                session["usuario"] = u["username"]
                session["rol"] = u["rol"]
                return redirect(url_for("dashboard"))

        return render_template("auth/login.html", error="Credenciales incorrectas")

    return render_template("auth/login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
