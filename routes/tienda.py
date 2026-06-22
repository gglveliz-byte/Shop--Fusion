"""
Rutas de la tienda pública
Home, productos, carrito, checkout
"""

# from app import csrf  <-- ELIMINADO PARA EVITAR IMPORT CIRCULAR
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from decimal import Decimal
from models import db
import json
import requests
import base64
from utils.rate_limit import limiter
from utils.security_logger import log_security_event
from utils.validators import format_whatsapp

bp = Blueprint('tienda', __name__)


@bp.route('/')
def index():
    """Página principal de la tienda (Admin)"""
    from models import Producto, Afiliado, CATEGORIAS_PRODUCTO
    from sqlalchemy import func

    # Si viene código de vendedor, redirigir a su tienda
    ref = request.args.get('ref')
    if ref:
        afiliado = Afiliado.query.filter_by(codigo=ref, activo=True).first()
        if afiliado:
            # Redirigir a la tienda del vendedor
            return redirect(url_for('tienda.tienda_vendedor', codigo=ref))

    # Obtener productos activos
    productos_db = Producto.query.filter_by(activo=True).order_by(Producto.creado_en.desc()).all()

    # Obtener categorías que tienen productos activos
    categorias_con_productos = db.session.query(
        Producto.categoria,
        func.count(Producto.id).label('count')
    ).filter(Producto.activo == True).group_by(Producto.categoria).all()

    # Crear diccionario de categorías con sus conteos
    categorias_activas = {}
    for cat, count in categorias_con_productos:
        if cat:
            # Buscar el nombre legible de la categoría
            nombre_cat = cat
            for valor, nombre in CATEGORIAS_PRODUCTO:
                if valor == cat:
                    nombre_cat = nombre
                    break
            categorias_activas[cat] = {'nombre': nombre_cat, 'count': count}

    # FASE 4: Serialización optimizada y unificada (DRY)
    productos = [p.to_dict() for p in productos_db]

    # Número de WhatsApp del admin
    whatsapp_numero = format_whatsapp(current_app.config.get('WHATSAPP_NUMBER', ''))

    return render_template('tienda/index.html',
                         productos=productos,
                         productos_db=productos_db,
                         categorias=categorias_activas,
                         afiliado_codigo=None,  # Tienda principal sin afiliado
                         whatsapp_numero=whatsapp_numero,
                         es_tienda_vendedor=False)


@bp.route('/producto/<int:id>')
def producto_detalle(id):
    """Detalle de un producto"""
    from models import Producto, Afiliado

    # Si viene código de vendedor, redirigir a su tienda
    ref = request.args.get('ref')
    if ref:
        afiliado = Afiliado.query.filter_by(codigo=ref, activo=True).first()
        if afiliado:
            return redirect(url_for('tienda.producto_vendedor', id=id, codigo=ref))

    producto = Producto.query.get_or_404(id)

    if not producto.activo:
        flash('Este producto no está disponible', 'error')
        return redirect(url_for('tienda.index'))

    # WhatsApp del admin (FASE 4: Reutilización de utils/validators.py)
    from utils.validators import format_whatsapp
    whatsapp_numero = format_whatsapp(current_app.config.get('WHATSAPP_NUMBER', ''))

    return render_template('tienda/producto.html',
                         producto=producto,
                         afiliado_codigo=None,
                         whatsapp_numero=whatsapp_numero,
                         es_tienda_vendedor=False)


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

    #INICIA LOS CAMBIOS INDICADOS EN FASE 3
    # RECALCULO DE SEGURIDAD Y VALIDACIÓN DE STOCK (Mitiga E42 y E41): 
    # Ignoramos precios enviados por JS y verificamos disponibilidad en DB.
    for item in carrito:
        producto = Producto.query.get(item['id'])
        if producto and producto.activo:
            cantidad = int(item['cantidad'])
            # Validación de inventario previa al procesamiento
            if not producto.esta_disponible(cantidad):
                flash(f'Lo sentimos, no hay stock suficiente de: {producto.nombre}', 'error')
                return redirect(url_for('tienda.carrito'))
            
            precio = producto.precio_venta()
            subtotal = precio * cantidad

            productos_pedido.append({
                'id': producto.id,
                'nombre': producto.nombre,
                'cantidad': cantidad,
                'precio': float(precio),
                'subtotal': float(subtotal)
            })

            total += subtotal
    #FIN DE LOS CAMBIOS INDICADOS EN FASE 3

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
        
        #INICIA LOS CAMBIOS INDICADOS EN FASE 3
        # SUSTRACCIÓN FORZOSA (Mitiga E41): Descontar inventario tras creación exitosa
        for item in carrito:
            """Correccion grave models.py, bloqueo pesimista:
            Usamos .with_for_update() para bloquear el registro y evitar que otro usuario
            compre el mismo producto al mismo tiempo. Luego verificamos que el producto este activo"""
            producto = Producto.query.filter_by(id=item['id'], activo=True).with_for_update().first()
            if producto:
                producto.reducir_stock(int(item['cantidad']))
        #FIN DE LOS CAMBIOS INDICADOS EN FASE 3
        
        db.session.commit()

        # Limpiar carrito
        session['carrito'] = []

        # Generar mensaje de WhatsApp
        from models import Configuracion
        config_web = Configuracion.query.first()
        nombre_tienda = config_web.nombre_tienda if config_web else "la tienda"
        
        mensaje = f"¡Hola {nombre_tienda}! Quiero comprar:\n\n"

        for item in productos_pedido:
            mensaje += f"- {item['nombre']} x{item['cantidad']} - ${item['subtotal']:.2f}\n"

        mensaje += f"\nTotal: ${total:.2f}\n\n"
        mensaje += f"Mis datos:\n"
        mensaje += f"👤 {nombre}\n"
        mensaje += f"📱 {telefono}\n"
        mensaje += f"📍 {direccion}\n\n"
        mensaje += f"Pedido #{pedido.id}"

        # URL de WhatsApp - usar del vendedor si existe, sino del admin
        whatsapp_numero = current_app.config['WHATSAPP_NUMBER']
        if afiliado_codigo:
            afiliado = Afiliado.query.filter_by(codigo=afiliado_codigo, activo=True).first()
            if afiliado and afiliado.whatsapp:
                whatsapp_numero = afiliado.whatsapp
        
        # Formatear número (FASE 4: Reutilización de utils/validators.py)
        from utils.validators import format_whatsapp
        whatsapp_numero = format_whatsapp(whatsapp_numero)

        import urllib.parse
        mensaje_encoded = urllib.parse.quote(mensaje)
        whatsapp_url = f"https://wa.me/{whatsapp_numero}?text={mensaje_encoded}"

        return render_template('tienda/pedido_confirmado.html',
                             pedido=pedido,
                             whatsapp_url=whatsapp_url,
                             mensaje=mensaje)

    # Calcular total con comisión PayPal (5.4%)
    comision_paypal = Decimal('5.4')
    total_con_paypal = total * (Decimal('1') + (comision_paypal / Decimal('100')))
    recargo_paypal = total_con_paypal - total

    # Obtener código de vendedor si existe
    afiliado_codigo = session.get('afiliado_codigo')
    vendedor = None
    if afiliado_codigo:
        vendedor = Afiliado.query.filter_by(codigo=afiliado_codigo, activo=True).first()

    return render_template('tienda/checkout.html',
                         productos=productos_pedido,
                         total=total,
                         total_con_paypal=total_con_paypal,
                         recargo_paypal=recargo_paypal,
                         comision_paypal=comision_paypal,
                         afiliado_codigo=afiliado_codigo,
                         vendedor=vendedor)


@bp.route('/api/crear-pedido', methods=['POST'])
@limiter.limit("3 per minute", error_message='Demasiados pedidos en poco tiempo. Por seguridad, espera un momento.')
def finalizar_pedido():
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

        #INICIA LOS CAMBIOS INDICADOS EN FASE 3
        # RECALCULO DE SEGURIDAD Y VALIDACIÓN DE STOCK (Mitiga E42 y E41): 
        # Ignoramos precios enviados por JS y verificamos disponibilidad en DB.
        productos_pedido = []
        total = Decimal('0.00')

        for item in carrito:
            producto = Producto.query.get(item['id'])
            if producto and producto.activo:
                cantidad = int(item['cantidad'])
                
                # Validación de inventario previa al procesamiento
                if not producto.esta_disponible(cantidad):
                    return {'success': False, 'error': f'Stock insuficiente de {producto.nombre}'}, 400
                
                # El precio se obtiene del servidor, NO del cliente.
                precio = producto.precio_venta() 
                subtotal = precio * cantidad

                productos_pedido.append({
                    'id': producto.id,
                    'nombre': producto.nombre,
                    'cantidad': cantidad,
                    'precio': float(precio),
                    'subtotal': float(subtotal)
                })

                total += subtotal
        #FIN DE LOS CAMBIOS INDICADOS EN FASE 3

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
        
        #INICIA LOS CAMBIOS INDICADOS EN FASE 3
        # SUSTRACCIÓN FORZOSA (Mitiga E41): Descontar inventario en DB
        for item in carrito:
            producto = Producto.query.get(item['id'])
            if producto:
                producto.reducir_stock(int(item['cantidad']))
        #FIN DE LOS CAMBIOS INDICADOS EN FASE 3
        
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
    from models import Configuracion
    config_web = Configuracion.query.first()
    nombre_tienda = config_web.nombre_tienda if config_web else "la tienda"
    
    mensaje = f"¡Hola {nombre_tienda}! Me interesa trabajar como afiliado.\n\n¿Podrías darme más información sobre:\n- Comisiones\n- Cómo funciona\n- Requisitos\n\n¡Gracias!"

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
@limiter.limit("3 per minute", error_message='Demasiados intentos de pago. Por seguridad, espera un momento.')
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

        #INICIA LOS CAMBIOS INDICADOS EN FASE 3
        # RECALCULO DE SEGURIDAD (Mitiga E42): Uso de precio oficial desde DB
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
        #FIN DE LOS CAMBIOS INDICADOS EN FASE 3

        # Agregar comisión PayPal (5.4%)
        comision_paypal = Decimal('5.4')
        total_con_comision = total * (Decimal('1') + (comision_paypal / Decimal('100')))
        recargo_paypal = total_con_comision - total

        # Agregar el recargo como item separado en PayPal
        items.append({
            "name": f"Comisión PayPal/Tarjeta ({comision_paypal}%)",
            "quantity": "1",
            "unit_amount": {
                "currency_code": "USD",
                "value": f"{float(recargo_paypal):.2f}"
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
                    "value": f"{float(total_con_comision):.2f}",
                    "breakdown": {
                        "item_total": {
                            "currency_code": "USD",
                            "value": f"{float(total_con_comision):.2f}"
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
        current_app.logger.exception(f"Error fatal creando orden de PayPal: {e}")
        return jsonify({'error': 'Error interno al procesar el pago'}), 500


@bp.route('/api/paypal/capture-order', methods=['POST'])
def paypal_capture_order():
    """Capturar pago de PayPal y crear pedido"""
    from models import Producto, Pedido, Afiliado
    from app import db
    from utils.accounting import register_transaction

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

        # Asegurarnos de enviar un cuerpo vacío (json={}) para evitar error 400/415 de PayPal
        response = requests.post(url, headers=headers, json={})

        if response.status_code not in [200, 201]:
            error_details = response.text
            print(f"DEBUG PAYPAL CAPTURE ERROR: {error_details}")
            return jsonify({'error': f'Error capturando pago con PayPal. Detalles internos: {error_details}'}), 500

        paypal_response = response.json()

        if paypal_response.get('status') != 'COMPLETED':
            return jsonify({'error': 'Pago no completado'}), 400

        # Calcular total y preparar productos
        productos_pedido = []
        total = Decimal('0.00')

        #INICIA LOS CAMBIOS INDICADOS EN FASE 3
        # RECALCULO DE SEGURIDAD (Mitiga E42): Uso de precio oficial desde DB
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
        #FIN DE LOS CAMBIOS INDICADOS EN FASE 3

        # Calcular total con comisión PayPal (5.4%)
        comision_paypal = Decimal('5.4')
        total_con_comision = total * (Decimal('1') + (comision_paypal / Decimal('100')))

        # Obtener afiliado si existe
        afiliado_id = None
        afiliado_codigo = session.get('afiliado_codigo')
        if afiliado_codigo:
            afiliado = Afiliado.query.filter_by(codigo=afiliado_codigo, activo=True).first()
            if afiliado:
                afiliado_id = afiliado.id

        # Crear pedido marcado como pagado (PayPal ya procesó el pago)
        # Guardamos el total CON comisión PayPal ya que ese es el monto que se cobró
        pedido = Pedido(
            cliente_nombre=nombre,
            cliente_telefono=telefono,
            cliente_direccion=direccion,
            productos_json=productos_pedido,
            total=total_con_comision,  # Total con comisión PayPal
            afiliado_id=afiliado_id,
            estado='pagado'  # Ya está pagado con PayPal
        )

        db.session.add(pedido)
        db.session.commit()

        # Si tiene vendedor, marcar como pagado y validar automáticamente
        if afiliado_id:
            pedido.marcar_como_pagado()
            # Validar automáticamente para que admin lo vea (PayPal es pago confirmado)
            pedido.validar_para_admin()
        else:
            # Pedido sin vendedor (tienda principal), solo marcar como pagado
            pedido.marcar_como_pagado()

        # --- SINCRONIZACIÓN CONTABLE AUTOMÁTICA ---
        # 1. Registrar el Ingreso Bruto
        monto_bruto = float(total_con_comision)
        register_transaction(
            tipo='ingreso',
            monto=monto_bruto,
            categoria='venta',
            fuente='paypal',
            descripcion=f"Venta PayPal - Pedido #{pedido.id}",
            referencia_id=paypal_response.get('id')
        )

        # 2. Registrar el Gasto por Comisión de PayPal (Recargo)
        monto_comision = float(total_con_comision - total)
        if monto_comision > 0:
            register_transaction(
                tipo='gasto',
                monto=monto_comision,
                categoria='comision',
                fuente='paypal',
                descripcion=f"Comisión PayPal - Pedido #{pedido.id}",
                referencia_id=f"FEE-{paypal_response.get('id')}"
            )

        # 3. Generar Factura Automática
        from utils.billing import calculate_invoice_data
        from models import Factura
        try:
            datos_fac = calculate_invoice_data(pedido)
            nueva_f = Factura(
                numero_factura=Factura.generar_numero_correlativo(),
                pedido_id=pedido.id,
                subtotal=datos_fac['subtotal'],
                iva_porcentaje=datos_fac['iva_porcentaje'],
                iva_monto=datos_fac['iva_monto'],
                total=datos_fac['total']
            )
            db.session.add(nueva_f)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error Factura Automática: {str(e)}")

        # Limpiar carrito de sesión
        session['carrito'] = []

        return jsonify({
            'success': True,
            'pedido_id': pedido.id,
            'total': float(total_con_comision),
            'paypal_transaction_id': paypal_response.get('id')
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error fatal capturando orden de PayPal: {e}")
        return jsonify({'error': 'No se pudo confirmar el pago. Contacta a soporte.'}), 500


@bp.route('/pedido-exitoso/<int:pedido_id>')
def pedido_exitoso(pedido_id):
    """Página de confirmación de pedido exitoso con PayPal"""
    from models import Pedido

    pedido = Pedido.query.get_or_404(pedido_id)

    return render_template('tienda/pedido_exitoso.html', pedido=pedido)


@bp.route('/api/get-vendedor-whatsapp')
@limiter.limit("5 per minute", error_message='Límite de solicitudes excedido. Intenta más tarde.')
def get_vendedor_whatsapp():
    """Obtener WhatsApp del vendedor por código (Protegido contra scraping)"""
    from models import Afiliado
    
    # SEGURIDAD CRÍTICA: Prevenir el scraping automatizado limitando llamadas externas
    referer = request.headers.get('Referer', '')
    if not referer or request.host not in referer:
        log_security_event('SCRAPING_ATTEMPT', 'BLOCKED', details="Intento de extracción de número de WhatsApp desde origen no autorizado")
        return jsonify({'error': 'Acceso denegado por políticas de seguridad (Restricción de Origen)'}), 403
    
    codigo = request.args.get('codigo')
    if not codigo:
        return jsonify({'error': 'Código no proporcionado'}), 400
    
    vendedor = Afiliado.query.filter_by(codigo=codigo, activo=True).first()
    if not vendedor:
        return jsonify({'error': 'Vendedor no encontrado'}), 404
    
    whatsapp = format_whatsapp(vendedor.whatsapp or current_app.config.get('WHATSAPP_NUMBER', ''))
    
    return jsonify({'whatsapp': whatsapp})


# ==================== TIENDA DE VENDEDOR ====================

@bp.route('/vendedor/<codigo>')
def tienda_vendedor(codigo):
    """Tienda del vendedor (afiliado)"""
    from models import Producto, Afiliado, CATEGORIAS_PRODUCTO
    from sqlalchemy import func

    # Verificar que el vendedor existe y está activo
    vendedor = Afiliado.query.filter_by(codigo=codigo, activo=True).first_or_404()
    
    # Guardar código en sesión para el checkout
    session['afiliado_codigo'] = codigo
    session.permanent = True

    # Obtener productos activos
    productos_db = Producto.query.filter_by(activo=True).order_by(Producto.creado_en.desc()).all()

    # Obtener categorías que tienen productos activos
    categorias_con_productos = db.session.query(
        Producto.categoria,
        func.count(Producto.id).label('count')
    ).filter(Producto.activo == True).group_by(Producto.categoria).all()

    # Crear diccionario de categorías con sus conteos
    categorias_activas = {}
    for cat, count in categorias_con_productos:
        if cat:
            nombre_cat = cat
            for valor, nombre in CATEGORIAS_PRODUCTO:
                if valor == cat:
                    nombre_cat = nombre
                    break
            categorias_activas[cat] = {'nombre': nombre_cat, 'count': count}

    # FASE 4: Serialización optimizada y unificada (DRY)
    productos = [p.to_dict() for p in productos_db]

    # WhatsApp del vendedor (FASE 4: Reutilización de utils/validators.py)
    from utils.validators import format_whatsapp
    whatsapp_numero = format_whatsapp(vendedor.whatsapp or current_app.config.get('WHATSAPP_NUMBER', ''))

    return render_template('tienda/index.html',
                         productos=productos,
                         productos_db=productos_db,
                         categorias=categorias_activas,
                         afiliado_codigo=codigo,
                         whatsapp_numero=whatsapp_numero,
                         vendedor=vendedor,
                         es_tienda_vendedor=True)


@bp.route('/vendedor/<codigo>/producto/<int:id>')
def producto_vendedor(id, codigo):
    """Detalle de producto en tienda del vendedor"""
    from models import Producto, Afiliado

    # Verificar que el vendedor existe y está activo
    vendedor = Afiliado.query.filter_by(codigo=codigo, activo=True).first_or_404()
    
    # Guardar código en sesión
    session['afiliado_codigo'] = codigo
    session.permanent = True

    producto = Producto.query.get_or_404(id)

    if not producto.activo:
        flash('Este producto no está disponible', 'error')
        return redirect(url_for('tienda.tienda_vendedor', codigo=codigo))

    # WhatsApp del vendedor
    whatsapp_numero = vendedor.whatsapp or current_app.config.get('WHATSAPP_NUMBER', '')
    if whatsapp_numero.startswith('0'):
        whatsapp_numero = '593' + whatsapp_numero[1:]
    elif not whatsapp_numero.startswith('+') and not whatsapp_numero.startswith('593'):
        whatsapp_numero = '593' + whatsapp_numero

    return render_template('tienda/producto.html',
                         producto=producto,
                         afiliado_codigo=codigo,
                         whatsapp_numero=whatsapp_numero,
                         vendedor=vendedor,
                         es_tienda_vendedor=True)

#INICIA LOS CAMBIOS INDICADOS EN FASE 3
@bp.route('/paypal-webhook', methods=['POST'])
def paypal_webhook():
    """
    [FASE 4 / E43 - ERRORES MEDIOS] Blindaje Transaccional
    Maneja notificaciones asíncronas de PayPal para evitar pérdida de pedidos.
    ¡SEGURIDAD CRÍTICA APLICADA!: Verificación criptográfica de la firma del webhook.
    """
    from models import Pedido
    from app import db
    import requests
    
    # 1. Extraer cabeceras criptográficas de PayPal
    auth_algo = request.headers.get('PAYPAL-AUTH-ALGO')
    cert_url = request.headers.get('PAYPAL-CERT-URL')
    transmission_id = request.headers.get('PAYPAL-TRANSMISSION-ID')
    transmission_sig = request.headers.get('PAYPAL-TRANSMISSION-SIG')
    transmission_time = request.headers.get('PAYPAL-TRANSMISSION-TIME')

    # 2. Validación: Si falta alguna cabecera, bloquear el intento (posible spoofing)
    if not all([auth_algo, cert_url, transmission_id, transmission_sig, transmission_time]):
        log_security_event('PAYPAL_WEBHOOK', 'BLOCKED', details="Intento de webhook sin cabeceras criptográficas válidas.")
        return jsonify({'error': 'Violación de seguridad: Faltan firmas criptográficas'}), 403

    try:
        data = request.get_json()
        if not data:
            current_app.logger.warning("Webhook de PayPal recibido sin datos JSON")
            return jsonify({'status': 'no_data'}), 400

        # 3. Verificación Criptográfica mediante API oficial de PayPal
        access_token = get_paypal_access_token()
        webhook_id = current_app.config.get('PAYPAL_WEBHOOK_ID')

        if not access_token:
            current_app.logger.error("No se pudo obtener el token de PayPal para verificar el webhook")
            return jsonify({'error': 'Error de autenticación interna'}), 500
            
        if not webhook_id:
            current_app.logger.error("VULNERABILIDAD CRÍTICA: PAYPAL_WEBHOOK_ID no está configurado. Rechazando webhook por seguridad.")
            return jsonify({'error': 'Sistema no configurado para validación criptográfica'}), 500

        # Validación estricta obligatoria contra PayPal
        mode = current_app.config.get('PAYPAL_MODE', 'sandbox')
        verify_url = "https://api-m.paypal.com/v1/notifications/verify-webhook-signature" if mode == 'live' else "https://api-m.sandbox.paypal.com/v1/notifications/verify-webhook-signature"
        
        verify_payload = {
            "auth_algo": auth_algo,
            "cert_url": cert_url,
            "transmission_id": transmission_id,
            "transmission_sig": transmission_sig,
            "transmission_time": transmission_time,
            "webhook_id": webhook_id,
            "webhook_event": data
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        resp = requests.post(verify_url, headers=headers, json=verify_payload)
        if resp.status_code == 200:
            verification_status = resp.json().get('verification_status')
            if verification_status != 'SUCCESS':
                log_security_event('PAYPAL_WEBHOOK', 'BLOCKED', details="Firma criptográfica manipulada (rechazada por PayPal)")
                return jsonify({'error': 'Firma criptográfica inválida. Pago falso detectado.'}), 403
        else:
            current_app.logger.error(f"Fallo verificando firma de PayPal: {resp.text}")
            return jsonify({'error': 'Error comunicando con PayPal para validación'}), 502

        # 4. Procesamiento Seguro del Evento (Solo si la validación criptográfica pasó o no está configurado el webhook_id)
        event_type = data.get('event_type')
        resource = data.get('resource', {})
        current_app.logger.info(f"Webhook PayPal recibido y validado: {event_type}")

        # Verificamos eventos de pago completado
        if event_type in ['PAYMENT.CAPTURE.COMPLETED', 'CHECKOUT.ORDER.APPROVED']:
            paypal_id = resource.get('id')
            custom_id = resource.get('custom_id') 
            
            if custom_id:
                pedido = Pedido.query.get(custom_id)
                if pedido and pedido.estado != 'pagado':
                    pedido.estado = 'pagado'
                    pedido.marcar_como_pagado()
                    db.session.commit()
                    current_app.logger.info(f"Pedido {custom_id} actualizado a 'pagado' vía Webhook Seguro")
            
            return jsonify({'status': 'procesado_seguro'}), 200

        return jsonify({'status': 'evento_no_critico'}), 200

    except Exception as e:
        current_app.logger.error(f"Error procesando Webhook de PayPal: {e}")
        return jsonify({'status': 'error_interno'}), 500

#FIN DE LOS CAMBIOS INDICADOS EN FASE 4