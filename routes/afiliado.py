"""
Rutas del panel de afiliado
Ver productos con comisiones, ver comisiones ganadas
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from sqlalchemy.orm import joinedload
from flask_login import login_required, current_user
from decimal import Decimal
from models import db
from utils.validators import validate_whatsapp, is_strong_password

bp = Blueprint('afiliado', __name__, url_prefix='/afiliado')


def afiliado_required(f):
    """Decorador para verificar que el usuario sea afiliado"""
    @login_required
    def decorated_function(*args, **kwargs):
        from models import Afiliado
        if not isinstance(current_user, Afiliado):
            flash('Acceso denegado. Solo afiliados.', 'error')
            return redirect(url_for('tienda.index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


@bp.route('/dashboard')
@afiliado_required
def dashboard():
    """Dashboard del vendedor"""
    from models import Comision, Pedido

    afiliado = current_user

    # Estadísticas de comisiones
    total_pendiente = afiliado.total_comisiones_pendientes()
    total_generado = afiliado.total_comisiones_generadas()
    total_pagado = afiliado.total_comisiones_pagadas()
    total_ganado = afiliado.total_ganado()

    # Últimas comisiones
    ultimas_comisiones = Comision.query.filter_by(afiliado_id=afiliado.id)\
        .order_by(Comision.creado_en.desc()).limit(5).all()

    # FASE 3: Optimización - Consultas agrupadas para métricas
    from sqlalchemy import func
    estados = db.session.query(Pedido.estado, func.count(Pedido.id))\
        .filter(Pedido.afiliado_id == afiliado.id)\
        .group_by(Pedido.estado).all()

    total_pedidos = sum(count for _, count in estados)
    pedidos_pendientes = next((count for est, count in estados if est == 'pendiente'), 0)
    pedidos_pagados = next((count for est, count in estados if est == 'pagado'), 0)
    pedidos_validados = db.session.query(func.count(Pedido.id))\
        .filter(Pedido.afiliado_id == afiliado.id, Pedido.validado_por_vendedor == True).scalar() or 0

    # Link de la tienda del vendedor
    link_tienda = url_for('tienda.tienda_vendedor', codigo=afiliado.codigo, _external=True)

    return render_template('afiliado/dashboard.html',
                         afiliado=afiliado,
                         total_pendiente=total_pendiente,
                         total_generado=total_generado,
                         total_pagado=total_pagado,
                         total_ganado=total_ganado,
                         ultimas_comisiones=ultimas_comisiones,
                         total_pedidos=total_pedidos,
                         pedidos_pendientes=pedidos_pendientes,
                         pedidos_pagados=pedidos_pagados,
                         pedidos_validados=pedidos_validados,
                         link_tienda=link_tienda)


@bp.route('/productos')
@afiliado_required
def productos():
    """Ver productos con información de comisiones"""
    from models import Producto, CATEGORIAS_PRODUCTO
    from sqlalchemy import func
    from models import db

    afiliado = current_user
    
    # FASE 3: Paginación de productos en vista de afiliado
    page = request.args.get('page', 1, type=int)
    pagination = Producto.query.filter_by(activo=True).order_by(Producto.creado_en.desc()).paginate(page=page, per_page=12, error_out=False)
    productos = pagination.items

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

    # Agregar información de comisión a cada producto
    productos_con_comision = []
    for producto in productos:
        margen = producto.calcular_margen()
        comision = producto.calcular_comision_afiliado(afiliado.porcentaje_comision)

        productos_con_comision.append({
            'producto': producto,
            'categoria': producto.categoria or 'otros',
            'margen': margen,
            'comision': comision,
            'link': url_for('tienda.producto_vendedor', id=producto.id, codigo=afiliado.codigo, _external=True)
        })

    return render_template('afiliado/productos.html',
                         productos=productos_con_comision,
                         categorias=categorias_activas,
                         afiliado=afiliado,
                         pagination=pagination)


@bp.route('/comisiones')
@afiliado_required
def comisiones():
    """Ver todas las comisiones del afiliado"""
    from models import Comision

    afiliado = current_user

    # Filtro por estado
    estado_filter = request.args.get('estado', 'todos')

    # [FASE 3 / E11 - ERRORES MEDIOS] Optimización N+1: Cargar el pedido asociado a cada comisión
    query = Comision.query.options(joinedload(Comision.pedido)).filter_by(afiliado_id=afiliado.id)
    if estado_filter != 'todos':
        query = query.filter_by(estado=estado_filter)

    comisiones = query.order_by(Comision.creado_en.desc()).all()

    # Totales
    total_pendiente = afiliado.total_comisiones_pendientes()
    total_generado = afiliado.total_comisiones_generadas()
    total_pagado = afiliado.total_comisiones_pagadas()
    total_ganado = afiliado.total_ganado()

    return render_template('afiliado/comisiones.html',
                         comisiones=comisiones,
                         estado_filter=estado_filter,
                         total_pendiente=total_pendiente,
                         total_generado=total_generado,
                         total_pagado=total_pagado,
                         total_ganado=total_ganado)


@bp.route('/pedidos')
@afiliado_required
def pedidos():
    """Ver pedidos generados por el vendedor"""
    from models import Pedido

    afiliado = current_user

    estado_filter = request.args.get('estado', 'todos')
    
    query = Pedido.query.filter_by(afiliado_id=afiliado.id)
    if estado_filter != 'todos':
        query = query.filter_by(estado=estado_filter)

    pedidos = query.order_by(Pedido.creado_en.desc()).all()

    # FASE 3: Optimización - Consultas agrupadas para métricas
    from sqlalchemy import func
    estados = db.session.query(Pedido.estado, func.count(Pedido.id))\
        .filter(Pedido.afiliado_id == afiliado.id)\
        .group_by(Pedido.estado).all()

    total_pedidos = sum(count for _, count in estados)
    pedidos_pendientes = next((count for est, count in estados if est == 'pendiente'), 0)
    pedidos_pagados = next((count for est, count in estados if est == 'pagado'), 0)
    pedidos_validados = db.session.query(func.count(Pedido.id))\
        .filter(Pedido.afiliado_id == afiliado.id, Pedido.validado_por_vendedor == True).scalar() or 0

    return render_template('afiliado/pedidos.html', 
                         pedidos=pedidos,
                         estado_filter=estado_filter,
                         total_pedidos=total_pedidos,
                         pedidos_pendientes=pedidos_pendientes,
                         pedidos_pagados=pedidos_pagados,
                         pedidos_validados=pedidos_validados)


@bp.route('/pedidos/<int:id>')
@afiliado_required
def ver_pedido(id):
    """Ver detalle de pedido del vendedor"""
    from models import Pedido

    afiliado = current_user
    pedido = Pedido.query.get_or_404(id)

    # Verificar que el pedido pertenece al vendedor
    if pedido.afiliado_id != afiliado.id:
        flash('No tienes permiso para ver este pedido', 'error')
        return redirect(url_for('afiliado.pedidos'))

    return render_template('afiliado/ver_pedido.html', pedido=pedido)


@bp.route('/pedidos/<int:id>/marcar-pagado', methods=['POST'])
@afiliado_required
def marcar_pedido_pagado(id):
    """Marcar pedido como pagado (vendedor)"""
    from models import Pedido

    afiliado = current_user
    pedido = Pedido.query.get_or_404(id)

    # Verificar que el pedido pertenece al vendedor
    if pedido.afiliado_id != afiliado.id:
        flash('No tienes permiso para modificar este pedido', 'error')
        return redirect(url_for('afiliado.pedidos'))

    if pedido.estado == 'pagado':
        flash('Este pedido ya está marcado como pagado', 'warning')
    else:
        pedido.marcar_como_pagado()
        flash(f'Pedido #{pedido.id} marcado como pagado', 'success')

    return redirect(url_for('afiliado.ver_pedido', id=id))


@bp.route('/pedidos/<int:id>/validar', methods=['POST'])
@afiliado_required
def validar_pedido(id):
    """Validar pedido para que el admin lo vea y se genere la comisión"""
    from models import Pedido

    afiliado = current_user
    pedido = Pedido.query.get_or_404(id)

    # Verificar que el pedido pertenece al vendedor
    if pedido.afiliado_id != afiliado.id:
        flash('No tienes permiso para validar este pedido', 'error')
        return redirect(url_for('afiliado.pedidos'))

    if pedido.validado_por_vendedor:
        flash('Este pedido ya está validado', 'warning')
    elif pedido.estado != 'pagado':
        flash('Debes marcar el pedido como pagado antes de validarlo', 'error')
    else:
        if pedido.validar_para_admin():
            flash(f'Pedido #{pedido.id} validado. El admin ahora puede verlo y se generó la comisión.', 'success')
        else:
            flash('Error al validar el pedido', 'error')

    return redirect(url_for('afiliado.ver_pedido', id=id))


@bp.route('/pedidos/<int:id>/cancelar', methods=['POST'])
@afiliado_required
def cancelar_pedido(id):
    """Cancelar pedido del vendedor"""
    from models import Pedido

    afiliado = current_user
    pedido = Pedido.query.get_or_404(id)

    # Verificar que el pedido pertenece al vendedor
    if pedido.afiliado_id != afiliado.id:
        flash('No tienes permiso para cancelar este pedido', 'error')
        return redirect(url_for('afiliado.pedidos'))

    if pedido.estado == 'cancelado':
        flash('Este pedido ya está cancelado', 'warning')
    elif pedido.estado == 'pagado' and pedido.validado_por_vendedor:
        flash('No se puede cancelar un pedido pagado y validado. Contacta al admin.', 'error')
    else:
        if pedido.marcar_como_cancelado():
            flash(f'Pedido #{pedido.id} cancelado exitosamente', 'success')
        else:
            flash('No se pudo cancelar el pedido', 'error')

    return redirect(url_for('afiliado.ver_pedido', id=id))


@bp.route('/mi-cuenta', methods=['GET', 'POST'])
@afiliado_required
def mi_cuenta():
    """El vendedor configura su perfil: WhatsApp, contraseña"""
    from models import Afiliado, db

    afiliado = current_user

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        whatsapp = request.form.get('whatsapp', '').strip()
        nueva_password = request.form.get('password', '')

        # [FASE 3 / E34 - ERRORES MEDIOS] Validar formato de WhatsApp
        
        if whatsapp and not validate_whatsapp(whatsapp):
            flash('El número de WhatsApp no parece ser válido. Ingresa al menos 9 dígitos.', 'error')
            return redirect(url_for('afiliado.mi_cuenta'))

        # Actualizar nombre si se proporciona
        if nombre:
            afiliado.nombre = nombre

        # Actualizar WhatsApp
        afiliado.whatsapp = whatsapp if whatsapp else None

        # [FASE 3 / E36 - ERRORES MEDIOS] Cambiar contraseña con validación de fortaleza
        if nueva_password:
            es_segura, mensaje = is_strong_password(nueva_password)
            if not es_segura:
                flash(mensaje, 'error')
                return redirect(url_for('afiliado.mi_cuenta'))
            afiliado.set_password(nueva_password)

        db.session.commit()
        flash('Tu perfil se actualizó correctamente.', 'success')
        return redirect(url_for('afiliado.mi_cuenta'))

    # Link de la tienda del vendedor
    link_tienda = url_for('tienda.tienda_vendedor', codigo=afiliado.codigo, _external=True)

    return render_template('afiliado/mi_cuenta.html',
                         afiliado=afiliado,
                         link_tienda=link_tienda)
