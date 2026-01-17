# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, session
import json
import os

# Crear el Blueprint para autenticación
auth_bp = Blueprint("auth", __name__)

# Ruta para el archivo de usuarios
DATA_FILE = "app/data/usuarios.json"

# Función para cargar los usuarios desde un archivo JSON
def cargar_usuarios():
    if not os.path.exists(DATA_FILE):
        return []  # Si no existe el archivo, retornamos una lista vacía
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)  # Cargamos los usuarios en formato JSON

# Ruta para el login, maneja tanto GET como POST
@auth_bp.route("/login", methods=["POST", "GET"])
def login():
    # Si el método es POST, procesamos el inicio de sesión
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']

        # Verificación de autenticación con las credenciales predeterminadas
        if usuario == 'admin' and password == 'admin':
            session['usuario'] = usuario  # Almacenamos el nombre de usuario en la sesión
            session['rol'] = 'admin'  # Asignamos el rol 'admin' en la sesión
            return redirect(url_for('dashboard.index'))  # Redirigimos al dashboard

        # Si las credenciales no son correctas, mostramos un error
        return render_template('login.html', error="Usuario o contraseña incorrectos")

    # Si el método es GET, mostramos el formulario de login
    return render_template('login.html')


# Ruta para el logout, que limpia la sesión y redirige al login
@auth_bp.route("/logout")
def logout():
    session.clear()  # Limpiamos la sesión (cerramos sesión)
    return redirect(url_for("auth.login"))  # Redirigimos al formulario de login

