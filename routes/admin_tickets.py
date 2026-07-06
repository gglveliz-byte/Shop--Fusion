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

# ============== GESTIÓN DE TICKETS DE SOPORTE ==============

@bp.route('/tickets')
@admin_required
def tickets():
    """Lista de tickets de soporte con filtros (Fase 6)"""
    from models import TicketSoporte
    
    estado_filter = request.args.get('estado', 'todos')
    prioridad_filter = request.args.get('prioridad', 'todas')
    
    query = TicketSoporte.query
    
    if estado_filter != 'todos':
        query = query.filter_by(estado=estado_filter)
        
    if prioridad_filter != 'todas':
        query = query.filter_by(prioridad=prioridad_filter)
        
    tickets = query.order_by(
        TicketSoporte.escalado.desc(), # Primero los escalados
        TicketSoporte.actualizado_en.desc()
    ).all()
    
    return render_template('admin/tickets.html', 
                         tickets=tickets,
                         estado_filter=estado_filter,
                         prioridad_filter=prioridad_filter)

@bp.route('/tickets/<int:id>/resolver', methods=['POST'])
@admin_required
def ticket_resolver(id):
    """Marca un ticket como cerrado/resuelto."""
    from models import TicketSoporte
    from app import db
    ticket = TicketSoporte.query.get_or_404(id)
    try:
        ticket.estado = 'cerrado'
        db.session.commit()
        flash(f'Ticket {ticket.numero} marcado como resuelto.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cerrando ticket: {e}")
        flash('Error al marcar el ticket como resuelto.', 'error')
    return redirect(url_for('admin.tickets'))

@bp.route('/tickets/<int:id>/escalar', methods=['POST'])
@admin_required
def ticket_escalar(id):
    """Escala un ticket manualmente desde el admin."""
    from utils.support import escalate_ticket
    res = escalate_ticket(id)
    if res.get('success'):
        flash('Ticket escalado correctamente y equipo notificado.', 'success')
    else:
        flash(f"Error al escalar: {res.get('error')}", 'error')
    return redirect(url_for('admin.tickets'))

@bp.route('/tickets/<int:id>', methods=['GET', 'POST'])
@admin_required
def ver_ticket(id):
    """Ver detalles del ticket y añadir comentarios."""
    from models import TicketSoporte
    from utils.support import add_comment
    
    ticket = TicketSoporte.query.get_or_404(id)
    
    if request.method == 'POST':
        comentario_texto = request.form.get('comentario')
        if comentario_texto:
            res = add_comment(ticket.id, comentario_texto, author='admin')
            if res.get('success'):
                flash('Comentario añadido.', 'success')
            else:
                flash(f"Error al añadir comentario: {res.get('error')}", 'error')
        return redirect(url_for('admin.ver_ticket', id=id))
        
    return render_template('admin/ver_ticket.html', ticket=ticket)
