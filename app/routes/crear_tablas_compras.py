import sqlite3
import os

DB_PATH = "../data/inventario.db"

if not os.path.exists(DB_PATH):
    print("❌ inventario.db no existe")
    exit()

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS compras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto INTEGER,
    producto TEXT NOT NULL,
    cantidad INTEGER NOT NULL,
    costo REAL NOT NULL,
    total REAL NOT NULL,
    fecha TEXT NOT NULL
)
""")

conn.commit()
conn.close()

print("✅ Tabla compras creada correctamente")
