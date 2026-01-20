import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(BASE_DIR, "database.db")


def get_db():
    # PRODUCCIÓN (Render) → SOLO PostgreSQL
    if DATABASE_URL and DATABASE_URL.startswith("postgres"):
        return psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor
        )

    # DESARROLLO LOCAL → SQLite
    if os.getenv("FLASK_ENV") == "development":
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    # SI LLEGA AQUÍ EN PRODUCCIÓN → ERROR CLARO
    raise RuntimeError(
        "DATABASE_URL no configurada. PostgreSQL es obligatorio en producción."
    )


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
    cur.execute("""
    CREATE TABLE IF NOT EXISTS productos_historial (
        id SERIAL PRIMARY KEY,
        producto_id INTEGER NOT NULL,
        usuario TEXT,
        accion TEXT NOT NULL,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)


    conn.commit()
    conn.close()
