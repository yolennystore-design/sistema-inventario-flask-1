import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(BASE_DIR, "database.db")


def get_db():
    if DATABASE_URL:
        # PRODUCCIÓN (Render - PostgreSQL)
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    else:
        # LOCAL (SQLite)
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
def crear_tablas():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        categoria TEXT,
        subcategoria TEXT,
        item TEXT,
        precio REAL DEFAULT 0,
        cantidad INTEGER DEFAULT 0,
        foto TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id SERIAL PRIMARY KEY,
        nombre TEXT,
        telefono TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id SERIAL PRIMARY KEY,
        id_producto INTEGER,
        producto TEXT,
        cantidad INTEGER,
        precio REAL,
        total REAL,
        fecha TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS compras (
        id SERIAL PRIMARY KEY,
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

    conn.commit()
    conn.close()
