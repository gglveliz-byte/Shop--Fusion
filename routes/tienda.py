"""
Rutas de la tienda pública
Home, productos, carrito, checkout
"""

# from app import csrf <-- ELIMINADO PARA EVITAR IMPORT CIRCULAR
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
    whatsapp_numero = format_whatsapp(current_app.config.get('WHATSAPP_NUMBER', ''))

    return render_template('tienda/producto.html',
                         producto=producto,
                         afiliado_codigo=None,
                         whatsapp_numero=whatsapp_numero,
                         es_tienda_vendedor=False)


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
        current_app.logger.error(f"Error interno al crear pedido: {str(e)}")
        return {'success': False, 'error': 'Ocurrió un error interno al procesar el pedido.'}, 500


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


@bp.route('/pedido-exitoso/<int:pedido_id>')
def pedido_exitoso(pedido_id):
    """Página de confirmación de pedido exitoso con PayPal"""
    from models import Pedido

    pedido = Pedido.query.get_or_404(pedido_id)

    return render_template('tienda/pedido_exitoso.html', pedido=pedido)


# Importar todas las subrutas modularizadas (al final para evitar importaciones circulares)
from routes import carrito
from routes import paypal
from routes import api_vendedor
