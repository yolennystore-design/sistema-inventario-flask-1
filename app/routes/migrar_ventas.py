# -*- coding: utf-8 -*-
import json
import sqlite3
import os

JSON_FILE = "../data/ventas.json"
DB_PATH = "../data/inventario.db"

if not os.path.exists(JSON_FILE):
    print("? ventas.json no existe")
    exit()

if not os.path.exists(DB_PATH):
    print("? inventario.db no existe")
    exit()

with open(JSON_FILE, encoding="utf-8") as f:
    ventas = json.load(f)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

ventas_migradas = 0
ventas_omitidas = 0

for v in ventas:
    # ?? Validar estructura m�nima
    if "cliente" not in v or "total" not in v or "fecha" not in v:
        ventas_omitidas += 1
        continue

    # Insertar venta
    cur.execute("""
        INSERT INTO ventas (cliente, tipo_pago, total, fecha)
        VALUES (?, ?, ?, ?)
    """, (
        v.get("cliente", "P�blico General"),
        v.get("tipo_pago", "contado"),
        v.get("total", 0),
        v.get("fecha", "")
    ))

    venta_id = cur.lastrowid

    # Insertar items SOLO si existen
    items = v.get("items", [])
    if not isinstance(items, list):
        ventas_omitidas += 1
        continue

    for item in items:
        cur.execute("""
            INSERT INTO venta_items
            (venta_id, id_producto, producto, cantidad, precio, total)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            venta_id,
            item.get("id"),
            item.get("nombre", ""),
            item.get("cantidad", 0),
            item.get("precio", 0),
            item.get("total", 0)
        ))

    ventas_migradas += 1

conn.commit()
conn.close()

print(f"? Ventas migradas: {ventas_migradas}")
print(f"?? Ventas omitidas (sin items): {ventas_omitidas}")





