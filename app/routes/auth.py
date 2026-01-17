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
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        usuario = request.form['Yolenny Store']
        password = request.form['password']

        if usuario == 'admin' and password == 'lisandyeloise':
            session['usuario'] = usuario
            return redirect(url_for('dashboard'))  # CORRIGE AQUÍ A 'dashboard'

        return render_template(
            'login.html',
            error='Usuario o contraseña incorrectos'
        )

    return render_template('login.html')

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
