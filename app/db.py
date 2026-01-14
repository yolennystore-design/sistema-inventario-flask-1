import sqlite3

DB_PATH = "app/data/inventario.db"

def get_db():
    """Retorna una conexión a la base de datos, asegurando el uso de diccionarios para las filas."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Asegura que las filas se devuelvan como diccionarios
    return conn

# ? Función para crear las tablas necesarias
def crear_tablas():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        precio REAL,
        stock INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS compras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        cantidad INTEGER,
        costo REAL,
        tipo_pago TEXT
    )
    """)

    conn.commit()
    conn.close()


