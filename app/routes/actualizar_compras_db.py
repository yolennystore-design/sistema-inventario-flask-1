import sys
import os

# ?? Forzar la ra�z del proyecto al PYTHONPATH
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, BASE_DIR)

from app.db import get_db

conn = get_db()
cursor = conn.cursor()

def agregar_columna(sql, nombre):
    try:
        cursor.execute(sql)
        print(f"? Columna '{nombre}' agregada")
    except Exception:
        print(f"?? Columna '{nombre}' ya existe")

agregar_columna(
    "ALTER TABLE compras ADD COLUMN tipo_pago TEXT DEFAULT 'contado'",
    "tipo_pago"
)

agregar_columna(
    "ALTER TABLE compras ADD COLUMN abonado REAL DEFAULT 0",
    "abonado"
)

agregar_columna(
    "ALTER TABLE compras ADD COLUMN pendiente REAL DEFAULT 0",
    "pendiente"
)

conn.commit()
conn.close()

print("?? Base FROM datos app/data/inventario.db actualizada correctamente")





