import os

with open('tienda_backup.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

def get_block(start_match, end_match=None, count=1):
    # Extracts blocks manually
    pass

# We will just write a simpler extractor that goes line by line.
# A function block starts with `@bp.route` (sometimes preceded by comments) and ends when a new `@bp.route` or top-level `def ` starts, or EOF.

blocks = []
current_block = []
in_block = False

# Splitting by @bp.route or top-level def
for line in lines:
    if line.startswith('@bp.route') or line.startswith('def '):
        if current_block:
            blocks.append(current_block)
        current_block = [line]
    else:
        current_block.append(line)

if current_block:
    blocks.append(current_block)

# blocks[0] is the header
header = "".join(blocks[0])

carrito_funcs = ['actualizar_carrito_session', 'carrito', 'agregar_carrito', 'actualizar_carrito', 'eliminar_carrito']
paypal_funcs = ['get_paypal_access_token', 'paypal_create_order', 'paypal_capture_order', 'paypal_webhook']
api_vendedor_funcs = ['get_vendedor_whatsapp', 'tienda_vendedor', 'producto_vendedor']

carrito_code = []
paypal_code = []
api_vendedor_code = []
tienda_code = []

for block in blocks[1:]:
    block_str = "".join(block)
    # find function name
    # The block might start with @bp.route, so def is on the second or third line
    import re
    m = re.search(r'^def\s+([a-zA-Z0-9_]+)\(', block_str, re.MULTILINE)
    if not m:
        tienda_code.append(block_str)
        continue
    
    fname = m.group(1)
    if fname in carrito_funcs:
        carrito_code.append(block_str)
    elif fname in paypal_funcs:
        paypal_code.append(block_str)
    elif fname in api_vendedor_funcs:
        api_vendedor_code.append(block_str)
    else:
        tienda_code.append(block_str)

def write_module(filename, code_blocks, extra_imports=""):
    with open(f'routes/{filename}', 'w', encoding='utf-8') as f:
        f.write("from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify\n")
        f.write("from decimal import Decimal\n")
        f.write("from models import db, Producto, Pedido, Afiliado, Configuracion, Comision, Transaccion\n")
        f.write("from routes.tienda import bp\n")
        f.write("from utils.rate_limit import limiter\n")
        f.write("from utils.security_logger import log_security_event\n")
        if extra_imports:
            f.write(extra_imports + "\n")
        f.write("\n")
        for b in code_blocks:
            f.write(b)

write_module('carrito.py', carrito_code)
write_module('paypal.py', paypal_code, extra_imports="import requests\nimport base64\nfrom utils.accounting import register_transaction")
write_module('api_vendedor.py', api_vendedor_code, extra_imports="from utils.validators import format_whatsapp")

# tienda.py remains the main one
with open('routes/tienda.py', 'w', encoding='utf-8') as f:
    f.write(header)
    for b in tienda_code:
        f.write(b)
    f.write("\n# Importar todas las subrutas modularizadas\n")
    f.write("from routes import carrito\n")
    f.write("from routes import paypal\n")
    f.write("from routes import api_vendedor\n")

print("Splitting complete.")
