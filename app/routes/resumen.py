# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, session, redirect, url_for
from app.db import get_db
from app.utils.auditoria import registrar_log
import json, os

resumen_bp = Blueprint("resumen", __name__, url_prefix="/resumen")

VENTAS_FILE = "app/data/ventas.json"


# ======================
# CARGAR VENTAS
# ======================
def cargar_ventas():
    if not os.path.exists(VENTAS_FILE):
        return []
    with open(VENTAS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@resumen_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    # ================= DATOS =================
    conn = get_db()

    compras = conn.execute("""
        SELECT fecha, cantidad, costo, tipo_pago
        FROM compras
        ORDER BY fecha
    """).fetchall()

    conn.close()

    ventas = cargar_ventas()

    resumen = []
    totales = {}

    # ================= INIT MES =================
    def init_mes(mes):
        totales.setdefault(mes, {
            "inversion_total": 0,
            "inversion_contado": 0,
            "inversion_credito": 0,
            "inv_prod_vendidos": 0,
            "ventas_contado": 0,
            "ventas_credito": 0,
            "articulos_vendidos": 0,
            "ganancia": 0
        })

    # ================= COSTO ACTUAL =================
    costo_actual = 0
    for c in compras:
        costo_actual = float(c["costo"])

    # ================= COMPRAS (1 FILA = 1 COMPRA) =================
    for c in compras:
        fecha = c["fecha"]
        mes = fecha[:7]

        cantidad = float(c["cantidad"])
        costo = float(c["costo"])
        inversion = cantidad * costo
        tipo_pago = (c["tipo_pago"] or "contado").lower()

        init_mes(mes)

        resumen.append({
            "tipo": "COMPRA",
            "mes": mes,
            "fecha": fecha,
            "inversion_total": inversion,
            "inversion_contado": inversion if tipo_pago == "contado" else 0,
            "inversion_credito": inversion if tipo_pago == "credito" else 0,
            "inv_prod_vendidos": 0,
            "ventas_contado": 0,
            "ventas_credito": 0,
            "articulos_vendidos": cantidad,
            "ganancia": 0
        })

        totales[mes]["inversion_total"] += inversion
        if tipo_pago == "contado":
            totales[mes]["inversion_contado"] += inversion
        else:
            totales[mes]["inversion_credito"] += inversion

    # ================= VENTAS (1 FILA = 1 VENTA) =================
    for v in ventas:
        fecha = v.get("fecha", "")
        mes = fecha[:7]
        tipo_pago = v.get("tipo", v.get("tipo_pago", "contado")).lower()

        init_mes(mes)

        fila = {
            "tipo": "VENTA",
            "mes": mes,
            "fecha": fecha,
            "inversion_total": 0,
            "inversion_contado": 0,
            "inversion_credito": 0,
            "inv_prod_vendidos": 0,
            "ventas_contado": 0,
            "ventas_credito": 0,
            "articulos_vendidos": 0,
            "ganancia": 0
        }

        items = v.get("items") or v.get("elementos") or []

        for it in items:
            cantidad = int(it.get("cantidad", 0))
            precio = float(it.get("precio", 0))

            costo_item = cantidad * costo_actual
            total_item = cantidad * precio
            ganancia_item = total_item - costo_item

            fila["inv_prod_vendidos"] += costo_item
            fila["articulos_vendidos"] += cantidad
            fila["ganancia"] += ganancia_item

            totales[mes]["inv_prod_vendidos"] += costo_item
            totales[mes]["articulos_vendidos"] += cantidad
            totales[mes]["ganancia"] += ganancia_item

            if tipo_pago == "contado":
                fila["ventas_contado"] += total_item
                totales[mes]["ventas_contado"] += total_item
            else:
                fila["ventas_credito"] += total_item
                totales[mes]["ventas_credito"] += total_item

        resumen.append(fila)

    # ================= ORDER BY FECHA =================
    resumen.sort(key=lambda x: x["fecha"])

    registrar_log(
        usuario=session["usuario"],
        accion="Consultó resumen detallado (ventas y compras)",
        modulo="Resumen"
    )

    return render_template(
        "resumen/index.html",
        resumen=resumen,
        totales=totales
    )
@resumen_bp.route("/eliminar", methods=["POST"])
def eliminar_resumen():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()

    conn.execute("DELETE FROM ventas")
    conn.execute("DELETE FROM compras")

    conn.commit()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion="Eliminó todas las ventas y compras del resumen",
        modulo="Resumen"
    )

    return redirect(url_for("resumen.index"))





