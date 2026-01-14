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

    conn.execute("""
	CREATE TABLE IF NOT EXISTS compras (
    	id INTEGER PRIMARY KEY AUTOINCREMENT,
    	id_producto INTEGER NOT NULL,
    	proveedor TEXT,
    	cantidad INTEGER NOT NULL,
    	precio REAL NOT NULL,
    	total REAL NOT NULL,
    	fecha TEXT NOT NULL
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
def fix_compras_table():
    import sqlite3
    from pathlib import Path

    db_path = Path("app/data/inventario.db")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(compras)")
    columns = [c[1] for c in cur.fetchall()]

    if "id_producto" not in columns:
        print("🛠 Agregando columna id_producto a compras...")
        cur.execute("ALTER TABLE compras ADD COLUMN id_producto INTEGER")
        conn.commit()
        print("✅ Columna id_producto agregada")
    else:
        print("ℹ️ Columna id_producto ya existe")

    conn.commit()
    conn.close()
