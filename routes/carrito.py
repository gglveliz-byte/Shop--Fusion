"""
Sub-rutas de gestión del carrito de compras.
Extraído de routes/tienda.py en Fase 3.3 (Modularización).
"""
from flask import render_template, request, redirect, url_for, flash, session, current_app, jsonify
from decimal import Decimal
from models import db
from routes.tienda import bp
from utils.rate_limit import limiter


@bp.route('/api/actualizar-carrito-session', methods=['POST'])
def actualizar_carrito_session():
    """Sincroniza el carrito del localStorage con la sesión de Flask"""
    try:
        data = request.get_json()
        carrito = data.get('carrito', [])
        session['carrito'] = carrito
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/carrito')
def carrito():
    """Ver carrito de compras"""
    from models import Producto

    carrito = session.get('carrito', [])

    # Obtener información completa de productos
    productos_carrito = []
    total = Decimal('0.00')

    for item in carrito:
        producto = Producto.query.get(item['id'])
        if producto and producto.activo:
            precio = producto.precio_venta()
            subtotal = precio * item['cantidad']

            productos_carrito.append({
                'producto': producto,
                'cantidad': item['cantidad'],
                'precio': precio,
                'subtotal': subtotal
            })

            total += subtotal

    afiliado_codigo = session.get('afiliado_codigo')

    return render_template('tienda/carrito.html',
                         productos=productos_carrito,
                         total=total,
                         afiliado_codigo=afiliado_codigo)


@bp.route('/carrito/agregar/<int:id>', methods=['POST'])
def agregar_carrito(id):
    """Agregar producto al carrito"""
    from models import Producto

    producto = Producto.query.get_or_404(id)

    if not producto.activo:
        flash('Este producto no está disponible', 'error')
        return redirect(url_for('tienda.index'))

    cantidad = int(request.form.get('cantidad', 1))

    if cantidad < 1:
        flash('La cantidad debe ser al menos 1', 'error')
        return redirect(url_for('tienda.producto_detalle', id=id))

    # Obtener carrito de sesión
    carrito = session.get('carrito', [])

    # Verificar si el producto ya está en el carrito
    producto_existente = False
    for item in carrito:
        if item['id'] == id:
            item['cantidad'] += cantidad
            producto_existente = True
            break

    # Si no existe, agregarlo
    if not producto_existente:
        carrito.append({
            'id': id,
            'cantidad': cantidad
        })

    session['carrito'] = carrito
    flash(f'{producto.nombre} agregado al carrito', 'success')

    return redirect(url_for('tienda.carrito'))


@bp.route('/carrito/actualizar/<int:id>', methods=['POST'])
def actualizar_carrito(id):
    """Actualizar cantidad de producto en carrito"""
    cantidad = int(request.form.get('cantidad', 1))

    carrito = session.get('carrito', [])

    for item in carrito:
        if item['id'] == id:
            if cantidad > 0:
                item['cantidad'] = cantidad
            else:
                carrito.remove(item)
            break

    session['carrito'] = carrito
    flash('Carrito actualizado', 'success')

    return redirect(url_for('tienda.carrito'))


@bp.route('/carrito/eliminar/<int:id>', methods=['POST'])
def eliminar_carrito(id):
    """Eliminar producto del carrito"""
    carrito = session.get('carrito', [])

    carrito = [item for item in carrito if item['id'] != id]

    session['carrito'] = carrito
    flash('Producto eliminado del carrito', 'success')

    return redirect(url_for('tienda.carrito'))
