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

# ============== GESTIÓN DE COMISIONES ==============

@bp.route('/comisiones')
@admin_required
def comisiones():
    """Lista de comisiones"""
    from models import Comision
    from app import db

    estado_filter = request.args.get('estado', 'todos')

    query = Comision.query
    if estado_filter != 'todos':
        query = query.filter_by(estado=estado_filter)

    # [OPTIMIZACIÓN E11 - FASE 4]
    # Se cargan de forma optimizada las relaciones 'pedido' y 'afiliado' para evitar ciclo de consultas N+1
    comisiones = query.options(
        joinedload(Comision.pedido), 
        joinedload(Comision.afiliado)
    ).order_by(Comision.creado_en.desc()).all()

    # Totales
    total_generadas = db.session.query(db.func.sum(Comision.monto))\
        .filter(Comision.estado == 'generada').scalar() or Decimal('0.00')
    total_pagadas = db.session.query(db.func.sum(Comision.monto))\
        .filter(Comision.estado == 'pagada').scalar() or Decimal('0.00')

    return render_template('admin/comisiones.html',
                         comisiones=comisiones,
                         estado_filter=estado_filter,
                         total_generadas=total_generadas,
                         total_pagadas=total_pagadas)


@bp.route('/comisiones/<int:id>/marcar-pagada', methods=['POST'])
@admin_required
def marcar_comision_pagada(id):
    """Marcar comisión como pagada"""
    from models import Comision

    comision = Comision.query.get_or_404(id)

    if comision.estado == 'pagada':
        flash('Esta comisión ya está marcada como pagada', 'warning')
    else:
        comision.marcar_como_pagada()
        flash(f'Comisión #{comision.id} marcada como pagada', 'success')

    return redirect(url_for('admin.comisiones'))


@bp.route('/afiliados/<int:id>/pagar-comisiones', methods=['POST'])
@admin_required
def pagar_comisiones_afiliado(id):
    """Pagar todas las comisiones generadas de un afiliado"""
    from models import Afiliado, Comision
    from datetime import datetime

    afiliado = Afiliado.query.get_or_404(id)

    # Obtener todas las comisiones generadas (no pagadas) del afiliado
    comisiones = Comision.query.filter_by(
        afiliado_id=afiliado.id,
        estado='generada'
    ).all()

    if not comisiones:
        flash(f'El afiliado {afiliado.nombre} no tiene comisiones pendientes de pago', 'warning')
        return redirect(url_for('admin.afiliados'))

    # Calcular total a pagar
    total_a_pagar = sum(c.monto for c in comisiones)
    num_comisiones = len(comisiones)

    # Marcar todas como pagadas
    for comision in comisiones:
        comision.estado = 'pagada'
        comision.pagada_en = datetime.utcnow()

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error marcando comisiones como pagadas: {e}")
        flash('Error en la base de datos al procesar el pago de comisiones.', 'error')
        return redirect(url_for('admin.afiliados'))

    # --- SINCRONIZACIÓN CONTABLE ---
    register_transaction(
        tipo='gasto',
        monto=float(total_a_pagar),
        categoria='comision',
        fuente='caja',
        descripcion=f"Pago comisiones - Vendedor: {afiliado.nombre}",
        referencia_id=f"COM-{afiliado.id}-{int(time.time())}"
    )

    flash(f'✓ Pagadas {num_comisiones} comisiones a {afiliado.nombre} por un total de ${float(total_a_pagar):.2f}', 'success')
    return redirect(url_for('admin.afiliados'))

