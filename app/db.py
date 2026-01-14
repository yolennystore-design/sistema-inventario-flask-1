import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def crear_tablas():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        categoria TEXT,
        subcategoria TEXT,
        item TEXT,
        precio REAL,
        cantidad INTEGER DEFAULT 0,
        foto TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS compras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_producto INTEGER,
        cantidad INTEGER,
        costo REAL,
        tipo_pago TEXT,
        fecha TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_producto INTEGER,
        cantidad INTEGER,
        precio REAL,
        fecha TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        telefono TEXT
    )
    """)

    conn.commit()
    conn.close()
