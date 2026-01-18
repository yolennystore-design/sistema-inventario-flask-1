from flask import Blueprint, render_template, session, redirect, url_for, request
import json
import os
import math

auditoria_bp = Blueprint("auditoria", __name__, url_prefix="/auditoria")

DATA_FILE = "app/data/auditoria.json"
REGISTROS_POR_PAGINA = 10

# =========================
# CARGAR LOGS
# =========================
def cargar_logs():
    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            contenido = f.read().strip()
            if not contenido:
                return []
            return json.loads(contenido)
    except json.JSONDecodeError:
        return []

# =========================
# GUARDAR LOGS
# =========================
def guardar_logs(registros):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=4)

# =========================
# LISTADO + FILTROS + PAGINACI�N
# =========================
@auditoria_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    if session.get("rol") != "admin":
        return "Acceso denegado", 403

    registros = cargar_logs()

    # ?? Filtros
    usuario = request.args.get("usuario", "").lower()
    modulo = request.args.get("modulo", "").lower()
    fecha = request.args.get("fecha", "")

    filtrados = []
    for i, r in enumerate(registros):
        if usuario and usuario not in r.get("usuario", "").lower():
            continue
        if modulo and modulo not in r.get("modulo", "").lower():
            continue
        if fecha and fecha not in r.get("fecha", ""):
            continue

        r["_index"] = i
        filtrados.append(r)

    # ?? Paginaci�n
    pagina = int(request.args.get("pagina", 1))
    total = len(filtrados)
    total_paginas = max(1, math.ceil(total / REGISTROS_POR_PAGINA))

    inicio = (pagina - 1) * REGISTROS_POR_PAGINA
    fin = inicio + REGISTROS_POR_PAGINA
    registros_pagina = filtrados[inicio:fin]

    params = {
        "usuario": request.args.get("usuario", ""),
        "modulo": request.args.get("modulo", ""),
        "fecha": request.args.get("fecha", "")
    }

    return render_template(
        "auditoria/index.html",
        registros=registros_pagina,
        pagina=pagina,
        total_paginas=total_paginas,
        filtros=params,
        params=params
    )

# =========================
# ELIMINAR REGISTRO
# =========================
@auditoria_bp.route("/eliminar/<int:index>", methods=["POST"])
def eliminar(index):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    if session.get("rol") != "admin":
        return "Acceso denegado", 403

    registros = cargar_logs()

    if 0 <= index < len(registros):
        registros.pop(index)
        guardar_logs(registros)

    return redirect(url_for("auditoria.index"))
# =========================
# ELIMINAR TODOS LOS REGISTROS
# =========================
@auditoria_bp.route("/eliminar_todo", methods=["POST"])
def eliminar_todo():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    if session.get("rol") != "admin":
        return "Acceso denegado", 403

    guardar_logs([])  # Vac�a el archivo JSON

    return redirect(url_for("auditoria.index"))





