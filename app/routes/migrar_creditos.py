# -*- coding: utf-8 -*-

import json
import os

VENTAS_FILE = "app/data/ventas.json"
CREDITOS_FILE = "app/data/creditos.json"

def cargar_json(ruta):
    if not os.path.exists(ruta) or os.stat(ruta).st_size == 0:
        return []
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_json(ruta, data):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

ventas = cargar_json(VENTAS_FILE)
creditos = cargar_json(CREDITOS_FILE)

migrados = 0

for credito in creditos:
    # ? Saltar créditos que ya tienen productos
    if "productos" in credito and credito["productos"]:
        continue

    for venta in ventas:
        mismo_cliente = venta.get("cliente") == credito.get("cliente")
        mismo_total = venta.get("total") == credito.get("monto")
        misma_fecha = venta.get("fecha") == credito.get("fecha")

        if mismo_cliente and mismo_total and misma_fecha:
            productos_credito = []

            for item in venta.get("items", []):
                productos_credito.append({
                    "nombre": item.get("nombre"),
                    "cantidad": item.get("cantidad"),
                    "precio": item.get("precio")
                })

            if productos_credito:
                credito["productos"] = productos_credito
                migrados += 1

            break  # no seguir buscando ventas

guardar_json(CREDITOS_FILE, creditos)

print(f"? Migración completada. Créditos actualizados: {migrados}")





