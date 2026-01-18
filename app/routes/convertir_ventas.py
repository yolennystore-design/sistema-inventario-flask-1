# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime

ENTRADA = "../data/ventas.json"
SALIDA = "../data/ventas_convertidas.json"

if not os.path.exists(ENTRADA):
    print("? ventas.json no existe")
    exit()

with open(ENTRADA, encoding="utf-8") as f:
    ventas_viejas = json.load(f)

ventas_nuevas = []

for v in ventas_viejas:
    venta = {
        "cliente": v.get("cliente", "P�blico General"),
        "tipo_pago": "contado",
        "total": v.get("total", 0),
        "fecha": v.get("fecha") + " 00:00",
        "items": [
            {
                "id": None,  # no exist�a antes
                "nombre": v.get("producto", ""),
                "cantidad": v.get("cantidad", 0),
                "precio": v.get("precio", 0),
                "total": v.get("total", 0)
            }
        ]
    }
    ventas_nuevas.append(venta)

with open(SALIDA, "w", encoding="utf-8") as f:
    json.dump(ventas_nuevas, f, indent=4, ensure_ascii=False)

print("? Ventas convertidas correctamente")
print(f"?? Archivo generado: ventas_convertidas.json ({len(ventas_nuevas)} ventas)")





