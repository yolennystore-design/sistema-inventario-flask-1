# -*- coding: utf-8 -*-

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, session, flash, send_file
)
from io import BytesIO
import os
import json 

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Table,
    TableStyle,
    Image,
    Spacer   # 👈 ESTA LÍNEA ES LA CLAVE
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

from app.db import get_db
from app.utils.auditoria import registrar_log

creditos_bp = Blueprint("creditos", __name__, url_prefix="/creditos")


# ======================
# 📋 LISTADO + FILTROS
# ======================
@creditos_bp.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    cliente = request.args.get("cliente", "")
    estado = request.args.get("estado", "")

    conn = get_db()
    cur = conn.cursor()

    # Clientes únicos
    cur.execute("SELECT DISTINCT cliente FROM creditos ORDER BY cliente")
    clientes = [c["cliente"] for c in cur.fetchall()]

    query = """
        SELECT id, numero_factura, cliente, monto,
               abonado, pendiente, estado, fecha
        FROM creditos
        WHERE 1=1
    """
    params = []

    if cliente:
        query += " AND cliente = %s"
        params.append(cliente)

    if estado:
        query += " AND estado = %s"
        params.append(estado)

    query += " ORDER BY fecha DESC"

    cur.execute(query, params)
    creditos = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "creditos/index.html",
        creditos=creditos,
        clientes=clientes,
        cliente_sel=cliente,
        estado=estado
    )


# ======================
# 🔐 ABONAR (SOLO ADMIN)
# ======================
@creditos_bp.route("/abonar/<int:id>", methods=["POST"])
def abonar(id):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    if session.get("rol") != "admin":
        flash("⛔ Solo el administrador puede realizar abonos", "danger")
        return redirect(url_for("creditos.index"))

    abono = float(request.form["abono"])

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT abonado, pendiente
        FROM creditos
        WHERE id = %s
    """, (id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return redirect(url_for("creditos.index"))

    abonado = float(row["abonado"])
    pendiente = float(row["pendiente"])

    if abono <= 0 or abono > pendiente:
        flash("Monto de abono inválido", "danger")
        return redirect(url_for("creditos.index"))

    nuevo_abonado = abonado + abono
    nuevo_pendiente = pendiente - abono
    estado = "Pagado" if nuevo_pendiente == 0 else "Pendiente"

    cur.execute("""
        UPDATE creditos
        SET abonado = %s,
            pendiente = %s,
            estado = %s
        WHERE id = %s
    """, (
        nuevo_abonado,
        nuevo_pendiente,
        estado,
        id
    ))

    conn.commit()
    cur.close()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Abonó RD${abono:,.2f} al crédito #{id}",
        modulo="Créditos"
    )

    flash("✅ Abono realizado correctamente", "success")
    return redirect(url_for("creditos.index"))


# ======================
# 📝 SOLICITAR PERMISO (EMPLEADO)
# ======================
@creditos_bp.route("/solicitar_abono/<int:id>", methods=["POST"])
def solicitar_abono(id):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    monto = request.form.get("abono", "0")
    usuario = session["usuario"]

    registrar_log(
        usuario=usuario,
        accion=f"Solicitó permiso para abonar RD${monto} al crédito #{id}",
        modulo="Créditos"
    )

    flash(
        "📨 Solicitud enviada al administrador.",
        "info"
    )

    return redirect(url_for("creditos.index"))

# ======================
# 🧾 PDF DEL CRÉDITO
# ======================
@creditos_bp.route("/pdf/<numero_factura>")
def pdf_credito(numero_factura):
    if "usuario" not in session:
        return redirect(url_for("auth.login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT numero_factura, cliente, monto,
               abonado, pendiente, fecha, estado
        FROM creditos
        WHERE numero_factura = %s
    """, (numero_factura,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return redirect(url_for("creditos.index"))

    numero_factura = row["numero_factura"]
    cliente = row["cliente"]
    monto = float(row["monto"])
    abonado = float(row["abonado"])
    pendiente = float(row["pendiente"])
    fecha = row["fecha"]
    estado = row.get("estado", "Pendiente")

    # =========================
    # OBTENER PRODUCTOS DE LA VENTA
    # =========================
    items = []
    ruta_ventas = "app/data/ventas.json"
    if os.path.exists(ruta_ventas):
        with open(ruta_ventas, "r", encoding="utf-8") as f:
            ventas = json.load(f)
            venta = next(
                (v for v in ventas if v.get("numero_factura") == numero_factura),
                None
            )
            if venta:
                items = venta.get("items", [])

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    elementos = []

    # =========================
    # LOGO
    # =========================
    logo = "app/static/logo.png"
    if os.path.exists(logo):
        elementos.append(Image(logo, 100, 60))

    elementos.append(Spacer(1, 12))

    # =========================
    # ENCABEZADO
    # =========================
    elementos.append(Paragraph("<b>YOLENNY STORE</b>", styles["Title"]))
    elementos.append(Paragraph("Comprobante de Crédito", styles["Heading2"]))
    elementos.append(Spacer(1, 20))

    # =========================
    # DATOS GENERALES
    # =========================
    datos = [
        ["Factura No.", numero_factura],
        ["Cliente", cliente],
        ["Fecha", fecha],
        ["Estado del crédito", estado],
    ]

    tabla_datos = Table(datos, colWidths=[150, 300])
    tabla_datos.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))

    elementos.append(tabla_datos)
    elementos.append(Spacer(1, 20))

    # =========================
    # RESUMEN FINANCIERO
    # =========================
    resumen = [
        ["Monto Total", f"RD$ {monto:,.2f}"],
        ["Total Abonado", f"RD$ {abonado:,.2f}"],
        ["Saldo Pendiente", f"RD$ {pendiente:,.2f}"],
    ]

    tabla_resumen = Table(resumen, colWidths=[150, 300])
    tabla_resumen.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
    ]))

    elementos.append(Paragraph("<b>Resumen del Crédito</b>", styles["Heading3"]))
    elementos.append(Spacer(1, 8))
    elementos.append(tabla_resumen)
    elementos.append(Spacer(1, 25))

    # =========================
# PRODUCTOS DEL CRÉDITO
# =========================
if items:
    elementos.append(
        Paragraph("<b>Productos incluidos</b>", styles["Heading3"])
    )
    elementos.append(Spacer(1, 10))

    tabla_productos_data = [
        ["Fecha", "Producto", "Cant.", "Precio", "Subtotal"]
    ]

    for i in items:
        tabla_productos_data.append([
            fecha,
            i.get("nombre", ""),
            str(i.get("cantidad", 0)),
            f"RD$ {i.get('precio', 0):,.2f}",
            f"RD$ {i.get('total', 0):,.2f}",
        ])

    tabla_productos = Table(
        tabla_productos_data,
        colWidths=[90, 170, 50, 80, 80]
    )

    tabla_productos.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))

    elementos.append(tabla_productos)
    elementos.append(Spacer(1, 25))

    # =========================
    # NOTA FINAL
    # =========================
    elementos.append(
        Paragraph(
            "Este documento certifica el estado actual del crédito del cliente. "
            "Para cualquier aclaración, comuníquese con Yolenny Store.",
            styles["Normal"]
        )
    )

    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph("<i>¡Gracias por confiar en nosotros!</i>", styles["Italic"]))

    doc.build(elementos)

    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"credito_{numero_factura}.pdf"
    )


# ======================
# 🗑 ELIMINAR CRÉDITO (ADMIN)
# ======================
@creditos_bp.route("/eliminar/<int:id>")
def eliminar_credito(id):
    if session.get("rol") != "admin":
        return redirect(url_for("creditos.index"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT numero_factura FROM creditos WHERE id = %s",
        (id,)
    )
    row = cur.fetchone()

    if not row:
        conn.close()
        return redirect(url_for("creditos.index"))

    numero_factura = row["numero_factura"]

    cur.execute("DELETE FROM creditos WHERE id = %s", (id,))
    conn.commit()

    cur.close()
    conn.close()

    registrar_log(
        usuario=session["usuario"],
        accion=f"Eliminó crédito factura {numero_factura}",
        modulo="Créditos"
    )

    flash("🗑 Crédito eliminado correctamente", "success")
    return redirect(url_for("creditos.index"))
