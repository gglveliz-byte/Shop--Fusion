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
                            if not validate_file_content(file):
                                current_app.logger.warning(f"SEGURIDAD: Archivo disfrazado detectado: {file.filename}")
                                flash(f'Archivo "{file.filename}" rechazado: el contenido no corresponde a una imagen real.', 'error')
                                continue
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

        try:
            db.session.add(producto)
            db.session.commit()
            flash(f'Producto "{nombre}" creado exitosamente', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creando producto: {e}")
            flash('Error en la base de datos al guardar el producto.', 'error')
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
                        if not validate_file_content(file):
                            current_app.logger.warning(f"SEGURIDAD: Archivo disfrazado detectado en edición: {file.filename}")
                            flash(f'Archivo "{file.filename}" rechazado: el contenido no corresponde a una imagen real.', 'error')
                            continue
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

        try:
            db.session.commit()
            flash(f'Producto "{producto.nombre}" actualizado exitosamente', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error actualizando producto: {e}")
            flash('Error en la base de datos al actualizar el producto.', 'error')
        return redirect(url_for('admin.productos'))

    return render_template('admin/editar_producto.html', producto=producto)


@bp.route('/productos/eliminar/<int:id>', methods=['POST'])
@admin_required
def eliminar_producto(id):
    """Desactivar producto"""
    from models import Producto
    from app import db

    producto = Producto.query.get_or_404(id)
    try:
        producto.activo = False
        db.session.commit()
        flash(f'Producto "{producto.nombre}" desactivado', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error desactivando producto: {e}")
        flash('Error al desactivar el producto.', 'error')
    return redirect(url_for('admin.productos'))


