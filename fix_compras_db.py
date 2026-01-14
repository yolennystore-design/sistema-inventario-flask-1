import sqlite3

DB_PATH = "app/data/inventario.db"


conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Ver columnas actuales
cursor.execute("PRAGMA table_info(compras)")
cols = [c[1] for c in cursor.fetchall()]

if "id_producto" not in cols:
    print("➕ Agregando columna id_producto...")
    cursor.execute("ALTER TABLE compras ADD COLUMN id_producto INTEGER")
else:
    print("✅ La columna id_producto ya existe")

conn.commit()
conn.close()

print("✔ Base de datos actualizada correctamente")
