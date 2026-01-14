from flask import Flask
from app.db import fix_compras_table

def create_app():
    app = Flask(__name__)
    app.secret_key = "super-secret-key"

    # 🔧 MIGRACIÓN AUTOMÁTICA
    fix_compras_table()

    # Importar blueprints
    from app.routes.productos import productos_bp
    from app.routes.compras import compras_bp
    from app.routes.ventas import ventas_bp
    from app.routes.clientes import clientes_bp
    from app.routes.resumen import resumen_bp
    from app.routes.auth import auth_bp

    app.register_blueprint(productos_bp)
    app.register_blueprint(compras_bp)
    app.register_blueprint(ventas_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(resumen_bp)
    app.register_blueprint(auth_bp)

    return app

