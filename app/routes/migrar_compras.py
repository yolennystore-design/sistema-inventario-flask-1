import json
import sqlite3
import os

JSON_FILE = "app/data/compras.json"
DB_PATH = "app/data/inventario.db"

if not os.path.exists(JSON_FILE):
    print("❌ compras.json no existe")
    exit()

with open(JSON_FILE, encoding="utf-8") as f:
    compras = json.load(f)

conn = sqlite3.connect(DB_PATH)

for c in compras:
    conn.execute("""
        INSERT INTO compras
        (id_producto, producto, cantidad, costo, total, fecha)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        c.get("id_producto", 0),
        c["producto"],
        c["cantidad"],
        c["costo"],
        c["total"],
        c["fecha"]
    ))

conn.commit()
conn.close()

print("✅ Compras migradas correctamente")
