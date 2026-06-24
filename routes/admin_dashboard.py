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

# ============== CONFIGURACIÓN WHITE-LABEL FASE 3 ==============

@bp.route('/configuracion', methods=['GET', 'POST'])
@admin_required
def configuracion():
    """Panel de configuración de marca blanca (Fase 3)"""
    config = Configuracion.query.first()
    
    if request.method == 'POST':
        if not config:
            config = Configuracion()
            db.session.add(config)
        
        # Identidad
        config.nombre_tienda = request.form.get('nombre_tienda', 'Mi Tienda Online')
        config.mensaje_bienvenida = request.form.get('mensaje_bienvenida')
        config.mensaje_footer = request.form.get('mensaje_footer')
        config.meta_descripcion = request.form.get('meta_descripcion')
        
        # Colores
        config.color_primario = request.form.get('color_primario', '#6366f1')
        config.color_secundario = request.form.get('color_secundario', '#22c55e')
        config.color_acento = request.form.get('color_acento', '#06b6d4')
        
        # Contacto
        config.whatsapp_contacto = request.form.get('whatsapp_contacto')

        # Manejo de archivos (Logo y Favicon)
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename and allowed_file(file.filename):
                if not validate_file_content(file):
                    flash('El archivo de logo no es una imagen válida (contenido sospechoso detectado).', 'error')
                else:
                    filename = secure_filename(f"logo_{int(time.time())}_{file.filename}")
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    config.logo_path = filename

        if 'favicon' in request.files:
            file = request.files['favicon']
            if file and file.filename and allowed_file(file.filename):
                if not validate_file_content(file):
                    flash('El archivo de favicon no es una imagen válida (contenido sospechoso detectado).', 'error')
                else:
                    filename = secure_filename(f"favicon_{int(time.time())}_{file.filename}")
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    config.favicon_path = filename

        try:
            db.session.commit()
            flash('Configuración actualizada correctamente ✨', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error actualizando configuración: {e}")
            flash('Error en la base de datos al guardar configuración.', 'error')
        return redirect(url_for('admin.configuracion'))

    return render_template('admin/configuracion.html', config=config)



@bp.route('/contabilidad')
@admin_required
def contabilidad():
    """Libro Diario y Balance General"""
    from utils.accounting import get_account_balance
    from models import Transaccion
    
    balance = get_account_balance()
    # Paginación simple para no saturar si hay miles de registros
    transacciones = Transaccion.query.order_by(Transaccion.creado_en.desc()).limit(200).all()
    
    return render_template('admin/contabilidad.html', 
                          balance=balance, 
                          transacciones=transacciones)

@bp.route('/dashboard')
@admin_required
def dashboard():
    """Dashboard principal del admin"""
    # Estadísticas generales
    total_productos = Producto.query.filter_by(activo=True).count()
    
    # Solo pedidos sin vendedor o validados por vendedores
    total_pedidos = Pedido.query.filter(
        db.or_(
            Pedido.afiliado_id.is_(None),
            Pedido.validado_por_vendedor == True
        )
    ).count()
    
    pedidos_pendientes = Pedido.query.filter(
        db.or_(
            db.and_(Pedido.afiliado_id.is_(None), Pedido.estado == 'pendiente'),
            db.and_(Pedido.validado_por_vendedor == True, Pedido.estado == 'pendiente')
        )
    ).count()
    
    pedidos_pagados = Pedido.query.filter(
        db.or_(
            db.and_(Pedido.afiliado_id.is_(None), Pedido.estado == 'pagado'),
            db.and_(Pedido.validado_por_vendedor == True, Pedido.estado == 'pagado')
        )
    ).count()
    
    total_afiliados = Afiliado.query.filter_by(activo=True).count()

    # Comisiones pendientes de pago
    comisiones_pendientes = db.session.query(db.func.sum(Comision.monto))\
        .filter(Comision.estado.in_(['pendiente', 'generada'])).scalar() or Decimal('0.00')

    # [OPTIMIZACIÓN E11 - FASE 4]
    # Uso de joinedload para traer el afiliado en la misma consulta y evitar N+1
    ultimos_pedidos = Pedido.query.options(joinedload(Pedido.afiliado)).filter(
        db.or_(
            Pedido.afiliado_id.is_(None),
            Pedido.validado_por_vendedor == True
        )
    ).order_by(Pedido.creado_en.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                         total_productos=total_productos,
                         total_pedidos=total_pedidos,
                         pedidos_pendientes=pedidos_pendientes,
                         pedidos_pagados=pedidos_pagados,
                         total_afiliados=total_afiliados,
                         comisiones_pendientes=comisiones_pendientes,
                         ultimos_pedidos=ultimos_pedidos)


