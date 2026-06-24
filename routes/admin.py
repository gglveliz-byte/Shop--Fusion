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
