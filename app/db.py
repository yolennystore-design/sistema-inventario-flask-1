# -*- coding: utf-8 -*-

import os
import sqlite3
import psycopg
from psycopg.rows import dict_row

# ======================
# CONFIGURACIÓN
# ======================

DATABASE_URL = os.getenv("DATABASE_URL")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.path.join(BASE_DIR, "database.db")

# ======================
# CONEXIÓN A LA BD
# ======================
def get_db():
    if DATABASE_URL:
        dsn = DATABASE_URL
        if "sslmode=" not in dsn:
            dsn += "?sslmode=require"

        return psycopg.connect(
            dsn,
            row_factory=dict_row,
            connect_timeout=5
        )

    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ======================
# CREAR TABLAS (SEGURO)
# ======================
def crear_tablas():
    """
    ⚠️ Esta función NO debe tumbar la app si falla la BD.
    Se ejecuta solo cuando la conexión es exitosa.
    """

    try:
        conn = get_db()
    except Exception as e:
        print("⚠️ No se pudo conectar a la BD:", e)
        return

    cur = conn.cursor()
    is_sqlite = isinstance(conn, sqlite3.Connection)

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
        nombre TEXT NOT NULL,
        telefono TEXT
    )
    """)

    # MIGRACIÓN SEGURA (direccion)
    try:
        cur.execute("ALTER TABLE clientes ADD COLUMN direccion TEXT")
        conn.commit()
    except Exception:
        conn.rollback()

    # ======================
    # VENTAS
    # ======================
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS ventas (
        id {id_type},
        numero_factura TEXT,
        cliente TEXT,
        tipo TEXT,
        id_producto INTEGER,
        producto TEXT,
        cantidad INTEGER,
        precio REAL,
        total REAL,
        fecha TEXT,
        eliminado BOOLEAN DEFAULT FALSE
    )
    """)

    # MIGRACIONES SEGURAS (ventas)
    for col in [
        "numero_factura TEXT",
        "cliente TEXT",
        "tipo TEXT",
        "eliminado BOOLEAN DEFAULT FALSE"
    ]:
        try:
            cur.execute(f"ALTER TABLE ventas ADD COLUMN {col}")
            conn.commit()
        except Exception:
            conn.rollback()

    # ======================
    # CRÉDITOS
    # ======================
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS creditos (
        id {id_type},
        numero_factura TEXT,
        cliente TEXT NOT NULL,
        monto REAL NOT NULL,
        abonado REAL DEFAULT 0,
        pendiente REAL NOT NULL,
        estado TEXT DEFAULT 'Pendiente',
        fecha TEXT,
        fecha_ultimo_abono TEXT,
        eliminado BOOLEAN DEFAULT FALSE
    )
    """)

    # MIGRACIONES SEGURAS (creditos)
    for col in [
        "fecha_ultimo_abono TEXT",
        "eliminado BOOLEAN DEFAULT FALSE"
    ]:
        try:
            cur.execute(f"ALTER TABLE creditos ADD COLUMN {col}")
            conn.commit()
        except Exception:
            conn.rollback()

    # ======================
    # COMPRAS
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
    # HISTORIAL
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
    cur.close()
    conn.close()


# ======================
# MIGRACIÓN EXPLÍCITA VENTAS
# ======================
def migrar_ventas():
    print(">>> EJECUTANDO migrar_ventas()")

    try:
        conn = get_db()
    except Exception as e:
        print("⚠️ No se pudo conectar:", e)
        return

    cur = conn.cursor()

    def try_add(sql):
        try:
            cur.execute(sql)
            conn.commit()
            print(f">>> OK: {sql}")
        except Exception as e:
            conn.rollback()
            print(f">>> YA EXISTE o ERROR: {sql} -> {e}")

    try_add("ALTER TABLE ventas ADD COLUMN numero_factura TEXT")
    try_add("ALTER TABLE ventas ADD COLUMN cliente TEXT")
    try_add("ALTER TABLE ventas ADD COLUMN tipo TEXT")
    try_add("ALTER TABLE ventas ADD COLUMN eliminado BOOLEAN DEFAULT FALSE")

    try_add("ALTER TABLE creditos ADD COLUMN eliminado BOOLEAN DEFAULT FALSE")

    cur.close()
    conn.close()
