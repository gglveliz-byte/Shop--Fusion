"""
Rutas de la tienda pública
Home, productos, carrito, checkout
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from decimal import Decimal
import json
import requests
import base64

bp = Blueprint('tienda', __name__)


@bp.route('/')
def index():
    """Página principal de la tienda"""
    from models import Producto, Afiliado

    # Capturar código de afiliado si existe en la URL
    ref = request.args.get('ref')
    if ref:
        # Verificar que el código existe y el afiliado está activo
        afiliado = Afiliado.query.filter_by(codigo=ref, activo=True).first()
        if afiliado:
            session['afiliado_codigo'] = ref
            session.permanent = True  # Hacer la sesión permanente

    # Obtener productos activos
    productos_db = Producto.query.filter_by(activo=True).order_by(Producto.creado_en.desc()).all()

    # Convertir productos a diccionarios para JSON
    productos = []
    for p in productos_db:
        productos.append({
            'id': p.id,
            'nombre': p.nombre,
            'descripcion': p.descripcion,
            'precio_final': float(p.precio_final),
            'precio_oferta': float(p.precio_oferta) if p.precio_oferta else None,
            'imagen': p.imagen,
            'imagenes': p.imagenes if p.imagenes else []
        })

    # Verificar si hay código de afiliado en sesión
    afiliado_codigo = session.get('afiliado_codigo')

    return render_template('tienda/index.html',
                         productos=productos,
                         productos_db=productos_db,
                         afiliado_codigo=afiliado_codigo)


@bp.route('/producto/<int:id>')
def producto_detalle(id):
    """Detalle de un producto"""
    from models import Producto, Afiliado

    # Capturar código de afiliado si existe en la URL
    ref = request.args.get('ref')
    if ref:
        afiliado = Afiliado.query.filter_by(codigo=ref, activo=True).first()
        if afiliado:
            session['afiliado_codigo'] = ref
            session.permanent = True

    producto = Producto.query.get_or_404(id)

    if not producto.activo:
        flash('Este producto no está disponible', 'error')
        return redirect(url_for('tienda.index'))

    afiliado_codigo = session.get('afiliado_codigo')

    return render_template('tienda/producto.html',
                         producto=producto,
                         afiliado_codigo=afiliado_codigo)


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


@bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """Proceso de checkout"""
    from models import Producto, Pedido, Afiliado
    from app import db

    carrito = session.get('carrito', [])

    if not carrito:
        flash('Tu carrito está vacío', 'error')
        return redirect(url_for('tienda.index'))

    # Calcular total
    productos_pedido = []
    total = Decimal('0.00')

    for item in carrito:
        producto = Producto.query.get(item['id'])
        if producto and producto.activo:
            precio = producto.precio_venta()
            subtotal = precio * item['cantidad']

            productos_pedido.append({
                'id': producto.id,
                'nombre': producto.nombre,
                'cantidad': item['cantidad'],
                'precio': float(precio),
                'subtotal': float(subtotal)
            })

            total += subtotal

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        direccion = request.form.get('direccion')

        # Validaciones
        if not all([nombre, telefono, direccion]):
            flash('Por favor completa todos los campos', 'error')
            return render_template('tienda/checkout.html',
                                 productos=productos_pedido,
                                 total=total)

        # Obtener afiliado si existe en sesión
        afiliado_id = None
        afiliado_codigo = session.get('afiliado_codigo')
        if afiliado_codigo:
            afiliado = Afiliado.query.filter_by(codigo=afiliado_codigo, activo=True).first()
            if afiliado:
                afiliado_id = afiliado.id

        # Crear pedido
        pedido = Pedido(
            cliente_nombre=nombre,
            cliente_telefono=telefono,
            cliente_direccion=direccion,
            productos_json=productos_pedido,
            total=total,
            afiliado_id=afiliado_id,
            estado='pendiente'
        )

        db.session.add(pedido)
        db.session.commit()

        # Limpiar carrito
        session['carrito'] = []

        # Generar mensaje de WhatsApp
        mensaje = f"¡Hola! Quiero comprar:\n\n"

        for item in productos_pedido:
            mensaje += f"- {item['nombre']} x{item['cantidad']} - ${item['subtotal']:.2f}\n"

        mensaje += f"\nTotal: ${total:.2f}\n\n"
        mensaje += f"Mis datos:\n"
        mensaje += f"👤 {nombre}\n"
        mensaje += f"📱 {telefono}\n"
        mensaje += f"📍 {direccion}\n\n"
        mensaje += f"Pedido #{pedido.id}"

        # URL de WhatsApp
        whatsapp_numero = current_app.config['WHATSAPP_NUMBER']
        import urllib.parse
        mensaje_encoded = urllib.parse.quote(mensaje)
        whatsapp_url = f"https://wa.me/{whatsapp_numero}?text={mensaje_encoded}"

        return render_template('tienda/pedido_confirmado.html',
                             pedido=pedido,
                             whatsapp_url=whatsapp_url,
                             mensaje=mensaje)

    return render_template('tienda/checkout.html',
                         productos=productos_pedido,
                         total=total)


@bp.route('/api/crear-pedido', methods=['POST'])
def api_crear_pedido():
    """API para crear pedido desde SPA (sin recargar página)"""
    from models import Producto, Pedido, Afiliado
    from app import db

    try:
        data = request.get_json()

        nombre = data.get('nombre')
        telefono = data.get('telefono')
        direccion = data.get('direccion')
        carrito = data.get('carrito', [])

        # Validaciones
        if not all([nombre, telefono, direccion]):
            return {'success': False, 'error': 'Todos los campos son requeridos'}, 400

        if not carrito:
            return {'success': False, 'error': 'El carrito está vacío'}, 400

        # Calcular total y preparar productos
        productos_pedido = []
        total = Decimal('0.00')

        for item in carrito:
            producto = Producto.query.get(item['id'])
            if producto and producto.activo:
                precio = producto.precio_venta()
                cantidad = item['cantidad']
                subtotal = precio * cantidad

                productos_pedido.append({
                    'id': producto.id,
                    'nombre': producto.nombre,
                    'cantidad': cantidad,
                    'precio': float(precio),
                    'subtotal': float(subtotal)
                })

                total += subtotal

        # Obtener afiliado si existe en sesión
        afiliado_id = None
        afiliado_codigo = session.get('afiliado_codigo')
        if afiliado_codigo:
            afiliado = Afiliado.query.filter_by(codigo=afiliado_codigo, activo=True).first()
            if afiliado:
                afiliado_id = afiliado.id

        # Crear pedido
        pedido = Pedido(
            cliente_nombre=nombre,
            cliente_telefono=telefono,
            cliente_direccion=direccion,
            productos_json=productos_pedido,
            total=total,
            afiliado_id=afiliado_id,
            estado='pendiente'
        )

        db.session.add(pedido)
        db.session.commit()

        return {
            'success': True,
            'pedido_id': pedido.id,
            'total': float(total),
            'afiliado_codigo': afiliado_codigo
        }, 200

    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': str(e)}, 500


@bp.route('/unete')
def unete():
    """Página para unirse como afiliado"""
    # Mensaje pre-llenado para WhatsApp
    mensaje = "¡Hola! Me interesa trabajar como afiliado.\n\n¿Podrías darme más información sobre:\n- Comisiones\n- Cómo funciona\n- Requisitos\n\n¡Gracias!"

    whatsapp_numero = current_app.config['WHATSAPP_NUMBER']
    import urllib.parse
    mensaje_encoded = urllib.parse.quote(mensaje)
    whatsapp_url = f"https://wa.me/{whatsapp_numero}?text={mensaje_encoded}"

    return render_template('tienda/unete.html', whatsapp_url=whatsapp_url)


# ==================== PAYPAL INTEGRATION ====================

def get_paypal_access_token():
    """Obtener token de acceso de PayPal"""
    client_id = current_app.config['PAYPAL_CLIENT_ID']
    client_secret = current_app.config['PAYPAL_SECRET']
    mode = current_app.config['PAYPAL_MODE']

    if mode == 'live':
        url = "https://api-m.paypal.com/v1/oauth2/token"
    else:
        url = "https://api-m.sandbox.paypal.com/v1/oauth2/token"

    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(url, headers=headers, data="grant_type=client_credentials")

    if response.status_code == 200:
        return response.json()['access_token']
    return None


@bp.route('/api/paypal/create-order', methods=['POST'])
def paypal_create_order():
    """Crear orden de PayPal"""
    from models import Producto

    try:
        data = request.get_json()
        carrito = data.get('carrito', [])

        if not carrito:
            return jsonify({'error': 'Carrito vacío'}), 400

        # Calcular total
        total = Decimal('0.00')
        items = []

        for item in carrito:
            producto = Producto.query.get(item['id'])
            if producto and producto.activo:
                precio = producto.precio_venta()
                cantidad = item['cantidad']
                subtotal = precio * cantidad
                total += subtotal

                items.append({
                    "name": producto.nombre[:127],
                    "quantity": str(cantidad),
                    "unit_amount": {
                        "currency_code": "USD",
                        "value": f"{float(precio):.2f}"
                    }
                })

        # Obtener token de PayPal
        access_token = get_paypal_access_token()
        if not access_token:
            return jsonify({'error': 'Error de autenticación con PayPal'}), 500

        mode = current_app.config['PAYPAL_MODE']
        if mode == 'live':
            url = "https://api-m.paypal.com/v2/checkout/orders"
        else:
            url = "https://api-m.sandbox.paypal.com/v2/checkout/orders"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        order_data = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "USD",
                    "value": f"{float(total):.2f}",
                    "breakdown": {
                        "item_total": {
                            "currency_code": "USD",
                            "value": f"{float(total):.2f}"
                        }
                    }
                },
                "items": items
            }]
        }

        response = requests.post(url, headers=headers, json=order_data)

        if response.status_code in [200, 201]:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Error creando orden en PayPal'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/paypal/capture-order', methods=['POST'])
def paypal_capture_order():
    """Capturar pago de PayPal y crear pedido"""
    from models import Producto, Pedido, Afiliado
    from app import db

    try:
        data = request.get_json()
        order_id = data.get('orderID')
        nombre = data.get('nombre')
        telefono = data.get('telefono')
        direccion = data.get('direccion')
        carrito = data.get('carrito', [])

        if not all([order_id, nombre, telefono, direccion, carrito]):
            return jsonify({'error': 'Datos incompletos'}), 400

        # Capturar el pago en PayPal
        access_token = get_paypal_access_token()
        if not access_token:
            return jsonify({'error': 'Error de autenticación con PayPal'}), 500

        mode = current_app.config['PAYPAL_MODE']
        if mode == 'live':
            url = f"https://api-m.paypal.com/v2/checkout/orders/{order_id}/capture"
        else:
            url = f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers)

        if response.status_code not in [200, 201]:
            return jsonify({'error': 'Error capturando pago'}), 500

        paypal_response = response.json()

        if paypal_response.get('status') != 'COMPLETED':
            return jsonify({'error': 'Pago no completado'}), 400

        # Calcular total y preparar productos
        productos_pedido = []
        total = Decimal('0.00')

        for item in carrito:
            producto = Producto.query.get(item['id'])
            if producto and producto.activo:
                precio = producto.precio_venta()
                cantidad = item['cantidad']
                subtotal = precio * cantidad

                productos_pedido.append({
                    'id': producto.id,
                    'nombre': producto.nombre,
                    'cantidad': cantidad,
                    'precio': float(precio),
                    'subtotal': float(subtotal)
                })

                total += subtotal

        # Obtener afiliado si existe
        afiliado_id = None
        afiliado_codigo = session.get('afiliado_codigo')
        if afiliado_codigo:
            afiliado = Afiliado.query.filter_by(codigo=afiliado_codigo, activo=True).first()
            if afiliado:
                afiliado_id = afiliado.id

        # Crear pedido marcado como pagado
        pedido = Pedido(
            cliente_nombre=nombre,
            cliente_telefono=telefono,
            cliente_direccion=direccion,
            productos_json=productos_pedido,
            total=total,
            afiliado_id=afiliado_id,
            estado='pendiente'
        )

        db.session.add(pedido)
        db.session.commit()

        # Marcar como pagado (esto genera la comisión automáticamente)
        pedido.marcar_como_pagado()

        # Limpiar carrito de sesión
        session['carrito'] = []

        return jsonify({
            'success': True,
            'pedido_id': pedido.id,
            'total': float(total),
            'paypal_transaction_id': paypal_response.get('id')
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/pedido-exitoso/<int:pedido_id>')
def pedido_exitoso(pedido_id):
    """Página de confirmación de pedido exitoso con PayPal"""
    from models import Pedido

    pedido = Pedido.query.get_or_404(pedido_id)

    return render_template('tienda/pedido_exitoso.html', pedido=pedido)
