from flask import render_template, request, redirect, url_for, flash, current_app, session
from decimal import Decimal
import os
import time
from models import db, Admin, Producto, Pedido, Afiliado, Comision, Configuracion, Transaccion, TicketSoporte
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from utils.accounting import register_transaction, get_account_balance
from utils.support import escalate_ticket, add_comment
from werkzeug.utils import secure_filename
from routes.admin import bp, admin_required, allowed_file, validate_file_content

# ============== GESTIÓN DE PEDIDOS ==============

@bp.route('/pedidos')
@admin_required
def pedidos():
    """Lista de pedidos - Solo pedidos validados por vendedores o sin vendedor (tienda principal)"""
    from models import Pedido

    estado_filter = request.args.get('estado', 'todos')
    tipo_filter = request.args.get('tipo', 'todos')  # todos, validados, sin_vendedor

    # Pedidos sin vendedor (tienda principal) O pedidos validados por vendedores
    query = Pedido.query.filter(
        db.or_(
            Pedido.afiliado_id.is_(None),  # Sin vendedor (tienda principal)
            Pedido.validado_por_vendedor == True  # Validados por vendedores
        )
    )

    if estado_filter != 'todos':
        query = query.filter_by(estado=estado_filter)

    if tipo_filter == 'validados':
        query = query.filter(Pedido.validado_por_vendedor == True)
    elif tipo_filter == 'sin_vendedor':
        query = query.filter(Pedido.afiliado_id.is_(None))

    # [OPTIMIZACIÓN E11 - FASE 4]
    # Se inyecta joinedload(Pedido.afiliado) para mitigar el error crítico E11 sobre desempeño nocivo
    pedidos = query.options(joinedload(Pedido.afiliado)).order_by(Pedido.creado_en.desc()).all()
    
    # Estadísticas
    total_validados = Pedido.query.filter_by(validado_por_vendedor=True).count()
    total_sin_vendedor = Pedido.query.filter_by(afiliado_id=None).count()
    
    return render_template('admin/pedidos.html', 
                         pedidos=pedidos, 
                         estado_filter=estado_filter,
                         tipo_filter=tipo_filter,
                         total_validados=total_validados,
                         total_sin_vendedor=total_sin_vendedor)


@bp.route('/pedidos/<int:id>')
@admin_required
def ver_pedido(id):
    """Ver detalle de pedido"""
    from models import Pedido

    pedido = Pedido.query.get_or_404(id)
    return render_template('admin/ver_pedido.html', pedido=pedido)


@bp.route('/pedidos/<int:id>/marcar-pagado', methods=['POST'])
@admin_required
def marcar_pedido_pagado(id):
    """Marcar pedido como pagado (solo para pedidos sin vendedor - tienda principal)"""
    from models import Pedido

    pedido = Pedido.query.get_or_404(id)

    # Solo puede marcar como pagado si no tiene vendedor (tienda principal)
    if pedido.afiliado_id:
        flash('Este pedido pertenece a un vendedor. El vendedor debe marcarlo como pagado y validarlo.', 'error')
        return redirect(url_for('admin.ver_pedido', id=id))

    if pedido.estado == 'pagado':
        flash('Este pedido ya está marcado como pagado', 'warning')
    else:
        pedido.marcar_como_pagado()
        
        # --- SINCRONIZACIÓN CONTABLE ---
        register_transaction(
            tipo='ingreso',
            monto=float(pedido.total),
            categoria='venta',
            fuente='caja',
            descripcion=f"Cobro manual - Pedido #{pedido.id}",
            referencia_id=f"PED-{pedido.id}"
        )
        
        # Para pedidos sin vendedor, no hay comisión que generar
        flash(f"Pedido #{pedido.id} marcado como pagado y registrado en contabilidad.", "success")

    return redirect(url_for('admin.ver_pedido', id=id))


@bp.route('/pedidos/<int:id>/cancelar', methods=['POST'])
@admin_required
def cancelar_pedido(id):
    """Cancelar pedido"""
    from models import Pedido

    pedido = Pedido.query.get_or_404(id)

    if pedido.estado == 'cancelado':
        flash('Este pedido ya está cancelado', 'warning')
    elif pedido.estado == 'pagado' and pedido.validado_por_vendedor:
        flash('No se puede cancelar un pedido pagado y validado. Contacta al vendedor.', 'error')
    else:
        if pedido.marcar_como_cancelado():
            flash(f'Pedido #{pedido.id} cancelado exitosamente', 'success')
        else:
            flash('No se pudo cancelar el pedido', 'error')

    return redirect(url_for('admin.ver_pedido', id=id))


