from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
import os

def generar_factura(venta, ruta):
    c = canvas.Canvas(ruta, pagesize=LETTER)
    width, height = LETTER

    y = height - 40

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "FACTURA DE VENTA")
    y -= 30

    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Cliente: {venta['cliente']}")
    y -= 15
    c.drawString(50, y, f"Fecha: {venta['fecha']}")
    y -= 15
    c.drawString(50, y, f"Tipo de pago: {venta['tipo_pago']}")
    y -= 25

    c.drawString(50, y, "Productos:")
    y -= 15

    for item in venta["items"]:
        c.drawString(
            60,
            y,
            f"{item['cantidad']} x {item['nombre']} @ {item['precio']} = {item['total']}"
        )
        y -= 15

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, f"TOTAL: ${venta['total']}")

    c.showPage()
    c.save()
