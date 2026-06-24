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

# ============== GESTIÓN DE AFILIADOS ==============

@bp.route('/afiliados')
@admin_required
def afiliados():
    """Lista de afiliados"""
    from models import Afiliado, Comision, Pedido
    from sqlalchemy import func

    afiliados_data = []
    
    # 1. OPTIMIZACIÓN N+1: Agrupar comisiones (pagadas y generadas) en una sola consulta
    comisiones_stats = db.session.query(
        Comision.afiliado_id,
        Comision.estado,
        func.sum(Comision.monto).label('total')
    ).group_by(Comision.afiliado_id, Comision.estado).all()
    
    # Diccionario rápido para mapear comisiones: { afiliado_id: {'pagada': X, 'generada': Y} }
    stats_dict = {}
    for af_id, estado, total in comisiones_stats:
        if af_id not in stats_dict:
            stats_dict[af_id] = {'pagada': 0, 'generada': 0}
        stats_dict[af_id][estado] = total or 0

    # 2. OPTIMIZACIÓN N+1: Contar todos los pedidos pagados agrupados por afiliado en una sola consulta
    ventas_stats = db.session.query(
        Pedido.afiliado_id,
        func.count(Pedido.id).label('num_ventas')
    ).filter(Pedido.estado == 'pagado').group_by(Pedido.afiliado_id).all()

    ventas_dict = {af_id: count for af_id, count in ventas_stats}

    # 3. Obtener afiliados y mapear (Solo 3 consultas en total para toda la tabla)
    afiliados = Afiliado.query.order_by(Afiliado.creado_en.desc()).all()

    for afiliado in afiliados:
        af_stats = stats_dict.get(afiliado.id, {})
        total_ganado = af_stats.get('pagada', 0)
        total_generado = af_stats.get('generada', 0)
        num_ventas = ventas_dict.get(afiliado.id, 0)
        
        afiliados_data.append({
            'afiliado': afiliado,
            'total_ganado': float(total_ganado),
            'total_pendiente': float(total_generado),
            'num_ventas': num_ventas
        })

    return render_template('admin/afiliados.html', afiliados_data=afiliados_data)


@bp.route('/afiliados/crear', methods=['GET', 'POST'])
@admin_required
def crear_afiliado():
    """Crear nuevo afiliado"""
    from models import Afiliado
    from app import db

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        codigo = request.form.get('codigo').upper()
        porcentaje = request.form.get('porcentaje_comision')
        password = request.form.get('password')
        whatsapp = request.form.get('whatsapp', '').strip()
        activo = request.form.get('activo') == 'on'

        # Validaciones
        if not all([nombre, email, codigo, porcentaje, password]):
            flash('Nombre, email, código, porcentaje y contraseña son obligatorios', 'error')
            return render_template('admin/crear_afiliado.html')

        # Verificar email único
        if Afiliado.query.filter_by(email=email).first():
            flash('Este email ya está registrado', 'error')
            return render_template('admin/crear_afiliado.html')

        # Verificar código único
        if Afiliado.query.filter_by(codigo=codigo).first():
            flash('Este código ya está en uso', 'error')
            return render_template('admin/crear_afiliado.html')

        try:
            porcentaje = Decimal(porcentaje)
            if porcentaje < 0 or porcentaje > 100:
                raise ValueError
        except:
            flash('El porcentaje debe ser un número entre 0 y 100', 'error')
            return render_template('admin/crear_afiliado.html')

        # Crear afiliado (vendedor)
        afiliado = Afiliado(
            nombre=nombre,
            email=email,
            codigo=codigo,
            porcentaje_comision=porcentaje,
            whatsapp=whatsapp if whatsapp else None,
            activo=activo
        )
        afiliado.set_password(password)

        try:
            db.session.add(afiliado)
            db.session.commit()
            flash(f'Afiliado "{nombre}" creado exitosamente con código {codigo}', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creando afiliado: {e}")
            flash('Error en la base de datos al guardar el afiliado.', 'error')
        return redirect(url_for('admin.afiliados'))

    return render_template('admin/crear_afiliado.html')


@bp.route('/afiliados/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_afiliado(id):
    """Editar afiliado existente"""
    from models import Afiliado
    from app import db

    afiliado = Afiliado.query.get_or_404(id)

    if request.method == 'POST':
        afiliado.nombre = request.form.get('nombre')
        email = request.form.get('email')
        whatsapp = request.form.get('whatsapp', '').strip()

        # Verificar email único
        email_existente = Afiliado.query.filter_by(email=email).first()
        if email_existente and email_existente.id != afiliado.id:
            flash('Este email ya está registrado', 'error')
            return render_template('admin/editar_afiliado.html', afiliado=afiliado)

        afiliado.email = email
        afiliado.whatsapp = whatsapp if whatsapp else None

        try:
            porcentaje = Decimal(request.form.get('porcentaje_comision'))
            if porcentaje < 0 or porcentaje > 100:
                raise ValueError
            afiliado.porcentaje_comision = porcentaje
        except:
            flash('El porcentaje debe ser un número entre 0 y 100', 'error')
            return render_template('admin/editar_afiliado.html', afiliado=afiliado)

        # Cambiar contraseña solo si se proporciona
        nueva_password = request.form.get('password')
        if nueva_password:
            afiliado.set_password(nueva_password)

        afiliado.activo = request.form.get('activo') == 'on'

        try:
            db.session.commit()
            flash(f'Afiliado "{afiliado.nombre}" actualizado exitosamente', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error actualizando afiliado: {e}")
            flash('Error en la base de datos al actualizar el afiliado.', 'error')
        return redirect(url_for('admin.afiliados'))

    return render_template('admin/editar_afiliado.html', afiliado=afiliado)


