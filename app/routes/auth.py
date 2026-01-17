# -*- coding: utf-8 -*-
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
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        if usuario == 'admin' and password == 'admin':
            session['usuario'] = usuario
            return redirect(url_for('dashboard.index'))  # AJUSTA AQUÍ

        return render_template(
            'login.html',
            error='Usuario o contraseña incorrectos'
        )

    return render_template('login.html')


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))





