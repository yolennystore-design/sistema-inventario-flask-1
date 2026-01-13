from flask import Flask, render_template, session, redirect, url_for
from app.db import crear_tablas

app = Flask(
    __name__,
    template_folder="app/templates",
    static_folder="app/static"
)

app.secret_key = "secret"

# ======================
# CREAR TABLAS (IMPORTANTE)
# ======================
crear_tablas()

# ======================
# IMPORTAR BLUEPRINTS
# ======================
from app.routes.auth import auth_bp
from app.routes.clientes import clientes_bp
from app.routes.productos import productos_bp
from app.routes.stock import stock_bp
from app.routes.ventas import ventas_bp
from app.routes.compras import compras_bp
from app.routes.creditos import creditos_bp
from app.routes.usuarios import usuarios_bp
from app.routes.auditoria import auditoria_bp
from app.routes.categorias import categorias_bp
from app.routes.resumen import resumen_bp

# ======================
# REGISTRAR BLUEPRINTS
# ======================
app.register_blueprint(auth_bp)
app.register_blueprint(clientes_bp)
app.register_blueprint(productos_bp)
app.register_blueprint(stock_bp)
app.register_blueprint(ventas_bp)
app.register_blueprint(compras_bp)
app.register_blueprint(creditos_bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(auditoria_bp)
app.register_blueprint(categorias_bp)
app.register_blueprint(resumen_bp)

# ======================
# DASHBOARD
# ======================
@app.route("/")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))
    return render_template("dashboard.html")

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(debug=True)
