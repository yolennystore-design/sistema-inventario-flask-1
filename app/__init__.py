import sqlite3
from pathlib import Path
from flask import Flask

# Función que se encarga de arreglar la base de datos
def fix_compras_table():
    db_path = Path("app/data/inventario.db")
    if not db_path.exists():
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Comprobamos las columnas de la tabla 'compras'
    cur.execute("PRAGMA table_info(compras)")
    columns = [c[1] for c in cur.fetchall()]

    # Si no existe la columna 'id_producto', la agregamos
    if "id_producto" not in columns:
        cur.execute("ALTER TABLE compras ADD COLUMN id_producto INTEGER")
        conn.commit()

    conn.close()

# Función para crear la aplicación
def create_app():
    app = Flask(__name__)

    # Llamamos a la función que arregla la tabla 'compras' en la base de datos
    fix_compras_table()

    # Registros de otros blueprints o configuraciones que tu app necesite
    # Ejemplo de un blueprint para la ruta de 'compras'
    from app.routes.compras import compras_bp
    app.register_blueprint(compras_bp)

    return app
