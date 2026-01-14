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

    # ======================
    # PRODUCTOS
    # ======================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        categoria TEXT,
        subcategoria TEXT,
        item TEXT,
        precio REAL DEFAULT 0,
        cantidad INTEGER DEFAULT 0,
        foto TEXT
    )
    """)

    # ======================
    # COMPRAS (VERSIÓN CORRECTA)
    # ======================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS compras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_producto INTEGER,
        producto TEXT,
        cantidad INTEGER,
        costo REAL,
        total REAL,
        tipo_pago TEXT,
        abonado REAL DEFAULT 0,
        pendiente REAL DEFAULT 0,
        fecha TEXT
    )
    """)

    # ======================
    # VENTAS
    # ======================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_producto INTEGER,
        producto TEXT,
        cantidad INTEGER,
        precio REAL,
        total REAL,
        fecha TEXT
    )
    """)

    # ======================
    # CLIENTES
    # ======================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        telefono TEXT
    )
    """)

    conn.commit()
    conn.close()
