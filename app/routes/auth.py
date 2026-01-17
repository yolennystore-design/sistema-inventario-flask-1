# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, session

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        password = request.form.get("password")

        # Credenciales admin
        if usuario == "admin" and password == "admin":
            session.clear()
            session["usuario"] = usuario
            session["rol"] = "admin"   # 👈 ESTO ES CLAVE
            return redirect(url_for("dashboard.index"))

        return render_template(
            "login.html",
            error="Usuario o contraseña incorrectos"
        )

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
