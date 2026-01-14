import json
import os
from datetime import datetime

DATA_FILE = "app/data/auditoria.json"

def registrar_log(usuario, accion, modulo):
    registro = {
        "usuario": usuario,
        "accion": accion,
        "modulo": modulo,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if not os.path.exists(DATA_FILE):
        logs = []
    else:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)

    logs.append(registro)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=4, ensure_ascii=False)
