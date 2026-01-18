# -*- coding: utf-8 -*-
"""
Verificar productos en base de datos
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from app import create_app, db
from models import Producto

app = create_app()

with app.app_context():
    count = Producto.query.count()
    print(f'\n✓ Total productos en base de datos: {count}')

    print('\nPrimeros 10 productos:')
    productos = Producto.query.limit(10).all()
    for p in productos:
        print(f'  - {p.nombre} (${p.precio_final})')

    print('\n' + '='*60)
