"""
Sub-rutas de tiendas de afiliados/vendedores y API pública de WhatsApp.
Extraído de routes/tienda.py en Fase 3.3 (Modularización).
"""
from flask import request, redirect, url_for, flash, session, current_app, jsonify, render_template
from models import db
from routes.tienda import bp
from utils.rate_limit import limiter
from utils.security_logger import log_security_event
from utils.validators import format_whatsapp


# ==================== TIENDA DE VENDEDOR ====================

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
