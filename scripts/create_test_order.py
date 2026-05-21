import os
import sys
from datetime import datetime
import click

# Ensure the project root is in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from app import create_app, db
from models import Producto, Pedido

app = create_app()

@click.command()
@click.option('--product-name', default='Producto Test', help='Nombre del producto a crear (si no existe)')
@click.option('--price', default=10.0, help='Precio del producto')
@click.option('--stock', default=100, help='Cantidad de stock del producto')
@click.option('--quantity', default=2, help='Cantidad a ordenar en el pedido')
def create_test_order(product_name, price, stock, quantity):
    """Crea un producto (si no existe) y un pedido en estado *pendiente*.
    El pedido se guarda en la base de datos con los campos mínimos requeridos.
    """
    with app.app_context():
        # Buscar o crear producto
        producto = Producto.query.filter_by(nombre=product_name).first()
        if not producto:
            producto = Producto(
                nombre=product_name,
                descripcion='Producto de prueba generado automáticamente.',
                categoria='otros',
                precio_final=price,
                precio_proveedor=price * 0.8,
                stock=stock,
                activo=True,
                creado_en=datetime.utcnow()
            )
            db.session.add(producto)
            db.session.commit()
            click.echo(f'✅ Producto creado: {producto.id} - {producto.nombre}')
        else:
            click.echo(f'ℹ️  Producto existente: {producto.id} - {producto.nombre}')

        # Preparar items del pedido
        productos_json = [{
            'id': producto.id,
            'nombre': producto.nombre,
            'cantidad': quantity,
            'precio': float(producto.precio_venta()),
            'subtotal': float(producto.precio_venta() * quantity)
        }]
        total = sum(item['subtotal'] for item in productos_json)

        # Crear pedido en estado pendiente
        pedido = Pedido(
            cliente_nombre='Cliente Test',
            cliente_telefono='000000000',
            cliente_direccion='Dirección de prueba',
            productos_json=productos_json,
            total=total,
            estado='pendiente',
            creado_en=datetime.utcnow()
        )
        db.session.add(pedido)
        db.session.commit()
        click.echo(f'✅ Pedido creado en estado PENDIENTE: #{pedido.id}, total ${pedido.total}')

if __name__ == '__main__':
    create_test_order()
