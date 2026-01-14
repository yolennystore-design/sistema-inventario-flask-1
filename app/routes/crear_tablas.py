import sqlite3
import os

DB_PATH = "app/data/inventario.db"

# Crear carpeta si no existe
os.makedirs("app/data", exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    categoria TEXT NOT NULL,
    subcategoria TEXT NOT NULL,
    item TEXT NOT NULL,
    precio REAL NOT NULL,
    cantidad INTEGER DEFAULT 0,
    foto TEXT
);
""")

conn.commit()
conn.close()

print("✅ Tabla 'productos' creada correctamente")
cursor.execute("""
CREATE TABLE IF NOT EXISTS compras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto INTEGER NOT NULL,
    producto TEXT NOT NULL,
    cantidad INTEGER NOT NULL,
    costo REAL NOT NULL,
    total REAL NOT NULL,
    fecha TEXT NOT NULL,
    FOREIGN KEY (id_producto) REFERENCES productos(id)
);
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente TEXT NOT NULL,
    tipo_pago TEXT NOT NULL,
    total REAL NOT NULL,
    fecha TEXT NOT NULL
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS venta_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER NOT NULL,
    id_producto INTEGER NOT NULL,
    producto TEXT NOT NULL,
    cantidad INTEGER NOT NULL,
    precio REAL NOT NULL,
    total REAL NOT NULL,
    FOREIGN KEY (venta_id) REFERENCES ventas(id),
    FOREIGN KEY (id_producto) REFERENCES productos(id)
);
""")
