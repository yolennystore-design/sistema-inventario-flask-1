# -*- coding: utf-8 -*-

import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor

# ======================
# CONFIGURACIÓN
# ======================

DATABASE_URL = os.getenv("DATABASE_URL")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(BASE_DIR, "database.db")


# ======================
# CONEXIÓN A LA BASE DE DATOS
# ======================

def get_db():
    """
    PRODUCCIÓN (Render):
        - PostgreSQL obligatorio
        - Usa DATABASE_URL

    DESARROLLO LOCAL:
        - SQLite automático
        - Usa database.db
    """

    # PRODUCCIÓN → PostgreSQL
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

    # ERROR CLARO SI FALLA TODO
    raise RuntimeError(
        "DATABASE_URL no configurada. PostgreSQL es obligatorio en producción."
    )


# ======================
# CREAR TABLAS
# ======================

def crear_tablas():
    conn = get_db()
    cur = conn.cursor()

    # Detectar si es SQLite o PostgreSQL
    is_sqlite = isinstance(conn, sqlite3.Connection)

    # Tipo de ID compatible
    id_type = (
        "INTEGER PRIMARY KEY AUTOINCREMENT"
        if is_sqlite
        else "SERIAL PRIMARY KEY"
    )

    # ======================
    # PRODUCTOS
    # ======================
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS productos (
        id {id_type},
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
    # CLIENTES
    # ======================
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS clientes (
        id {id_type},
        nombre TEXT,
        telefono TEXT
    )
    """)

    # ======================
    # VENTAS
    # ======================
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS ventas (
        id {id_type},
        id_producto INTEGER,
        producto TEXT,
        cantidad INTEGER,
        precio REAL,
        total REAL,
        fecha TEXT
    )
    """)

    # ======================
    # COMPRAS / CRÉDITOS
    # ======================
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS compras (
        id {id_type},
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
    # HISTORIAL DE PRODUCTOS
    # ======================
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS productos_historial (
        id {id_type},
        producto_id INTEGER NOT NULL,
        usuario TEXT,
        accion TEXT NOT NULL,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ======================
    # GASTOS
    # ======================
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS gastos (
        id {id_type},
        concepto TEXT NOT NULL,
        categoria TEXT,
        monto REAL NOT NULL,
        fecha DATE NOT NULL,
        usuario TEXT
    )
    """)

    conn.commit()
    conn.close()
