"""
Rutas del panel de administración
Gestión de productos, pedidos, afiliados y comisiones
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from sqlalchemy.orm import joinedload
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Admin, Producto, Pedido, Afiliado, Comision, Configuracion, Transaccion
from utils.accounting import register_transaction
from decimal import Decimal
import os
import time

bp = Blueprint('admin', __name__, url_prefix='/admin')

#PARA EVITAR PROBLEMAS DE ORDEN, ESTE BLOQUE admin_required DEBE ESTAR AL INICIO
#INICIA LOS CAMBIOS INDICADOS EN FASE 1
def admin_required(f):
    """
    Decorador de Seguridad: Verifica que el usuario esté autenticado y sea Administrador.
    Evita errores 500 al bloquear el acceso antes de ejecutar consultas a la DB.
    """
    @login_required
    def decorated_function(*args, **kwargs):
        # Si no hay usuario o no es de tipo Admin, denegar acceso inmediatamente
        if not current_user.is_authenticated or not isinstance(current_user, Admin):
            flash('Acceso denegado. Se requiere sesión de administrador.', 'error')
            return redirect('/auth/admin/login')
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

#FIN DE LOS CAMBIOS INDICADOS EN FASE 1


def allowed_file(filename):
    """Verificar si el archivo tiene extensión permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']



# SEGURIDAD (FASE 3 / HARDENING): Firmas binarias de archivos de imagen válidos
# Cada tipo de imagen tiene una secuencia de bytes única e imposible de falsificar al inicio del archivo.
ALLOWED_MIME_SIGNATURES = {
    b'\xff\xd8\xff': 'image/jpeg',       # JPEG / JPG
    b'\x89PNG\r\n\x1a\n': 'image/png',   # PNG
    b'GIF87a': 'image/gif',              # GIF87
    b'GIF89a': 'image/gif',              # GIF89
    b'RIFF': 'image/webp',               # WebP (verificación adicional abajo)
    b'\x00\x00\x01\x00': 'image/x-icon', # ICO (favicon)
}


def validate_file_content(file_storage):
    """
    Validación MIME real: Lee los primeros bytes del archivo para verificar
    que el contenido real corresponda a una imagen legítima, sin importar
    la extensión del nombre de archivo.
    Retorna True si el archivo es una imagen real, False si es un payload disfrazado.
    """
    header = file_storage.read(16)  # Leer los primeros 16 bytes (firma binaria)
    file_storage.seek(0)            # Rebobinar el archivo para que file.save() funcione después

    if not header:
        return False

    # Verificar contra cada firma conocida
    for signature, mime_type in ALLOWED_MIME_SIGNATURES.items():
        if header.startswith(signature):
            # Verificación extra para WebP: después de "RIFF" debe contener "WEBP"
            if signature == b'RIFF' and b'WEBP' not in header:
                continue
            return True

    return False

# Importar todas las subrutas modularizadas
from routes import admin_dashboard
from routes import admin_productos
from routes import admin_pedidos
from routes import admin_afiliados
from routes import admin_comisiones
from routes import admin_tickets

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
    total_afiliados = Afiliado.query.filter_by(activo=True).count()
    
    # FASE 3: Optimización - Consultas agrupadas para métricas (Reduce 3 roundtrips a PostgreSQL a 1)
    pedidos_stats = db.session.query(
        Pedido.estado,
        db.func.count(Pedido.id)
    ).filter(
        db.or_(
            Pedido.afiliado_id.is_(None),
            Pedido.validado_por_vendedor == True
        )
    ).group_by(Pedido.estado).all()
    
    total_pedidos = sum(count for _, count in pedidos_stats)
    pedidos_pendientes = next((count for estado, count in pedidos_stats if estado == 'pendiente'), 0)
    pedidos_pagados = next((count for estado, count in pedidos_stats if estado == 'pagado'), 0)

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


# ============== GESTIÓN DE PRODUCTOS ==============

@bp.route('/productos')
@admin_required
def productos():
    """Lista de productos con paginación (Mitiga E17)"""
    from models import Producto
    
    # Obtener número de página de la URL (default: 1)
    page = request.args.get('page', 1, type=int)
    per_page = 10 # Productos por página
    
    # [FASE 3 / E17 - ERRORES MEDIOS] Paginación de productos
    pagination = Producto.query.order_by(Producto.creado_en.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/productos.html', 
                         productos=pagination.items, 
                         pagination=pagination)


@bp.route('/productos/crear', methods=['GET', 'POST'])
@admin_required
def crear_producto():
    """Crear nuevo producto"""
    from models import Producto
    from app import db

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        categoria = request.form.get('categoria', 'otros')
        precio_final = request.form.get('precio_final')
        precio_proveedor = request.form.get('precio_proveedor')
        precio_oferta = request.form.get('precio_oferta')
        stock = request.form.get('stock', 0)
        activo = request.form.get('activo') == 'on'

        # Validaciones
        if not nombre or not precio_final or not precio_proveedor or not categoria:
            flash('Nombre, categoria, precio final y precio proveedor son obligatorios', 'error')
            return render_template('admin/crear_producto.html')

        try:
            precio_final = Decimal(precio_final)
            precio_proveedor = Decimal(precio_proveedor)
            precio_oferta = Decimal(precio_oferta) if precio_oferta else None
            stock = int(stock) if stock else 0

            # Validar que precio final > precio proveedor
            if precio_final <= precio_proveedor:
                flash('El precio final debe ser mayor al precio proveedor', 'error')
                return render_template('admin/crear_producto.html')

            # Validar precio oferta si existe
            if precio_oferta and precio_oferta < precio_proveedor:
                flash('El precio de oferta debe ser mayor o igual al precio proveedor', 'error')
                return render_template('admin/crear_producto.html')

        except (ValueError, Exception) as e:
            current_app.logger.error(f"Error al procesar datos numéricos del producto: {e}")
            flash('Los precios y el stock deben ser números válidos', 'error')
            return render_template('admin/crear_producto.html')

        # Manejar imágenes - Priorizar URLs sobre archivos locales
        imagen_principal = None
        imagenes_adicionales = []
        imagen_url = None
        imagenes_url = []

        # Primero verificar si hay URLs de imágenes
        imagen_url = request.form.get('imagen_url', '').strip()
        imagen_url_2 = request.form.get('imagen_url_2', '').strip()
        imagen_url_3 = request.form.get('imagen_url_3', '').strip()
        imagen_url_4 = request.form.get('imagen_url_4', '').strip()

        # Recolectar URLs adicionales
        for url in [imagen_url_2, imagen_url_3, imagen_url_4]:
            if url:
                imagenes_url.append(url)

        # Si no hay URL principal, verificar archivos locales
        if not imagen_url:
            import time
            if 'imagenes' in request.files:
                files = request.files.getlist('imagenes')
                for i, file in enumerate(files[:4]):  # Máximo 4 imágenes
                    if file and file.filename:
                        if allowed_file(file.filename):
                            filename = secure_filename(file.filename)
                            filename = f"{int(time.time())}_{i}_{filename}"
                            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

                            if i == 0:
                                imagen_principal = filename
                            else:
                                imagenes_adicionales.append(filename)
                        else:
                            current_app.logger.warning(f"Intento de subida de archivo no permitido: {file.filename}")
                            flash(f'Archivo "{file.filename}" no permitido (solo jpg, png, webp)', 'error')

        # Crear producto
        producto = Producto(
            nombre=nombre,
            descripcion=descripcion,
            categoria=categoria,
            precio_final=precio_final,
            precio_proveedor=precio_proveedor,
            precio_oferta=precio_oferta,
            imagen=imagen_principal if not imagen_url else None,
            imagenes=imagenes_adicionales if imagenes_adicionales and not imagen_url else None,
            imagen_url=imagen_url if imagen_url else None,
            imagenes_url=imagenes_url if imagenes_url else None,
            stock=stock,
            activo=activo
        )

        db.session.add(producto)
        db.session.commit()

        flash(f'Producto "{nombre}" creado exitosamente', 'success')
        return redirect(url_for('admin.productos'))

    return render_template('admin/crear_producto.html')


@bp.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_producto(id):
    """Editar producto existente"""
    from models import Producto
    from app import db

    producto = Producto.query.get_or_404(id)

    if request.method == 'POST':
        producto.nombre = request.form.get('nombre')
        producto.descripcion = request.form.get('descripcion')
        producto.categoria = request.form.get('categoria', 'otros')

        try:
            producto.precio_final = Decimal(request.form.get('precio_final'))
            producto.precio_proveedor = Decimal(request.form.get('precio_proveedor'))
            precio_oferta = request.form.get('precio_oferta')
            producto.precio_oferta = Decimal(precio_oferta) if precio_oferta else None
            
            stock = request.form.get('stock')
            producto.stock = int(stock) if stock else 0

            # Validaciones
            if producto.precio_final <= producto.precio_proveedor:
                flash('El precio final debe ser mayor al precio proveedor', 'error')
                return render_template('admin/editar_producto.html', producto=producto)

            if producto.precio_oferta and producto.precio_oferta < producto.precio_proveedor:
                flash('El precio de oferta debe ser mayor o igual al precio proveedor', 'error')
                return render_template('admin/editar_producto.html', producto=producto)

        except (ValueError, Exception) as e:
            current_app.logger.error(f"Error al procesar datos numéricos en edición de producto ID {id}: {e}")
            flash('Los precios y el stock deben ser números válidos', 'error')
            return render_template('admin/editar_producto.html', producto=producto)

        producto.activo = request.form.get('activo') == 'on'

        # Manejar imágenes - Priorizar URLs sobre archivos locales
        imagen_url = request.form.get('imagen_url', '').strip()
        imagen_url_2 = request.form.get('imagen_url_2', '').strip()
        imagen_url_3 = request.form.get('imagen_url_3', '').strip()
        imagen_url_4 = request.form.get('imagen_url_4', '').strip()

        # Si hay URL principal, usar URLs
        if imagen_url:
            producto.imagen_url = imagen_url
            imagenes_url = []
            for url in [imagen_url_2, imagen_url_3, imagen_url_4]:
                if url:
                    imagenes_url.append(url)
            producto.imagenes_url = imagenes_url if imagenes_url else None
            # Limpiar imágenes locales si se usan URLs
            producto.imagen = None
            producto.imagenes = None
        else:
            # Si no hay URLs, verificar archivos locales
            if 'imagenes' in request.files:
                files = request.files.getlist('imagenes')
                archivos_validos = [f for f in files if f and f.filename and allowed_file(f.filename)]

                if archivos_validos:
                    import time
                    imagen_principal = None
                    imagenes_adicionales = []

                    for i, file in enumerate(archivos_validos[:4]):
                        filename = secure_filename(file.filename)
                        filename = f"{int(time.time())}_{i}_{filename}"
                        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))

                        if i == 0:
                            imagen_principal = filename
                        else:
                            imagenes_adicionales.append(filename)

                    producto.imagen = imagen_principal
                    producto.imagenes = imagenes_adicionales if imagenes_adicionales else None
                    # Limpiar URLs si se suben archivos
                    producto.imagen_url = None
                    producto.imagenes_url = None

        db.session.commit()
        flash(f'Producto "{producto.nombre}" actualizado exitosamente', 'success')
        return redirect(url_for('admin.productos'))

    return render_template('admin/editar_producto.html', producto=producto)


@bp.route('/productos/eliminar/<int:id>', methods=['POST'])
@admin_required
def eliminar_producto(id):
    """Desactivar producto"""
    from models import Producto
    from app import db

    producto = Producto.query.get_or_404(id)
    producto.activo = False
    db.session.commit()
    flash(f'Producto "{producto.nombre}" desactivado', 'success')
    return redirect(url_for('admin.productos'))


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

        db.session.add(afiliado)
        db.session.commit()

        flash(f'Afiliado "{nombre}" creado exitosamente con código {codigo}', 'success')
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

        db.session.commit()
        flash(f'Afiliado "{afiliado.nombre}" actualizado exitosamente', 'success')
        return redirect(url_for('admin.afiliados'))

    return render_template('admin/editar_afiliado.html', afiliado=afiliado)


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

    db.session.commit()

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
    ticket.estado = 'cerrado'
    db.session.commit()
    flash(f'Ticket {ticket.numero} marcado como resuelto.', 'success')
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
