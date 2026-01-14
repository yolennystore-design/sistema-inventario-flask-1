import sqlite3
import os

DB_PATH = "../data/inventario.db"

if not os.path.exists(DB_PATH):
    print("? inventario.db no existe")
    exit()

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Tabla ventas
cur.execute("""
CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente TEXT NOT NULL,
    tipo_pago TEXT NOT NULL,
    total REAL NOT NULL,
    fecha TEXT NOT NULL
)
""")

# Tabla items FROM venta
cur.execute("""
CREATE TABLE IF NOT EXISTS venta_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER NOT NULL,
    id_producto INTEGER,
    producto TEXT NOT NULL,
    cantidad INTEGER NOT NULL,
    precio REAL NOT NULL,
    total REAL NOT NULL,
    FOREIGN KEY (venta_id) REFERENCES ventas(id)
)
""")

conn.commit()
conn.close()

print("? Tablas ventas y venta_items creadas correctamente")





