# -*- coding: utf-8 -*-

STOCK_MINIMO = 5

def estado_stock(cantidad):
    if cantidad <= 0:
        return "agotado"
    elif cantidad <= STOCK_MINIMO:
        return "bajo"
    else:
        return "normal"





