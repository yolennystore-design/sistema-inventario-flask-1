# -*- coding: utf-8 -*-
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ✅ ALIAS PARA COMPATIBILIDAD CON LAS RUTAS
def get_db():
    return get_connection()


def crear_tablas():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        precio REAL,
        stock INTEGER DEFAULT 0
    )
    """)

    # 🔹 Agregar columnas si no existen (SQLite safe)
    try:
        cursor.execute("ALTER TABLE productos ADD COLUMN categoria TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE productos ADD COLUMN nombre_foto TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
