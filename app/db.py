import sqlite3

DB_PATH = "app/data/inventario.db"

def get_db():
    """Retorna una conexión a la base de datos, asegurando el uso de diccionarios para las filas."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Asegura que las filas se devuelvan como diccionarios
    return conn

# ✅ Función para crear las tablas necesarias
def crear_tablas():
    conn = get_db()

    # Consulta SQL para crear las tablas necesarias si no existen
    query = """
    CREATE TABLE IF NOT EXISTS resumen_ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        inversion_total REAL,
        inversion_contado REAL DEFAULT 0,   -- Asegúrate de que los valores tengan un valor predeterminado
        inversion_credito REAL DEFAULT 0,
        inversion_productos_vendidos REAL DEFAULT 0,
        ventas_contado REAL DEFAULT 0,
        ventas_credito REAL DEFAULT 0,
        articulos_vendidos INTEGER DEFAULT 0,
        ganancia REAL DEFAULT 0
    );
    """

    conn.execute(query)
    conn.commit()
    conn.close()
