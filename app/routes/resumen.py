# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, session, redirect, url_for
from app.db import get_db
from app.utils.auditoria import registrar_log

resumen_bp = Blueprint("resumen", __name__, url_prefix="/resumen")


@resumen_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    # ======================
    # COMPRAS
    # ======================
    cur.execute("""
        SELECT fecha, cantidad, costo, tipo_pago
        FROM compras
        ORDER BY fecha
    """)
    compras = cur.fetchall()

    # ======================
    # VENTAS (DESDE BD, NO JSON)
    # ======================
    cur.execute("""
        SELECT
            numero_factura,
            fecha,
            tipo,
            SUM(total) AS total,
            SUM(cantidad) AS articulos
        FROM ventas
        GROUP BY numero_factura, fecha, tipo
        ORDER BY fecha
    """)
    ventas = cur.fetchall()

    cur.close()
    conn.close()

    resumen = []
    totales = {}

    # ======================
    # INIT MES
    # ======================
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

    # ======================
    # COSTO ACTUAL (ÚLTIMO COSTO)
    # ======================
    costo_actual = 0
    for c in compras:
        costo_actual = float(c["costo"])

    # ======================
    # PROCESAR COMPRAS
    # ======================
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

    # ======================
    # PROCESAR VENTAS
    # ======================
    for v in ventas:
        fecha = v["fecha"]
        mes = fecha[:7]
        tipo_pago = (v["tipo"] or "contado").lower()

        total_venta = float(v["total"])
        articulos = int(v["articulos"])

        init_mes(mes)

        fila = {
            "tipo": "VENTA",
            "mes": mes,
            "fecha": fecha,
            "inversion_total": 0,
            "inversion_contado": 0,
            "inversion_credito": 0,
            "inv_prod_vendidos": articulos * costo_actual,
            "ventas_contado": 0,
            "ventas_credito": 0,
            "articulos_vendidos": articulos,
            "ganancia": total_venta - (articulos * costo_actual)
        }

        totales[mes]["inv_prod_vendidos"] += fila["inv_prod_vendidos"]
        totales[mes]["articulos_vendidos"] += articulos
        totales[mes]["ganancia"] += fila["ganancia"]

        if tipo_pago == "contado":
            fila["ventas_contado"] = total_venta
            totales[mes]["ventas_contado"] += total_venta
        else:
            fila["ventas_credito"] = total_venta
            totales[mes]["ventas_credito"] += total_venta

        resumen.append(fila)

    # ======================
    # ORDENAR POR FECHA
    # ======================
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

def normalizar_pago(tipo):
    if not tipo:
        return "contado"

    tipo = tipo.lower().strip()

    if "credit" in tipo:
        return "credito"
    return "contado"
