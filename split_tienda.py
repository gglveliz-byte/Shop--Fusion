import re
import os

with open('tienda_backup.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define blocks based on function names.
# We will use regex to capture from `@bp.route` or `def ` until the next `@bp.route` or `def `.
# Since there are some comments before routes, we'll split by `@bp.route` and `def ` carefully.

blocks = re.split(r'\n(?=@bp\.route|def )', content)

# 0 is the header imports
header = blocks[0]

carrito_funcs = ['actualizar_carrito_session', 'carrito', 'agregar_carrito', 'actualizar_carrito', 'eliminar_carrito']
paypal_funcs = ['get_paypal_access_token', 'paypal_create_order', 'paypal_capture_order', 'paypal_webhook']
api_vendedor_funcs = ['get_vendedor_whatsapp', 'tienda_vendedor', 'producto_vendedor']

carrito_code = []
paypal_code = []
api_vendedor_code = []
tienda_code = []

for block in blocks[1:]:
    # find function name
    m = re.search(r'def\s+([a-zA-Z0-9_]+)\(', block)
    if not m:
        tienda_code.append(block)
        continue
    
    fname = m.group(1)
    if fname in carrito_funcs:
        carrito_code.append(block)
    elif fname in paypal_funcs:
        paypal_code.append(block)
    elif fname in api_vendedor_funcs:
        api_vendedor_code.append(block)
    else:
        tienda_code.append(block)

def write_module(filename, code_blocks, extra_imports=""):
    with open(f'routes/{filename}', 'w', encoding='utf-8') as f:
        f.write("from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify\n")
        f.write("from decimal import Decimal\n")
        f.write("from models import db, Producto, Pedido, Afiliado, Configuracion, Comision, Transaccion\n")
        f.write("from routes.tienda import bp\n")
        f.write("from utils.rate_limit import limiter\n")
        if extra_imports:
            f.write(extra_imports + "\n")
        f.write("\n")
        for b in code_blocks:
            f.write(b + "\n")

write_module('carrito.py', carrito_code)
write_module('paypal.py', paypal_code, extra_imports="import requests\nimport base64\nfrom utils.accounting import register_transaction\nfrom utils.security_logger import log_security_event")
write_module('api_vendedor.py', api_vendedor_code, extra_imports="from utils.validators import format_whatsapp")

# tienda.py remains the main one
with open('routes/tienda.py', 'w', encoding='utf-8') as f:
    f.write(header + "\n")
    for b in tienda_code:
        f.write(b + "\n")
    f.write("\n# Importar todas las subrutas modularizadas\n")
    f.write("from routes import carrito\n")
    f.write("from routes import paypal\n")
    f.write("from routes import api_vendedor\n")

print("Splitting complete.")
