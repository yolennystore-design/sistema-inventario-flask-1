import sqlite3
from pathlib import Path

db_path = Path("app/data/inventario.db")

print("Usando base de datos:", db_path.resolve())

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Ver columnas actuales
cur.execute("PRAGMA table_info(compras)")
columns = [c[1] for c in cur.fetchall()]
print("Columnas actuales:", columns)

# Agregar columna faltante
if "id_producto" not in columns:
    print("Agregando columna id_producto...")
    cur.execute("ALTER TABLE compras ADD COLUMN id_producto INTEGER")
    conn.commit()
    print("Columna agregada ✅")
else:
    print("La columna id_producto ya existe ✅")

conn.close()
print("Proceso terminado")
