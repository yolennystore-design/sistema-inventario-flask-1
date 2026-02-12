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
    # VENTAS (POR PRODUCTO, CON COSTO REAL)
    # ======================
    cur.execute("""
        SELECT
            v.fecha,
            v.tipo,
            v.cantidad,
            v.precio AS precio_venta,
            (
                SELECT c.costo
                FROM compras c
                WHERE c.id_producto = v.id_producto
                ORDER BY c.fecha DESC
                LIMIT 1
            ) AS precio_compra
        FROM ventas v
        ORDER BY v.fecha
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
    # PROCESAR VENTAS (GANANCIA REAL)
    # ======================
    for v in ventas:
        fecha = v["fecha"]
        mes = fecha[:7]
        tipo_pago = (v["tipo"] or "contado").lower()

        cantidad = float(v["cantidad"])
        precio_venta = float(v["precio_venta"])
        precio_compra = float(v["precio_compra"] or 0)

        venta_total = precio_venta * cantidad
        inversion_producto = precio_compra * cantidad
        ganancia = venta_total - inversion_producto

        init_mes(mes)

        fila = {
            "tipo": "VENTA",
            "mes": mes,
            "fecha": fecha,
            "inversion_total": 0,
            "inversion_contado": 0,
            "inversion_credito": 0,
            "inv_prod_vendidos": inversion_producto,
            "ventas_contado": venta_total if tipo_pago == "contado" else 0,
            "ventas_credito": venta_total if tipo_pago == "credito" else 0,
            "articulos_vendidos": cantidad,
            "ganancia": ganancia
        }

        totales[mes]["inv_prod_vendidos"] += inversion_producto
        totales[mes]["articulos_vendidos"] += cantidad
        totales[mes]["ganancia"] += ganancia

        if tipo_pago == "contado":
            totales[mes]["ventas_contado"] += venta_total
        else:
            totales[mes]["ventas_credito"] += venta_total

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
