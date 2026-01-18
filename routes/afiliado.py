"""
Rutas del panel de afiliado
Ver productos con comisiones, ver comisiones ganadas
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from decimal import Decimal

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
    """Dashboard del afiliado"""
    from models import Comision, Pedido

    afiliado = current_user

    # Estadísticas
    total_pendiente = afiliado.total_comisiones_pendientes()
    total_generado = afiliado.total_comisiones_generadas()
    total_pagado = afiliado.total_comisiones_pagadas()
    total_ganado = afiliado.total_ganado()

    # Últimas comisiones
    ultimas_comisiones = Comision.query.filter_by(afiliado_id=afiliado.id)\
        .order_by(Comision.creado_en.desc()).limit(5).all()

    # Total de pedidos generados
    total_pedidos = Pedido.query.filter_by(afiliado_id=afiliado.id).count()

    return render_template('afiliado/dashboard.html',
                         afiliado=afiliado,
                         total_pendiente=total_pendiente,
                         total_generado=total_generado,
                         total_pagado=total_pagado,
                         total_ganado=total_ganado,
                         ultimas_comisiones=ultimas_comisiones,
                         total_pedidos=total_pedidos)


@bp.route('/productos')
@afiliado_required
def productos():
    """Ver productos con información de comisiones"""
    from models import Producto

    afiliado = current_user
    productos = Producto.query.filter_by(activo=True).all()

    # Agregar información de comisión a cada producto
    productos_con_comision = []
    for producto in productos:
        margen = producto.calcular_margen()
        comision = producto.calcular_comision_afiliado(afiliado.porcentaje_comision)

        productos_con_comision.append({
            'producto': producto,
            'margen': margen,
            'comision': comision,
            'link': url_for('tienda.producto_detalle', id=producto.id, ref=afiliado.codigo, _external=True)
        })

    return render_template('afiliado/productos.html',
                         productos=productos_con_comision,
                         afiliado=afiliado)


@bp.route('/comisiones')
@afiliado_required
def comisiones():
    """Ver todas las comisiones del afiliado"""
    from models import Comision

    afiliado = current_user

    # Filtro por estado
    estado_filter = request.args.get('estado', 'todos')

    query = Comision.query.filter_by(afiliado_id=afiliado.id)
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
    """Ver pedidos generados por el afiliado (sin datos personales del cliente)"""
    from models import Pedido

    afiliado = current_user

    pedidos = Pedido.query.filter_by(afiliado_id=afiliado.id)\
        .order_by(Pedido.creado_en.desc()).all()

    return render_template('afiliado/pedidos.html', pedidos=pedidos)
