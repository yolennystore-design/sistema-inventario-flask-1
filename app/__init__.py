from flask import Flask
from app.db import init_db

def create_app():
    app = Flask(__name__)

    init_db()  # ← CREA TODAS LAS TABLAS AL ARRANCAR

    from app.routes.productos import productos_bp
    from app.routes.compras import compras_bp
    from app.routes.ventas import ventas_bp

    app.register_blueprint(productos_bp)
    app.register_blueprint(compras_bp)
    app.register_blueprint(ventas_bp)

    return app
