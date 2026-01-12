import os
import re
import time
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from flask_wtf import FlaskForm, CSRFProtect
from flask_wtf.csrf import CSRFError
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, IntegerField, FloatField
from wtforms.validators import DataRequired, Email, Length, NumberRange
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
import sys
import psycopg
from psycopg.rows import dict_row
from psycopg import sql
from decouple import config
from urllib.parse import urlparse
import json
from decimal import Decimal, ROUND_HALF_UP
try:
    import openai
except Exception:
    openai = None
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from services_exclusivos import (
    obtener_productos_exclusivos,          # parte pública
    obtener_productos_exclusivos_admin,    # admin
    obtener_producto_exclusivo_por_id,     # admin
    actualizar_producto_exclusivo,         # admin
    registrar_compra_exclusivo,
    ensure_compras_envio_columns,
    crear_producto_exclusivo,            # registrar compra + stock
)
from services_afiliados import (
    obtener_comision_afiliado,
    crear_afiliado,
    obtener_afiliado_por_email,
    obtener_afiliado_por_codigo,
    obtener_afiliado_cliente,
    asignar_afiliado_a_cliente,
    registrar_comision,
    registrar_click_afiliado,
    obtener_estadisticas_afiliado,
    obtener_descuento_disponible_afiliado,
    aplicar_descuento_afiliado,
)
from services_afiliados_pagos import (
    AFILIADOS_PAGO_FIELDS,
    afiliados_pago_columns_exist,
    afiliados_pagos_table_exists,
)
from services_categorias import (
    obtener_categorias,
    obtener_categoria_por_id,
    crear_categoria,
    actualizar_categoria,
    eliminar_categoria,
    obtener_categorias_como_lista,
)
from services_auth import (
    crear_sesion,
    validar_sesion,
    cerrar_sesion,
    cerrar_todas_sesiones_usuario,
    limpiar_sesiones_expiradas,
)
from services_carrito import (
    obtener_carrito_usuario,
    agregar_al_carrito_usuario,
    actualizar_cantidad_carrito_usuario,
    eliminar_del_carrito_usuario,
    limpiar_carrito_usuario,
    calcular_total_carrito_visitante,
    validar_limite_visitante,
    migrar_carrito_cookies_a_bd,
    obtener_carrito_afiliado,
    agregar_al_carrito_afiliado,
    actualizar_cantidad_carrito_afiliado,
    eliminar_del_carrito_afiliado,
    limpiar_carrito_afiliado,
    migrar_carrito_cookies_a_bd_afiliado,
)






app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)
# Friendly stdout handler with timestamp (useful under gunicorn / render)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
if not any(isinstance(h, logging.StreamHandler) for h in app.logger.handlers):
    app.logger.addHandler(handler)

app.config['SECRET_KEY'] = config('SECRET_KEY')
# CRÍTICO: Configurar CSRF sin límite de tiempo para evitar problemas con sesiones
app.config['WTF_CSRF_TIME_LIMIT'] = None  # Sin límite de tiempo
app.config['SESSION_COOKIE_SECURE'] = False  # Se ajusta a True en produccion
app.config['SESSION_COOKIE_HTTPONLY'] = True
# SameSite=None requiere Secure=True, pero en desarrollo usamos Lax
# Si hay problemas, cambiar a None y Secure=True (solo con HTTPS)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Lax permite cookies en navegación cross-site y evita bloqueo de tracking prevention
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 horas
# Asegurar que las cookies de sesión se envíen correctamente
app.config['SESSION_COOKIE_NAME'] = 'shopfusion_session'  # Nombre más específico para evitar conflictos
app.config['SESSION_COOKIE_DOMAIN'] = None  # Permitir cualquier dominio en desarrollo
app.config['SESSION_COOKIE_PATH'] = '/'  # Asegurar que las cookies se envíen en todas las rutas

# Referidos afiliados: 15 dias en cookie
AFILIADO_REF_COOKIE = 'ref_afiliado'
AFILIADO_REF_MAX_AGE = 15 * 24 * 60 * 60

# Configuración CSRF - Permite JSON con header X-CSRFToken
app.config['WTF_CSRF_CHECK_DEFAULT'] = True
app.config['WTF_CSRF_HEADERS'] = ['X-CSRFToken', 'X-CSRF-Token']
# Asegurar que CSRF use sesiones correctamente
app.config['WTF_CSRF_ENABLED'] = True

# Protección CSRF global
csrf = CSRFProtect(app)

# ============================================================================
# CONFIGURACIÓN DE SEGURIDAD
# ============================================================================

# Rate Limiting - Protección contra fuerza bruta y abuso
RATELIMIT_STORAGE_URI = config('RATELIMIT_STORAGE_URI', default='memory://')
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri=RATELIMIT_STORAGE_URI,  # En producción, usar Redis: "redis://localhost:6379"
    headers_enabled=True
)

# Headers de Seguridad HTTP (Talisman)
# Solo forzar HTTPS en producción
is_production = config('ENVIRONMENT', default='development') == 'production'
app.config['SESSION_COOKIE_SECURE'] = is_production
ENABLE_DB_ADMIN = str(config('ENABLE_DB_ADMIN', default='false')).lower() in ('1', 'true', 'yes')
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
ENABLE_OPENAI = bool(OPENAI_API_KEY) and openai is not None
if is_production and RATELIMIT_STORAGE_URI == 'memory://':
    app.logger.warning('[CONFIG] RATELIMIT_STORAGE_URI usa memory:// en produccion; configura Redis')

# En desarrollo, deshabilitar Talisman temporalmente para evitar problemas con cookies
# En producción, habilitar con configuración completa
if is_production:
    csp_connect = "'self' https://api.sandbox.paypal.com https://api.paypal.com https://www.paypal.com"
    if ENABLE_OPENAI:
        csp_connect += " https://api.openai.com"
    Talisman(
        app,
        force_https=True,
        force_https_permanent=True,
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,  # 1 año
        content_security_policy={
            'default-src': "'self'",
            'script-src': "'self' 'unsafe-inline' https://www.paypal.com https://www.paypalobjects.com https://cdnjs.cloudflare.com",
            'style-src': "'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com",
            'style-src-elem': "'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com",
            'img-src': "'self' data: https: http:",
            'font-src': "'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com",
            'connect-src': csp_connect,
            'frame-src': "'self' https://www.paypal.com",
        },
        content_security_policy_nonce_in=[],
        referrer_policy='strict-origin-when-cross-origin'
    )
    # Aplicar ProxyFix cuando el app está detrás de un proxy (ej. Render, Heroku, Nginx)
    try:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
        app.logger.info('[CONFIG] ProxyFix aplicado (x_for=1, x_proto=1)')
    except Exception as e:
        app.logger.warning(f'[CONFIG] No se pudo aplicar ProxyFix: {e}')
else:
    # En desarrollo, no usar Talisman para evitar problemas con cookies de sesión
    app.logger.warning('[CONFIG] Talisman deshabilitado en desarrollo para evitar problemas con cookies')

if ENABLE_OPENAI:
    openai.api_key = OPENAI_API_KEY
openai_client = openai if ENABLE_OPENAI else None

# Middleware de autenticación basado en tokens BD
@app.before_request
def validate_auth_token():
    """Valida el token de autenticación desde BD en cada request"""
    # Rutas que no requieren autenticación
    rutas_publicas_exact = {
        '/login', '/registro', '/', '/contacto', '/privacidad',
        '/terminos', '/soporte', '/proveedores', '/trabaja-con-nosotros',
        '/exclusivos', '/catalogo', '/buscar', '/buscar_inteligente',
        '/api/carrito/contador', '/favicon.ico'
    }
    rutas_publicas_prefix = ['/static/']
    
    # Si es ruta pública, solo limpiar sesiones expiradas periódicamente
    if request.path in rutas_publicas_exact or any(request.path.startswith(ruta) for ruta in rutas_publicas_prefix):
        # Limpiar sesiones expiradas cada 100 requests (aproximadamente)
        import random
        if random.randint(1, 100) == 1:
            limpiar_sesiones_expiradas()
        return
    
    # Obtener token del header o cookie
    token = request.headers.get('X-Auth-Token') or request.cookies.get('auth_token')
    
    if token:
        # Validar token en BD
        usuario_info = validar_sesion(token, request.remote_addr)
        if usuario_info:
            # Guardar info del usuario en g (contexto de Flask)
            from flask import g
            g.current_user = usuario_info
            g.auth_token = token
            # También mantener en session para compatibilidad temporal
            session['usuario_id'] = usuario_info['usuario_id']
            session['nombre'] = usuario_info['nombre']
            session['email'] = usuario_info['email']
            session['rol'] = usuario_info['rol']
            
            # CRÍTICO: Si el usuario está autenticado, limpiar cualquier carrito de cookies
            # Los usuarios registrados SIEMPRE usan BD, nunca cookies
            if 'carrito' in session and usuario_info.get('rol') == 'cliente':
                # Si hay carrito en cookies y no está en BD, migrarlo
                carrito_cookies = session.get('carrito', [])
                if carrito_cookies:
                    migrar_carrito_cookies_a_bd(usuario_info['usuario_id'], carrito_cookies)
                # Limpiar carrito de cookies
                session.pop('carrito', None)
                session.modified = True
        else:
            # Token inválido o expirado
            g.current_user = None
            g.auth_token = None
            session.clear()
    else:
        # No hay token, usuario visitante
        from flask import g
        g.current_user = None
        g.auth_token = None
        if str(session.get('rol', '')).lower() == 'cliente':
            session.clear()
    
    # Mantener compatibilidad con CSRF - inicializar sesión mínima
    if '_session_init' not in session:
        session['_session_init'] = True
        session.modified = True

@app.after_request
def save_session(response):
    """Asegurar que la sesión se guarde después de cada request"""
    # CRÍTICO: Forzar que la sesión se guarde en la cookie
    # Esto es necesario para que CSRF funcione correctamente
    session.permanent = True
    # SIEMPRE marcar como modificada para forzar guardado
    # Esto asegura que la cookie se envíe al navegador incluso si la sesión parece vacía
    if session:
        session.modified = True
        
        # Forzar guardado accediendo a la sesión
        # Esto fuerza a Flask a serializar y guardar la sesión
        try:
            # Esto fuerza la serialización de la sesión
            _ = len(session)
            # También forzar que se guarde el token CSRF si existe
            if '_csrf_token' in session or '_session_init' in session:
                session.modified = True
        except Exception as e:
            # Si hay error, registrar pero continuar
            import logging
            logging.getLogger(__name__).warning(f"Error al guardar sesión: {e}")

    try:
        from flask import g
        ref_code = session.get('ref_afiliado_codigo')
        cookie_code = request.cookies.get(AFILIADO_REF_COOKIE)
        rol_session = str(session.get('rol', '')).lower()
        if rol_session != 'cliente':
            if ref_code and (getattr(g, 'set_ref_cookie', False) or cookie_code != ref_code):
                response.set_cookie(
                    AFILIADO_REF_COOKIE,
                    ref_code,
                    max_age=AFILIADO_REF_MAX_AGE,
                    httponly=True,
                    samesite='Lax',
                    secure=is_production
                )
            if getattr(g, 'clear_ref_cookie', False):
                response.delete_cookie(AFILIADO_REF_COOKIE)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Error al ajustar cookie afiliado: {e}")
    return response

def get_afiliado_referido():
    """Retorna afiliado referido almacenado en session (si aplica)."""
    if session.get('afiliado_auth'):
        return None, None
    try:
        from flask import g
    except Exception:
        g = None

    if g and getattr(g, 'current_user', None) and g.current_user.get('rol'):
        if g.current_user.get('rol') != 'cliente':
            return None, None
    if session.get('rol') and str(session.get('rol')).lower() != 'cliente':
        return None, None

    usuario_id = None
    if g and getattr(g, 'current_user', None) and g.current_user.get('rol') == 'cliente':
        usuario_id = g.current_user.get('usuario_id')
    elif str(session.get('rol', '')).lower() == 'cliente':
        usuario_id = session.get('usuario_id')

    if usuario_id:
        afiliado = obtener_afiliado_cliente(usuario_id)
        if afiliado:
            return afiliado.get('afiliado_id'), afiliado.get('codigo_afiliado')
        return None, None

    afiliado_id = session.get('ref_afiliado_id')
    afiliado_codigo = session.get('ref_afiliado_codigo')
    if not afiliado_id or not afiliado_codigo:
        cookie_code = (request.cookies.get(AFILIADO_REF_COOKIE) or '').strip()
        if cookie_code:
            afiliado = obtener_afiliado_por_codigo(cookie_code)
            if afiliado:
                afiliado_id = afiliado['id']
                afiliado_codigo = afiliado['codigo_afiliado']
                session['ref_afiliado_id'] = afiliado_id
                session['ref_afiliado_codigo'] = afiliado_codigo
                session.modified = True
    if not afiliado_id or not afiliado_codigo:
        return None, None
    try:
        afiliado_id = int(afiliado_id)
    except (TypeError, ValueError):
        return None, None
    return afiliado_id, str(afiliado_codigo)

def resolver_afiliado_por_email(email, afiliado_id, afiliado_codigo):
    """Si el email pertenece a un cliente, usa su afiliado fijo o ninguno."""
    if not email:
        return afiliado_id, afiliado_codigo
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM shopfusion.usuarios
                WHERE lower(email) = %s
            """, (email.lower(),))
            usuario = cur.fetchone()
            if not usuario:
                return afiliado_id, afiliado_codigo
            cur.execute("""
                SELECT ac.afiliado_id, COALESCE(ac.codigo_afiliado, a.codigo_afiliado) as codigo_afiliado
                FROM shopfusion.afiliados_clientes ac
                JOIN shopfusion.afiliados a ON ac.afiliado_id = a.id
                WHERE ac.usuario_id = %s
                LIMIT 1
            """, (usuario['id'],))
            afiliado = cur.fetchone()
            if afiliado:
                return afiliado.get('afiliado_id'), afiliado.get('codigo_afiliado')
            return None, None
    except Exception as e:
        app.logger.warning("[AFILIADOS_REF] Error resolviendo afiliado por email: %s", e)
        return afiliado_id, afiliado_codigo
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass

@app.before_request
def track_afiliado_referral():
    """Detecta ?ref= y registra el click para atribuir comisiones."""
    ref_code = (request.args.get('ref') or '').strip()
    cookie_code = (request.cookies.get(AFILIADO_REF_COOKIE) or '').strip()
    try:
        from flask import g
    except Exception:
        g = None

    is_cliente = False
    if g and getattr(g, 'current_user', None) and g.current_user.get('rol') == 'cliente':
        is_cliente = True
    elif str(session.get('rol', '')).lower() == 'cliente':
        is_cliente = True
    elif str(session.get('rol', '')).lower():
        return

    if not ref_code:
        if session.get('afiliado_auth'):
            return
        if is_cliente:
            return
        if session.get('ref_afiliado_codigo'):
            return
        if not cookie_code:
            return
        afiliado = obtener_afiliado_por_codigo(cookie_code)
        if not afiliado:
            if g:
                g.clear_ref_cookie = True
            return
        session['ref_afiliado_id'] = afiliado['id']
        session['ref_afiliado_codigo'] = afiliado['codigo_afiliado']
        session.modified = True
        return
    if session.get('afiliado_auth'):
        return

    afiliado = obtener_afiliado_por_codigo(ref_code)
    if not afiliado:
        return

    producto_raw = request.args.get('producto') or request.args.get('producto_id')
    producto_id = None
    if producto_raw:
        try:
            producto_id = int(producto_raw)
        except (TypeError, ValueError):
            producto_id = None

    try:
        registrar_click_afiliado(
            afiliado['id'],
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            producto_id=producto_id
        )
    except Exception as e:
        app.logger.warning("[AFILIADOS_REF] No se pudo registrar click: %s", e)

    if is_cliente:
        return

    session['ref_afiliado_id'] = afiliado['id']
    session['ref_afiliado_codigo'] = afiliado['codigo_afiliado']
    session.modified = True
    if g:
        g.set_ref_cookie = afiliado['codigo_afiliado']

def get_db_connection():
    """Conexión a la base de datos - Usa esquema shopfusion"""
    from urllib.parse import unquote
    database_url = config('DATABASE_URL')
    result = urlparse(database_url)
    # Decodificar la contraseña explícitamente por si acaso
    password = unquote(result.password) if result.password else result.password
    # Usar puerto por defecto si no está especificado
    port = result.port if result.port else 5432
    conn = psycopg.connect(
        dbname=result.path[1:],
        user=result.username,
        password=password,
        host=result.hostname,
        port=port,
        sslmode='require',
        row_factory=dict_row
    )
    # Configurar el esquema por defecto a shopfusion
    with conn.cursor() as cur:
        cur.execute("SET search_path TO shopfusion")
    conn.commit()
    return conn

MAX_INTENTOS = 15  # Aumentado de 5 a 15 para evitar bloqueos durante desarrollo
IP_PERMITIDA = '177.234.196.7'
TIMEOUT_INTENTOS = 300  # 5 minutos - tiempo después del cual se resetean los intentos
BANCOS_ECUADOR = ['Pichincha', 'Guayaquil', 'Produbanco']
METODOS_PAGO_ECUADOR = ['transferencia', 'paypal']
METODOS_PAGO_INTERNACIONAL = ['paypal', 'skrill']
FRECUENCIAS_PAGO = ['semanal', 'quincenal', 'mensual']
STOCK_BAJO_UMBRAL = 5


def ensure_envio_clientes_table(conn=None):
    """
    Crea tabla de datos de envío/facturación para clientes (sin alterar tablas existentes).
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS shopfusion.datos_envio_clientes (
                    usuario_id INTEGER PRIMARY KEY REFERENCES shopfusion.usuarios(id) ON DELETE CASCADE,
                    tipo_identificacion VARCHAR(20),
                    numero_identificacion VARCHAR(50),
                    nombre VARCHAR(150),
                    apellido VARCHAR(150),
                    email VARCHAR(200),
                    telefono VARCHAR(50),
                    pais VARCHAR(100) DEFAULT 'Ecuador',
                    provincia VARCHAR(150),
                    ciudad VARCHAR(150),
                    direccion TEXT,
                    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if close_conn:
            conn.close()

def get_envio_cliente(usuario_id):
    """Obtiene datos de envío/facturación guardados del cliente."""
    conn = get_db_connection()
    try:
        ensure_envio_clientes_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tipo_identificacion, numero_identificacion, nombre, apellido, email,
                       telefono, pais, provincia, ciudad, direccion
                FROM shopfusion.datos_envio_clientes
                WHERE usuario_id = %s
                """,
                (usuario_id,)
            )
            return cur.fetchone()
    finally:
        conn.close()

def upsert_envio_cliente(usuario_id, datos):
    """Guarda/actualiza datos de envío del cliente."""
    conn = get_db_connection()
    try:
        ensure_envio_clientes_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO shopfusion.datos_envio_clientes (
                    usuario_id, tipo_identificacion, numero_identificacion, nombre, apellido, email,
                    telefono, pais, provincia, ciudad, direccion, actualizado_en
                ) VALUES (
                    %(usuario_id)s, %(tipo_identificacion)s, %(numero_identificacion)s, %(nombre)s, %(apellido)s, %(email)s,
                    %(telefono)s, %(pais)s, %(provincia)s, %(ciudad)s, %(direccion)s, CURRENT_TIMESTAMP
                )
                ON CONFLICT (usuario_id)
                DO UPDATE SET
                    tipo_identificacion = EXCLUDED.tipo_identificacion,
                    numero_identificacion = EXCLUDED.numero_identificacion,
                    nombre = EXCLUDED.nombre,
                    apellido = EXCLUDED.apellido,
                    email = EXCLUDED.email,
                    telefono = EXCLUDED.telefono,
                    pais = EXCLUDED.pais,
                    provincia = EXCLUDED.provincia,
                    ciudad = EXCLUDED.ciudad,
                    direccion = EXCLUDED.direccion,
                    actualizado_en = CURRENT_TIMESTAMP;
                """,
                {
                    'usuario_id': usuario_id,
                    'tipo_identificacion': datos.get('tipo_identificacion'),
                    'numero_identificacion': datos.get('numero_identificacion'),
                    'nombre': datos.get('nombre'),
                    'apellido': datos.get('apellido'),
                    'email': datos.get('email'),
                    'telefono': datos.get('telefono'),
                    'pais': datos.get('pais') or 'Ecuador',
                    'provincia': datos.get('provincia'),
                    'ciudad': datos.get('ciudad'),
                    'direccion': datos.get('direccion'),
                }
            )
            conn.commit()
    finally:
        conn.close()


def ensure_pedidos_entregas_table(conn=None):
    """
    Crea una tabla auxiliar para marcar pedidos como entregados/leídos
    sin alterar cliente_compraron_productos. Devuelve True si existe/creó.
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    ok = True
    try:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS shopfusion.pedidos_entregas (
                        pedido_id INTEGER PRIMARY KEY,
                        entregado BOOLEAN DEFAULT FALSE,
                        fecha_entregado TIMESTAMP NULL
                    );
                """)
                conn.commit()
            except Exception:
                conn.rollback()
                ok = False
    finally:
        if close_conn:
            conn.close()
    return ok

def link_proveedor_column_exists(conn=None):
    """Check if link_proveedor column exists in shopfusion.productos_vendedor."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'shopfusion'
                    AND table_name = 'productos_vendedor'
                    AND column_name = 'link_proveedor'
                );
            """)
            row = cur.fetchone()
            return bool(row.get('exists', False)) if row else False
    finally:
        if close_conn:
            conn.close()

def ensure_estado_entrega_columns(conn=None):
    """
    Garantiza que cliente_compraron_productos tenga columnas de estado/fecha de entrega
    sin fallar si ya existen. Devuelve True si quedaron creadas o ya estaban.
    """
    ok = True
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    ALTER TABLE shopfusion.cliente_compraron_productos
                    ADD COLUMN IF NOT EXISTS estado_entrega VARCHAR(20) DEFAULT 'pendiente';
                """)
                cur.execute("""
                    ALTER TABLE shopfusion.cliente_compraron_productos
                    ADD COLUMN IF NOT EXISTS fecha_entrega TIMESTAMP NULL;
                """)
                conn.commit()
            except Exception:
                conn.rollback()
                ok = False
    finally:
        if close_conn:
            conn.close()
    return ok

def has_estado_entrega_columns(conn=None):
    """Verifica si las columnas de entrega existen."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'shopfusion'
                  AND table_name = 'cliente_compraron_productos'
                  AND column_name IN ('estado_entrega','fecha_entrega');
            """)
            rows = cur.fetchall()
            cols = {r['column_name'] for r in rows}
            return 'estado_entrega' in cols and 'fecha_entrega' in cols
    finally:
        if close_conn:
            conn.close()

# ============================================================================
# FUNCIONES DE SEGURIDAD
# ============================================================================

def validar_nombre_tabla(nombre):
    """
    Valida que un nombre de tabla sea seguro (solo letras, números, guiones bajos)
    Previene SQL Injection al usar nombres de tablas dinámicos
    """
    import re
    if not nombre or not isinstance(nombre, str):
        return False
    # Solo permitir letras, números y guiones bajos, máximo 63 caracteres (límite PostgreSQL)
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_]{0,62}$'
    return bool(re.match(pattern, nombre))

def validar_nombre_columna(nombre):
    """
    Valida que un nombre de columna sea seguro
    """
    import re
    if not nombre or not isinstance(nombre, str):
        return False
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_]{0,62}$'
    return bool(re.match(pattern, nombre))


def validar_tipo_columna(tipo):
    """Valida tipo de columna para evitar SQL malicioso en create_table."""
    if not tipo or not isinstance(tipo, str):
        return False
    tipo = tipo.strip()
    if not tipo:
        return False
    lowered = tipo.lower()
    if ";" in tipo or "--" in tipo or "/*" in tipo or "*/" in tipo:
        return False
    # Permitir solo caracteres seguros
    if not re.match(r'^[a-zA-Z0-9_(),\\s]+$', tipo):
        return False
    # Bloquear palabras clave peligrosas
    for kw in ["drop", "alter", "grant", "revoke", "truncate", "delete", "insert", "update"]:
        if kw in lowered:
            return False
    return True


def ensure_direcciones_tables(conn=None):
    """Crea tablas de direcciones para clientes y afiliados si no existen."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopfusion.direcciones_clientes (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER NOT NULL REFERENCES shopfusion.usuarios(id) ON DELETE CASCADE,
                    pais VARCHAR(100) NOT NULL,
                    ciudad VARCHAR(150) NOT NULL,
                    direccion TEXT NOT NULL,
                    telefono VARCHAR(50) NOT NULL,
                    principal BOOLEAN DEFAULT FALSE,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (usuario_id, pais, ciudad, direccion, telefono)
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_direcciones_clientes_usuario
                ON shopfusion.direcciones_clientes(usuario_id);
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopfusion.direcciones_afiliados (
                    id SERIAL PRIMARY KEY,
                    afiliado_id INTEGER NOT NULL REFERENCES shopfusion.afiliados(id) ON DELETE CASCADE,
                    pais VARCHAR(100) NOT NULL,
                    ciudad VARCHAR(150) NOT NULL,
                    direccion TEXT NOT NULL,
                    telefono VARCHAR(50) NOT NULL,
                    principal BOOLEAN DEFAULT FALSE,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (afiliado_id, pais, ciudad, direccion, telefono)
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_direcciones_afiliados_afiliado
                ON shopfusion.direcciones_afiliados(afiliado_id);
            """)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if close_conn:
            conn.close()


def ensure_soporte_table(conn=None):
    """Crea tabla de tickets de soporte si no existe."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopfusion.tickets_soporte (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(150) NOT NULL,
                    email VARCHAR(200) NOT NULL,
                    mensaje TEXT NOT NULL,
                    estado VARCHAR(30) DEFAULT 'abierto',
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_tickets_soporte_email
                ON shopfusion.tickets_soporte(email);
            """)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if close_conn:
            conn.close()

def obtener_tablas_permitidas():
    """
    Retorna lista de tablas permitidas para operaciones dinámicas
    """
    return {
        'usuarios', 'productos_vendedor', 'sorteos', 'sugerencias',
        'vendedores_ecuador', 'afiliados', 'comisiones_afiliados',
        'tracking_afiliados', 'cliente_compraron_productos', 'boletos'
    }

def vendedores_table_exists(conn=None):
    """Check if shopfusion.vendedores_ecuador exists."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'shopfusion'
                    AND table_name = 'vendedores_ecuador'
                );
            """)
            row = cur.fetchone()
            return bool(row.get('exists', False)) if row else False
    finally:
        if close_conn:
            conn.close()

# Inicializacion de esquema movida a scripts/migraciones controladas.

# Función helper para obtener categorías desde BD (con fallback)
def get_categorias():
    """Obtiene categorías activas desde BD, con fallback a lista hardcodeada si falla"""
    try:
        return obtener_categorias_como_lista()
    except Exception:
        # Fallback a categorías básicas si falla la BD
        return ["Tecnología", "Salud", "Ropa", "Gaming", "Hogar", "Otros"]

def validar_correo(email):
    patron = r'^[\w\.-]+@[a-zA-Z\d\.-]+\.[a-zA-Z]{2,}$'
    return re.match(patron, email) is not None


def _to_decimal(value):
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _money(value):
    return _to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _amounts_match(expected, actual, tolerance=Decimal("0.01")):
    expected_q = _money(expected)
    actual_q = _money(actual)
    return abs(expected_q - actual_q) <= tolerance

class SubscribeForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Suscribir')

class ContactForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    message = TextAreaField('Mensaje', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Enviar')

class AdminLoginForm(FlaskForm):
    usuario = StringField('Usuario', validators=[DataRequired(), Length(max=50)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar sesión')


class SorteoForm(FlaskForm):
    id = IntegerField('ID', default=0)
    titulo = StringField('Título del sorteo', validators=[DataRequired(), Length(max=150)])
    descripcion = TextAreaField('Descripción del sorteo', validators=[DataRequired(), Length(max=500)])
    imagen = StringField('Imagen del premio (URL)', validators=[DataRequired(), Length(max=300)])
    submit = SubmitField('Agregar sorteo')

class AfiliadoRegistroForm(FlaskForm):
    nombre = StringField('Nombre completo', validators=[DataRequired(), Length(max=150)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=150)])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Registrarse como afiliado')

class AfiliadoLoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar sesión')
import requests
from decouple import config

PAYPAL_CLIENT_ID = config('PAYPAL_CLIENT_ID')
PAYPAL_SECRET = config('PAYPAL_SECRET')
PAYPAL_MODE = config('PAYPAL_MODE', default='sandbox')  # sandbox o live
PAYPAL_API_BASE = "https://api-m.sandbox.paypal.com" if PAYPAL_MODE == 'sandbox' else "https://api-m.paypal.com"
PAYPAL_TIMEOUT_SECONDS = 15
SORTEO_BOLETO_USD = config('SORTEO_BOLETO_USD', default='1.00')
SORTEO_BOLETO_CURRENCY = config('SORTEO_BOLETO_CURRENCY', default='USD')

# Número de contacto para WhatsApp (usar formato +<código-país><número>)
WHATSAPP_NUMBER = config('WHATSAPP_NUMBER', default='+593987865420')
# Versión sin + para enlaces wa.me
WHATSAPP_NUMBER_DIGITS = WHATSAPP_NUMBER.replace('+', '')

if is_production and PAYPAL_MODE != 'live':
    raise RuntimeError("PAYPAL_MODE must be 'live' in production")


@app.route('/api/paypal/capture', methods=['POST'])
@limiter.limit("20 per minute")  # Máximo 20 capturas por minuto
def capture_payment():
    """Verifica y captura el pago en PayPal para el sorteo."""
    try:
        # 👀 Leer JSON sin explotar si viene vacío
        data = request.get_json(silent=True) or {}

        # Aceptar varios nombres posibles por si el JS envía otra clave
        order_id = (
            data.get('orderID') or
            data.get('orderId') or
            data.get('order_id') or
            data.get('id')
        )

        if not order_id:
            app.logger.error(f"[PAYPAL_CAPTURE] Falta orderID en el payload: {data}")
            return jsonify({'error': 'Falta el orderID', 'payload': data}), 400

        # Inicializar variables para evitar referencias indefinidas
        expected_total = Decimal("0")
        monto_bruto_total = Decimal("0")
        descuento_aplicado = Decimal("0")
        descuento_disponible = Decimal("0")
        es_afiliado = False
        afiliado_id_sesion = None

        # 🔑 Obtener token de acceso de PayPal
        auth = (PAYPAL_CLIENT_ID, PAYPAL_SECRET)
        token_resp = requests.post(
            f"{PAYPAL_API_BASE}/v1/oauth2/token",
            data={'grant_type': 'client_credentials'},
            auth=auth,
            timeout=PAYPAL_TIMEOUT_SECONDS
        )

        if token_resp.status_code != 200:
            app.logger.error(
                f"[PAYPAL_CAPTURE] Error al obtener token: {token_resp.status_code} {token_resp.text}"
            )
            return jsonify({'error': 'No se pudo obtener token de PayPal'}), 500

        access_token = token_resp.json().get('access_token')
        if not access_token:
            # No loguear el texto completo de la respuesta de PayPal (puede contener info sensible)
            app.logger.error(f"[PAYPAL_CAPTURE] Respuesta sin access_token: status={token_resp.status_code}")
            return jsonify({'error': 'No se pudo obtener token de PayPal'}), 500

        # 💰 Capturar el pago
        capture_url = f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        capture_resp = requests.post(capture_url, headers=headers, timeout=PAYPAL_TIMEOUT_SECONDS)
        result = capture_resp.json()

        # ✔️ Captura correcta
        if capture_resp.status_code == 201:
            try:
                payer_name = result['payer']['name']['given_name']
                capture_data = result['purchase_units'][0]['payments']['captures'][0]['amount']
                amount = capture_data['value']
                currency = capture_data.get('currency_code', 'USD')
            except Exception as parse_err:
                app.logger.error(f"[PAYPAL_CAPTURE] Error parseando respuesta: {parse_err} {result}")
                return jsonify({'error': 'Pago capturado pero respuesta inesperada', 'raw': result}), 200

            expected_amount = _to_decimal(SORTEO_BOLETO_USD)
            amount_value = _to_decimal(amount)
            if currency != SORTEO_BOLETO_CURRENCY or not _amounts_match(expected_amount, amount_value):
                app.logger.error(
                    "[PAYPAL_CAPTURE] Monto inesperado order_id=%s esperado=%s %s recibido=%s %s",
                    order_id,
                    expected_amount,
                    SORTEO_BOLETO_CURRENCY,
                    amount_value,
                    currency,
                )
                return jsonify({'error': 'Monto inesperado'}), 400

            app.logger.info(
                f"[PAYPAL_CAPTURE] Captura OK order_id={order_id} amount={amount} {currency}"
            )

            # (Opcional) también podrías marcar pago_confirmado aquí
            # session['pago_confirmado'] = True

            return jsonify({
                'status': 'success',
                'payer': payer_name,
                'amount': amount,
                'currency': currency
            })

        # 🟡 Caso típico: ya fue capturada antes
        if capture_resp.status_code == 422:
            issue = ''
            try:
                issue = result['details'][0]['issue']
            except Exception:
                pass

            if issue == 'ORDER_ALREADY_CAPTURED':
                app.logger.warning(
                    f"[PAYPAL_CAPTURE] Orden ya capturada order_id={order_id}"
                )
                # Lo tratamos como éxito lógico para no romper el flujo
                return jsonify({
                    'status': 'already_captured',
                    'details': result
                }), 200

        # ❌ Cualquier otro error de PayPal
        app.logger.error(
            f"[PAYPAL_CAPTURE] Error al capturar: status={capture_resp.status_code} body={result}"
        )
        return jsonify({'error': 'Error al capturar el pago', 'details': result}), 400

    except Exception as e:
        app.logger.exception(f"[PAYPAL_CAPTURE] Excepción inesperada: {e}")
        return jsonify({'error': 'Error interno al procesar el pago'}), 500


@app.route('/api/exclusivos/checkout', methods=['POST'])
@limiter.limit("10 per minute")  # Máximo 10 checkouts por minuto por IP
def exclusivos_checkout():
    """
    Captura el pago de PayPal para un producto exclusivo y registra la compra
    en la tabla cliente_compraron_productos.
    """
    try:
        data = request.get_json() or {}

        order_id = data.get('orderID')
        producto_id = data.get('producto_id')
        cantidad = int(data.get('cantidad') or 1)

        nombre = (data.get('nombre') or '').strip()
        apellido = (data.get('apellido') or '').strip()
        email = (data.get('email') or '').strip()
        telefono = (data.get('telefono') or '').strip()
        pais = (data.get('pais') or '').strip()
        direccion = (data.get('direccion') or '').strip()
        provincia = (data.get('provincia') or '').strip()
        ciudad = (data.get('ciudad') or '').strip()
        tipo_identificacion = (data.get('tipo_identificacion') or '').strip()
        numero_identificacion = (data.get('numero_identificacion') or '').strip()
        provincia = (data.get('provincia') or '').strip()
        ciudad = (data.get('ciudad') or '').strip()
        tipo_identificacion = (data.get('tipo_identificacion') or '').strip()
        numero_identificacion = (data.get('numero_identificacion') or '').strip()

        # Completar datos faltantes desde sesión/BD si el cliente está autenticado
        usuario_id = None
        try:
            from flask import g
            if hasattr(g, 'current_user') and g.current_user and g.current_user.get('rol') == 'cliente':
                usuario_id = g.current_user.get('usuario_id')
        except Exception:
            usuario_id = None
        if not usuario_id and session.get('usuario_id') and session.get('rol') == 'cliente':
            usuario_id = session.get('usuario_id')

        if usuario_id:
            conn_dir = None
            try:
                conn_dir = get_db_connection()
                ensure_direcciones_tables(conn_dir)
                with conn_dir.cursor() as cur:
                    # Datos básicos del usuario
                    cur.execute("SELECT nombre, email FROM shopfusion.usuarios WHERE id = %s", (usuario_id,))
                    usuario = cur.fetchone()
                    if usuario:
                        if not nombre:
                            nombre = usuario.get('nombre', '')
                        if not email:
                            email = usuario.get('email', '')
                    # Dirección guardada más reciente
                    cur.execute("""
                        SELECT pais, ciudad, direccion, telefono
                        FROM shopfusion.direcciones_clientes
                        WHERE usuario_id = %s
                        ORDER BY actualizado_en DESC, creado_en DESC
                        LIMIT 1
                    """, (usuario_id,))
                    dir_guardada = cur.fetchone()
                    if dir_guardada:
                        if not pais:
                            pais = dir_guardada.get('pais', '')
                        if not direccion:
                            direccion = dir_guardada.get('direccion', '')
                        if not telefono:
                            telefono = dir_guardada.get('telefono', '')
            finally:
                if conn_dir:
                    conn_dir.close()

        # Validaciones básicas
        if not order_id:
            return jsonify({'error': 'Falta orderID de PayPal'}), 400
        if not producto_id:
            return jsonify({'error': 'Falta producto_id'}), 400
        if not (nombre and apellido and email and telefono and pais and direccion):
            return jsonify({'error': 'Faltan datos del cliente'}), 400

        # Obtener producto y calcular total esperado
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT precio, precio_oferta, precio_proveedor, stock
                    FROM productos_vendedor
                    WHERE id = %s AND estado = 'activo'
                """, (producto_id,))
                producto = cur.fetchone()
        finally:
            conn.close()

        if not producto:
            return jsonify({'error': 'Producto no encontrado'}), 404

        stock_actual = int(producto.get('stock') or 0)
        if cantidad > stock_actual:
            return jsonify({'error': f'Stock insuficiente. Disponible: {stock_actual}'}), 400

        precio_normal = float(producto.get('precio') or 0)
        precio_oferta_val = float(producto.get('precio_oferta') or 0)
        if precio_oferta_val > 0 and precio_oferta_val < precio_normal:
            precio_final = precio_oferta_val
        else:
            precio_final = precio_normal
        expected_total = precio_final * cantidad

        # 🔑 Obtener token de acceso de PayPal (igual que en capture_payment)
        auth = (PAYPAL_CLIENT_ID, PAYPAL_SECRET)
        response = requests.post(
            f"{PAYPAL_API_BASE}/v1/oauth2/token",
            data={'grant_type': 'client_credentials'},
            auth=auth,
            timeout=PAYPAL_TIMEOUT_SECONDS
        )
        access_token = response.json().get('access_token')

        if not access_token:
            return jsonify({'error': 'No se pudo obtener token de PayPal'}), 500

        # 💰 Capturar el pago
        capture_url = f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        capture_response = requests.post(capture_url, headers=headers, timeout=PAYPAL_TIMEOUT_SECONDS)
        result = capture_response.json()

        if capture_response.status_code != 201:
            app.logger.error(f"[EXCLUSIVOS_CHECKOUT] Error al capturar pago: {result}")
            return jsonify({
                'error': 'Error al capturar el pago en PayPal',
                'details': result
            }), 400

        # Datos del pago
        payer_info = result.get('payer', {})
        payer_name = payer_info.get('name', {}).get('given_name', '') or nombre
        paypal_email = (payer_info.get('email_address') or '').strip()
        email_cuenta = session.get('email') if session.get('rol') == 'cliente' else None
        payer_email = (email_cuenta or email or paypal_email).strip()
        if paypal_email:
            session['ultima_paypal_email'] = paypal_email
            session.modified = True

        purchase_unit = result['purchase_units'][0]
        capture = purchase_unit['payments']['captures'][0]

        amount_value = float(capture['amount']['value'])
        currency_code = capture['amount']['currency_code']
        paypal_capture_id = capture['id']

        if not _amounts_match(expected_total, amount_value):
            app.logger.error(
                "[EXCLUSIVOS_CHECKOUT] Monto no coincide. Esperado=%s Capturado=%s",
                _money(expected_total),
                _money(amount_value)
            )
            return jsonify({'error': 'Monto capturado no coincide con el total esperado'}), 400

        # 🧾 Registrar compra en la BD y actualizar stock
        # Obtener información del afiliado de la sesión
        afiliado_id, afiliado_codigo = get_afiliado_referido()
        afiliado_id, afiliado_codigo = resolver_afiliado_por_email(payer_email, afiliado_id, afiliado_codigo)

        precio_proveedor = float(producto.get('precio_proveedor') or 0)
        precio_unitario_pagado = amount_value / cantidad if cantidad else amount_value
        monto_margen = (precio_unitario_pagado - precio_proveedor) * cantidad
        
        compra_id = registrar_compra_exclusivo(
            producto_id=int(producto_id),
            nombre=nombre,
            apellido=apellido,
            email=email_para_guardar,
            telefono=telefono,
            pais=pais,
            direccion=direccion,
            provincia=provincia,
            ciudad=ciudad,
            tipo_identificacion=tipo_identificacion,
            numero_identificacion=numero_identificacion,
            cantidad=cantidad,
            paypal_order_id=order_id,
            paypal_capture_id=paypal_capture_id,
            monto_total=amount_value,
            moneda=currency_code,
            estado_pago="pagado",
            afiliado_id=afiliado_id,
            afiliado_codigo=afiliado_codigo
        )

        # Guardar/actualizar dirección del cliente autenticado para futuras compras
        if usuario_id:
            conn_dir = None
            try:
                conn_dir = get_db_connection()
                ensure_direcciones_tables(conn_dir)
                with conn_dir.cursor() as cur:
                    cur.execute("""
                        INSERT INTO shopfusion.direcciones_clientes
                            (usuario_id, pais, ciudad, direccion, telefono, principal, actualizado_en)
                        VALUES (%s, %s, %s, %s, %s, FALSE, CURRENT_TIMESTAMP)
                        ON CONFLICT (usuario_id, pais, ciudad, direccion, telefono)
                        DO UPDATE SET actualizado_en = CURRENT_TIMESTAMP
                    """, (usuario_id, pais, '', direccion, telefono))
                    conn_dir.commit()
            except Exception as e:
                app.logger.warning(f"[EXCLUSIVOS_CHECKOUT] No se pudo guardar dirección de cliente: {e}")
            finally:
                if conn_dir:
                    try:
                        conn_dir.close()
                    except Exception:
                        pass

        # 💰 Registrar comisión de afiliado si existe
        if afiliado_id:
            conn = None
            try:
                # MEJORA: Verificar que el afiliado esté activo antes de registrar comisión
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, estado, comision_porcentaje 
                        FROM afiliados 
                        WHERE id = %s AND estado = 'activo'
                    """, (afiliado_id,))
                    afiliado = cur.fetchone()
                    
                    if afiliado:
                        # Registrar comisión con producto_id para mejor asociación de tracking
                        registrar_comision(
                            afiliado_id=afiliado_id,
                            compra_id=compra_id,
                            monto_venta=amount_value,
                            comision_porcentaje=float(afiliado['comision_porcentaje']),
                            producto_id=int(producto_id),  # Pasar producto_id para asociación correcta
                            monto_margen=monto_margen
                        )
                        app.logger.info(f"[EXCLUSIVOS_CHECKOUT] Comisión registrada para afiliado {afiliado_id}, compra {compra_id}, producto {producto_id}")
                    else:
                        app.logger.warning(f"[EXCLUSIVOS_CHECKOUT] Afiliado {afiliado_id} no encontrado o inactivo - no se registra comisión")
            except Exception as e:
                app.logger.error(f"[EXCLUSIVOS_CHECKOUT] Error al registrar comisión: {e}")
            finally:
                if conn:
                    conn.close()

        return jsonify({
            'status': 'success',
            'payer': payer_name,
            'amount': amount_value,
            'moneda': currency_code,
            'compra_id': compra_id
        })

    except Exception as e:
        app.logger.error(f"[EXCLUSIVOS_CHECKOUT] Error inesperado: {e}")
        return jsonify({'error': 'Error inesperado al procesar el pago'}), 500


@app.route('/api/afiliados/checkout', methods=['POST'])
@limiter.limit("10 per minute")
def afiliados_checkout():
    """
    Checkout para afiliados con descuento aplicado.
    El descuento = comisión ganada (acumulada cada 3 ventas, válido por 15 días).
    """
    if 'afiliado_id' not in session or not session.get('afiliado_auth'):
        return jsonify({'error': 'Debes iniciar sesión como afiliado'}), 401
    
    try:
        data = request.get_json() or {}
        afiliado_id = session['afiliado_id']
        
        order_id = data.get('orderID')
        producto_id = data.get('producto_id')
        cantidad = int(data.get('cantidad') or 1)
        usar_descuento = data.get('usar_descuento', False)
        
        nombre = (data.get('nombre') or '').strip()
        apellido = (data.get('apellido') or '').strip()
        email = (data.get('email') or '').strip()
        telefono = (data.get('telefono') or '').strip()
        pais = (data.get('pais') or '').strip()
        direccion = (data.get('direccion') or '').strip()
        
        # Completar con datos existentes si falta información
        if not nombre:
            nombre = session.get('afiliado_nombre', '')
        if not email:
            email = session.get('afiliado_email', '')
        if not telefono or not pais or not direccion:
            conn_dir = None
            try:
                conn_dir = get_db_connection()
                ensure_direcciones_tables(conn_dir)
                with conn_dir.cursor() as cur:
                    cur.execute("""
                        SELECT pais, ciudad, direccion, telefono
                        FROM shopfusion.direcciones_afiliados
                        WHERE afiliado_id = %s
                        ORDER BY actualizado_en DESC, creado_en DESC
                        LIMIT 1
                    """, (afiliado_id,))
                    dir_guardada = cur.fetchone()
                    if dir_guardada:
                        if not pais:
                            pais = dir_guardada.get('pais', '')
                        if not direccion:
                            direccion = dir_guardada.get('direccion', '')
                        if not telefono:
                            telefono = dir_guardada.get('telefono', '')
            finally:
                if conn_dir:
                    conn_dir.close()
        
        if not order_id or not producto_id:
            return jsonify({'error': 'Faltan datos requeridos'}), 400
        
        # Obtener producto
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, titulo, precio, precio_oferta, precio_proveedor, stock
                FROM productos_vendedor
                WHERE id = %s AND estado = 'activo'
            """, (producto_id,))
            producto = cur.fetchone()
        conn.close()
        
        if not producto:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        # Calcular precio final: usar precio_oferta si existe y es menor que precio, si no usar precio
        precio_normal = float(producto.get('precio') or 0)
        precio_oferta_val = float(producto.get('precio_oferta') or 0)
        if precio_oferta_val > 0 and precio_oferta_val < precio_normal:
            precio_final = precio_oferta_val
        else:
            precio_final = precio_normal
        
        precio_proveedor = float(producto.get('precio_proveedor') or 0)
        margen = precio_final - precio_proveedor
        
        # Obtener comisión del afiliado usando la función helper
        comision_porcentaje = obtener_comision_afiliado(afiliado_id)
        
        comision_ganada = (margen * comision_porcentaje) / 100
        
        # PRECIO QUE PAGA EL AFILIADO: Precio Final - Comisión que ganaría (solo si margen >= 0)
        if margen > 0:
            precio_afiliado = precio_final - comision_ganada
        else:
            precio_afiliado = precio_final
        
        # Descuento adicional si tiene descuento acumulado disponible
        descuento_adicional = 0.00
        if usar_descuento:
            descuento_disponible = obtener_descuento_disponible_afiliado(afiliado_id)
            descuento_adicional = min(descuento_disponible, precio_afiliado * cantidad)
            precio_afiliado = max(0, precio_afiliado - (descuento_adicional / cantidad))
        
        # El monto total que pagará el afiliado
        monto_total = precio_afiliado * cantidad
        
        # Verificar pago en PayPal
        auth = (PAYPAL_CLIENT_ID, PAYPAL_SECRET)
        response = requests.post(
            f"{PAYPAL_API_BASE}/v1/oauth2/token",
            data={'grant_type': 'client_credentials'},
            auth=auth,
            timeout=PAYPAL_TIMEOUT_SECONDS
        )
        access_token = response.json().get('access_token')
        
        if not access_token:
            conn.close()
            return jsonify({'error': 'No se pudo obtener token de PayPal'}), 500
        
        capture_url = f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        capture_response = requests.post(capture_url, headers=headers, timeout=PAYPAL_TIMEOUT_SECONDS)
        result = capture_response.json()
        
        if capture_response.status_code != 201:
            conn.close()
            return jsonify({'error': 'Error al capturar el pago en PayPal'}), 400
        
        # Registrar compra
        payer_info = result.get('payer', {})
        paypal_email = (payer_info.get('email_address') or '').strip()
        # Preferir el email de la cuenta/logueo para vincular la compra al perfil
        email_cuenta = None
        if session.get('rol') == 'cliente':
            email_cuenta = session.get('email')
        email_para_guardar = (email_cuenta or email or paypal_email).strip()
        # Guardamos el email de PayPal en sesi¢n como respaldo para futuras consultas
        if paypal_email:
            session['ultima_paypal_email'] = paypal_email
            session.modified = True
        capture = result['purchase_units'][0]['payments']['captures'][0]
        paypal_capture_id = capture['id']
        amount_value = float(capture['amount']['value'])

        if not _amounts_match(monto_total, amount_value):
            app.logger.error(
                "[AFILIADOS_CHECKOUT] Monto no coincide. Esperado=%s Capturado=%s",
                _money(monto_total),
                _money(amount_value)
            )
            conn.close()
            return jsonify({'error': 'Monto capturado no coincide con el total esperado'}), 400

        compra_id = registrar_compra_exclusivo(
            producto_id=int(producto_id),
            nombre=nombre,
            apellido=apellido,
            email=email_para_guardar,
            telefono=telefono,
            pais=pais,
            direccion=direccion,
            provincia=provincia,
            ciudad=ciudad,
            tipo_identificacion=tipo_identificacion,
            numero_identificacion=numero_identificacion,
            cantidad=cantidad,
            paypal_order_id=order_id,
            paypal_capture_id=paypal_capture_id,
            monto_total=monto_total,
            moneda='USD',
            estado_pago="pagado",
            afiliado_id=None,
            afiliado_codigo=None
        )
        
        # Aplicar descuento adicional usado (si se usó descuento acumulado)
        if descuento_adicional > 0:
            aplicar_descuento_afiliado(afiliado_id, descuento_adicional)
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'payer': f"{nombre} {apellido}",
            'amount': monto_total,
            'precio_original': precio_final,
            'precio_afiliado': precio_afiliado,
            'descuento_comision': comision_ganada * cantidad,  # Descuento por ser afiliado
            'descuento_adicional': descuento_adicional,  # Descuento acumulado usado
            'comision_ganada': comision_ganada * cantidad
        })
        
    except Exception as e:
        app.logger.error(f"[AFILIADOS_CHECKOUT] Error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': 'Error al procesar el pago'}), 500


@app.route('/api/afiliados/track-click', methods=['POST'])
@limiter.limit("60 per minute")
def afiliados_track_click():
    """Registra un click de producto desde la tienda general del afiliado."""
    try:
        data = request.get_json(force=True) or {}
        producto_id = data.get('producto_id') or data.get('product_id')
        if not producto_id:
            return jsonify({'ok': False, 'error': 'producto_id requerido'}), 400
        try:
            producto_id = int(producto_id)
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'error': 'producto_id invalido'}), 400

        afiliado_id, _ = get_afiliado_referido()
        if not afiliado_id:
            return jsonify({'ok': False, 'reason': 'sin_referido'}), 200

        registrar_click_afiliado(
            afiliado_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            producto_id=producto_id
        )
        return jsonify({'ok': True})
    except Exception as e:
        app.logger.warning(f"[AFILIADOS_TRACK_CLICK] Error: {e}")
        return jsonify({'ok': False}), 200


@app.route('/registro', methods=['GET', 'POST'])
@limiter.limit("3 per hour")  # Máximo 3 registros por hora por IP
def registro():
    if request.method == 'POST':
        try:
            nombre = request.form['nombreInput']
            email = request.form['correoInput'].strip().lower()
            contrasena = request.form['contrasenaInput']
            confirmar_contrasena = request.form['confirmarContrasena']
            if not validar_correo(email):
                raise ValueError(f"[REGISTRO] Correo inválido: {email}")
            if contrasena != confirmar_contrasena:
                raise ValueError("[REGISTRO] Las contraseñas no coinciden")
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Asegurar que estamos usando el esquema correcto
            cur.execute("SET search_path TO shopfusion, public")
            
            # VALIDACIÓN: Verificar si el email ya existe como afiliado o proveedor
            # Verificar en afiliados
            cur.execute("SELECT id, nombre FROM shopfusion.afiliados WHERE lower(email) = %s", (email,))
            afiliado_existente = cur.fetchone()
            if afiliado_existente:
                flash(f'Este email ya está registrado como afiliado. Si eres afiliado, inicia sesión desde "Trabaja con Nosotros" → "Programa de Afiliados".', 'warning')
                app.logger.warning(f"[REGISTRO] Intento de registro como cliente con email de afiliado: {email}")
                cur.close()
                conn.close()
                return redirect(url_for('registro'))
            
            # Verificar en vendedores/proveedores
            cur.execute("SELECT id, nombre_comercial FROM shopfusion.vendedores_ecuador WHERE lower(email) = %s", (email,))
            vendedor_existente = cur.fetchone()
            if vendedor_existente:
                flash(f'Este email ya está registrado como proveedor. Si eres proveedor, inicia sesión desde "Trabaja con Nosotros" → "Sé Nuestro Proveedor".', 'warning')
                app.logger.warning(f"[REGISTRO] Intento de registro como cliente con email de proveedor: {email}")
                cur.close()
                conn.close()
                return redirect(url_for('registro'))
            
            # Verificar si ya existe como cliente
            cur.execute("SELECT id FROM shopfusion.usuarios WHERE lower(email) = %s", (email,))
            cliente_existente = cur.fetchone()
            if cliente_existente:
                flash('Este email ya está registrado. Inicia sesión en su lugar.', 'warning')
                cur.close()
                conn.close()
                return redirect(url_for('login', tipo='cliente'))
            
            # Si no existe en ninguna tabla, proceder con el registro
            # CORREGIR SECUENCIA: Asegurar que la secuencia esté sincronizada antes de insertar
            try:
                # Intentar corregir la secuencia (puede estar en diferentes esquemas)
                cur.execute("SET search_path TO shopfusion, public")
                cur.execute("""
                    SELECT setval(
                        pg_get_serial_sequence('shopfusion.usuarios', 'id'),
                        COALESCE((SELECT MAX(id) FROM shopfusion.usuarios), 1),
                        true
                    );
                """)
                conn.commit()
                app.logger.info('[REGISTRO] Secuencia de usuarios corregida')
            except Exception as seq_error:
                # Si falla, intentar con el nombre directo de la secuencia
                try:
                    cur.execute("""
                        SELECT setval('shopfusion.usuarios_id_seq', 
                            COALESCE((SELECT MAX(id) FROM shopfusion.usuarios), 1), 
                            true);
                    """)
                    conn.commit()
                    app.logger.info('[REGISTRO] Secuencia corregida usando nombre directo')
                except Exception as seq_error2:
                    # Si también falla, intentar sin esquema
                    try:
                        cur.execute("""
                            SELECT setval('usuarios_id_seq', 
                                COALESCE((SELECT MAX(id) FROM shopfusion.usuarios), 1), 
                                true);
                        """)
                        conn.commit()
                        app.logger.info('[REGISTRO] Secuencia corregida sin esquema')
                    except Exception as seq_error3:
                        # Si todo falla, solo registrar advertencia y continuar
                        app.logger.warning(f'[REGISTRO] No se pudo corregir secuencia (continuando de todas formas): {seq_error3}')
                        conn.rollback()
            
            contrasena_cifrada = generate_password_hash(contrasena)
            cur.execute(
                "INSERT INTO shopfusion.usuarios (nombre, email, password, rol) VALUES (%s, %s, %s, 'cliente') RETURNING id",
                (nombre, email, contrasena_cifrada)
            )
            nuevo_usuario = cur.fetchone()
            conn.commit()
            usuario_id = nuevo_usuario.get('id') if nuevo_usuario else None
            if usuario_id:
                afiliado_id, afiliado_codigo = get_afiliado_referido()
                if afiliado_id:
                    asignar_afiliado_a_cliente(usuario_id, afiliado_id, afiliado_codigo)
            cur.close()
            conn.close()
            flash('Registro exitoso. Inicia sesión.', 'success')
            app.logger.info('[REGISTRO] Usuario registrado: %s', email)
            return redirect(url_for('login', tipo='cliente'))
        except ValueError as ve:
            flash(str(ve), 'danger')
            app.logger.warning(str(ve))
            return redirect(url_for('registro'))
        except psycopg.OperationalError as oe:
            msg = f"[REGISTRO] Error de conexión a la base de datos: {str(oe)}"
            flash(msg, 'danger')
            app.logger.error(msg)
            return redirect(url_for('registro'))
        except Exception as e:
            msg = f"[REGISTRO] Error inesperado: {str(e)}"
            flash(msg, 'danger')
            app.logger.error(msg)
            return redirect(url_for('registro'))
    app.logger.info('[REGISTRO] Acceso a la página de registro')
    return render_template('registro_inicio.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Máximo 5 intentos de login por minuto
def login():
    """Login principal - Por defecto para clientes, pero puede validar según contexto"""
    tipo_esperado = request.args.get('tipo', 'cliente').lower().strip()
    
    if request.method == 'POST':
        try:
            email = request.form['correoInput']
            contrasena = request.form['contrasenaInput']
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, nombre, email, password, rol FROM usuarios WHERE email = %s", [email])
            user = cur.fetchone()
            cur.close()
            conn.close()
            
            if user and check_password_hash(user['password'], contrasena):
                rol = user['rol'].lower().strip()
                
                # VALIDACIÓN POR CONTEXTO DE ACCESO
                # Si viene con tipo=cliente, solo acepta clientes
                if tipo_esperado == 'cliente':
                    if rol not in ['cliente']:
                        # Determinar a dónde redirigir según el rol
                        if rol in ['admin', 'base de datos', 'super admin']:
                            flash(f'⚠️ Esta cuenta pertenece a un {rol.upper()}. Por favor, inicia sesión desde el panel de administración.', 'warning')
                            return redirect(url_for('admin'))
                        elif rol == 'vendedor':
                            flash('⚠️ Esta cuenta pertenece a un PROVEEDOR. Por favor, inicia sesión desde "Trabaja con Nosotros" → "Iniciar Sesión como Proveedor".', 'warning')
                            return redirect(url_for('login_vendedor'))
                        else:
                            flash('⚠️ Esta cuenta no es de cliente. Si eres afiliado o proveedor, accede desde "Trabaja con Nosotros".', 'danger')
                        app.logger.warning(f"[LOGIN] Intento de login de {rol} como cliente: {email}")
                        return redirect(url_for('login', tipo='cliente'))
                
                # Crear sesión en BD con token
                tipo_usuario = 'cliente' if rol == 'cliente' else rol
                
                token = crear_sesion(
                    usuario_id=user['id'],
                    tipo_usuario=tipo_usuario,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    duracion_horas=24
                )
                
                if not token:
                    flash('Error al crear sesión. Intenta nuevamente.', 'danger')
                    return redirect(url_for('login', tipo=tipo_esperado))
                
                # Migrar carrito de cookies a BD si existe (solo para clientes)
                if rol == 'cliente':
                    carrito_cookies = session.get('carrito', [])
                    if carrito_cookies:
                        migrar_carrito_cookies_a_bd(user['id'], carrito_cookies)
                        session.pop('carrito', None)  # Limpiar carrito de cookies
                
                # Guardar token en cookie
                # Para clientes, redirigir a index (página principal)
                redirect_url = url_for('index') if rol == 'cliente' else url_for('usuario')
                if rol in ['admin', 'base de datos', 'super admin']:
                    redirect_url = url_for('admin')
                elif rol == 'vendedor':
                    redirect_url = url_for('vendedor_panel')
                response = make_response(redirect(redirect_url))
                response.set_cookie(
                    'auth_token',
                    token,
                    max_age=86400,
                    httponly=True,
                    samesite='Lax',
                    secure=is_production
                )
                
                # También guardar en session para compatibilidad temporal
                session['usuario_id'] = user['id']
                session['nombre'] = user['nombre']
                session['email'] = user['email']
                session['rol'] = user['rol']
                session['auth_token'] = token
                
                flash('Inicio de sesión exitoso', 'success')
                app.logger.info('[LOGIN] Usuario autenticado: %s (rol: %s)', email, user['rol'])
                
                return response
            else:
                # Verificar si el email existe en otras tablas (afiliados, vendedores)
                conn_check = get_db_connection()
                cur_check = conn_check.cursor()
                
                # Buscar en afiliados
                cur_check.execute("SELECT id, nombre FROM afiliados WHERE lower(email) = %s", (email.lower(),))
                afiliado = cur_check.fetchone()
                
                # Buscar en vendedores
                cur_check.execute("SELECT id, nombre_comercial FROM vendedores_ecuador WHERE lower(email) = %s", (email.lower(),))
                vendedor = cur_check.fetchone()
                
                cur_check.close()
                conn_check.close()
                
                # Si el email existe en otra tabla, informar al usuario
                if afiliado:
                    flash(f'⚠️ Esta cuenta pertenece a un AFILIADO. Por favor, inicia sesión desde "Trabaja con Nosotros" → "Iniciar Sesión como Afiliado".', 'warning')
                    app.logger.info(f"[LOGIN] Email {email} encontrado en afiliados, redirigiendo a login de afiliados")
                    return redirect(url_for('afiliados_login'))
                elif vendedor:
                    flash(f'⚠️ Esta cuenta pertenece a un PROVEEDOR. Por favor, inicia sesión desde "Trabaja con Nosotros" → "Iniciar Sesión como Proveedor".', 'warning')
                    app.logger.info(f"[LOGIN] Email {email} encontrado en vendedores, redirigiendo a login de vendedores")
                    return redirect(url_for('login_vendedor'))
                else:
                    # No exponer si el usuario existe o no (timing attack protection)
                    app.logger.warning(f"[LOGIN] Intento de login fallido para: {email}")
                    flash('Correo o contraseña incorrectos', 'danger')
                    return redirect(url_for('login', tipo=tipo_esperado))
        except psycopg.OperationalError as oe:
            app.logger.error(f"[LOGIN] Error de conexión a la base de datos: {str(oe)}")
            flash('Error de conexión. Intenta más tarde.', 'danger')
            return redirect(url_for('login', tipo=tipo_esperado))
        except Exception as e:
            app.logger.error(f"[LOGIN] Error inesperado: {str(e)}")
            flash('Error al procesar la solicitud. Intenta nuevamente.', 'danger')
            return redirect(url_for('login', tipo=tipo_esperado))
    
    app.logger.info('[LOGIN] Acceso a la página de login (tipo: %s)', tipo_esperado)
    # Determinar si viene de registro de cliente o de otro tipo
    tipo = request.args.get('tipo', 'cliente')
    return render_template('registro_inicio.html', tipo=tipo)

@app.route('/admin', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Máximo 5 intentos de login admin por minuto
def admin():
    # VALIDACIÓN: Si ya hay sesión como admin, redirigir al panel
    if 'usuario_id' in session and request.method == 'GET':
        rol_actual = str(session.get('rol', '')).strip().lower()
        if rol_actual in ['admin', 'base de datos', 'super admin']:
            if rol_actual == 'admin':
                return redirect(url_for('panel'))
            elif rol_actual == 'base de datos':
                return redirect(url_for('super_admin_bd'))
            else:
                return redirect(url_for('panel'))
        # Si hay sesión pero no es admin, limpiar sesión para permitir login de admin
        elif rol_actual in ['cliente', 'vendedor']:
            session.clear()
            flash('Sesión cerrada. Inicia sesión como administrador.', 'info')
            app.logger.info('[ADMIN] Sesión de %s cerrada para permitir login de admin', rol_actual)
    
    # LOGGING INMEDIATO AL INICIO
    app.logger.info('[ADMIN] ========== REQUEST ========== Método: %s, URL: %s', request.method, request.url)
    
    # CRÍTICO: Inicializar sesión ANTES de crear el formulario para que CSRF funcione
    # Asegurar que la sesión esté activa y se guarde
    session.permanent = True
    if 'intentos_admin' not in session:
        session['intentos_admin'] = 0
        session['ultimo_intento'] = int(time.time())
    else:
        # Resetear intentos si han pasado más de TIMEOUT_INTENTOS segundos
        ultimo_intento = session.get('ultimo_intento', 0)
        tiempo_transcurrido = int(time.time()) - ultimo_intento
        if tiempo_transcurrido > TIMEOUT_INTENTOS:
            session['intentos_admin'] = 0
            session['ultimo_intento'] = int(time.time())
            app.logger.info('[ADMIN] Intentos reseteados automáticamente después de %s segundos', tiempo_transcurrido)
    
    # Marcar sesión como modificada para forzar guardado
    session.modified = True

    form = AdminLoginForm()
    
    # Debug: Loggear TODOS los POSTs ANTES de cualquier validación
    if request.method == 'POST':
        try:
            app.logger.info('[ADMIN] ========== POST RECIBIDO ==========')
            app.logger.info('[ADMIN] Datos del formulario: usuario=%s', request.form.get('usuario', 'N/A'))
            app.logger.info('[ADMIN] CSRF token presente en form: %s', 'csrf_token' in request.form)
            app.logger.info('[ADMIN] Intentos actuales en sesión: %s', session.get('intentos_admin', 0))
            app.logger.info('[ADMIN] Session completa: %s', dict(session))
            
            # Intentar validar formulario y capturar cualquier excepción
            try:
                is_valid = form.validate_on_submit()
                app.logger.info('[ADMIN] Form.validate_on_submit() = %s', is_valid)
            except Exception as val_error:
                app.logger.error('[ADMIN] Excepción al validar formulario: %s', val_error, exc_info=True)
                flash(f'Error al validar formulario: {str(val_error)}', 'danger')
                is_valid = False
            
            if not is_valid:
                app.logger.warning('[ADMIN] Form NO válido - Errores: %s', form.errors)
                app.logger.warning('[ADMIN] Datos del request completo: %s', dict(request.form))
                for field, errors in form.errors.items():
                    for error in errors:
                        error_msg = f'Error en {field}: {error}'
                        flash(error_msg, 'danger')
                        app.logger.error('[ADMIN] %s', error_msg)
                # NO retornar aquí - dejar que continúe para mostrar errores
            else:
                app.logger.info('[ADMIN] ✅ Form válido, procesando login...')
        except Exception as e:
            app.logger.error('[ADMIN] ❌ Error al procesar POST: %s', e, exc_info=True)
            flash(f'Error al procesar el formulario: {str(e)}', 'danger')
            # Continuar para mostrar el formulario con error

    # Ahora procesar si el formulario es válido
    if request.method == 'POST' and form.validate_on_submit():
        app.logger.info('[ADMIN] POST recibido - usuario: %s', form.usuario.data if form.usuario.data else 'N/A')
        app.logger.info('[ADMIN] Form válido, procesando login...')
        try:
            usuario = form.usuario.data.strip()
            password = form.password.data.strip()
            app.logger.info('[ADMIN] Validando credenciales para: %s', usuario)
            
            if session['intentos_admin'] >= MAX_INTENTOS:
                tiempo_restante = TIMEOUT_INTENTOS - (int(time.time()) - session.get('ultimo_intento', 0))
                if tiempo_restante > 0:
                    minutos = tiempo_restante // 60
                    segundos = tiempo_restante % 60
                    msg = f"Máximo de intentos superado ({MAX_INTENTOS}). Espera {minutos}m {segundos}s antes de intentar nuevamente."
                else:
                    session['intentos_admin'] = 0
                    session['ultimo_intento'] = int(time.time())
                    msg = "Intentos reseteados. Puedes intentar nuevamente."
                flash(msg, 'danger')
                app.logger.warning(f"[ADMIN] Máximo de intentos superado ({MAX_INTENTOS}) - Intentos actuales: {session['intentos_admin']}")
                return redirect(url_for('admin'))

            conn = get_db_connection()
            cur = conn.cursor()
            # 🔍 Buscar el usuario sin limitar al rol 'admin'
            cur.execute("SELECT id, nombre, email, password, rol FROM usuarios WHERE email = %s", [usuario])
            user = cur.fetchone()
            cur.close()
            conn.close()
            
            app.logger.info('[ADMIN] Usuario encontrado: %s', 'Sí' if user else 'No')
            
            if user:
                password_valid = check_password_hash(user['password'], password)
                app.logger.info('[ADMIN] Contraseña válida: %s', password_valid)
            
            if user and check_password_hash(user['password'], password):
                # Guardar en sesión
                session['usuario_id'] = user['id']
                session['nombre'] = user['nombre']
                session['rol'] = user['rol']
                session['intentos_admin'] = 0
                session['ultimo_intento'] = int(time.time())
                session['last_activity'] = int(time.time())
                
                # Forzar que la sesión se guarde
                session.permanent = True
                session.modified = True  # CRÍTICO: Forzar guardado
                
                flash('Inicio de sesión exitoso', 'success')
                app.logger.info('[ADMIN] Usuario autenticado: %s con rol "%s" (ID: %s)', usuario, user['rol'], user['id'])
                app.logger.info('[ADMIN] Sesión ANTES de redirect - usuario_id: %s, rol: "%s"', session.get('usuario_id'), session.get('rol'))

                # 🧭 Redirigir según rol (comparación exacta)
                rol_clean = str(user['rol']).strip().lower()
                if rol_clean == 'admin':
                    app.logger.info('[ADMIN] Redirigiendo a panel de administrador')
                    # Usar make_response para asegurar que la sesión se guarde en la cookie
                    response = make_response(redirect(url_for('panel')))
                    return response
                elif rol_clean == 'base de datos':
                    app.logger.info('[ADMIN] Redirigiendo a panel de super admin BD')
                    response = make_response(redirect(url_for('super_admin_bd')))
                    return response
                else:
                    flash(f'Rol no autorizado para esta sección. Rol actual: "{user["rol"]}"', 'danger')
                    app.logger.warning(f"[ADMIN] Rol no autorizado: '{user['rol']}' (limpiado: '{rol_clean}')")
                    return redirect(url_for('admin'))
            else:
                session['intentos_admin'] = session.get('intentos_admin', 0) + 1
                session['ultimo_intento'] = int(time.time())
                session.modified = True
                msg = f"Usuario o contraseña incorrectos ({session['intentos_admin']}/{MAX_INTENTOS})"
                flash(msg, 'danger')
                app.logger.warning(f"[ADMIN] Usuario o contraseña incorrectos ({session['intentos_admin']}/{MAX_INTENTOS}): {usuario}")
                return redirect(url_for('admin'))

        except psycopg.OperationalError as oe:
            msg = f"[ADMIN] Error de conexión a la base de datos: {str(oe)}"
            flash(msg, 'danger')
            app.logger.error(msg)
            return redirect(url_for('admin'))
        except Exception as e:
            msg = f"[ADMIN] Error inesperado: {str(e)}"
            flash(msg, 'danger')
            app.logger.error(msg)
            return redirect(url_for('admin'))

    app.logger.info('[ADMIN] Acceso a la página de admin - Intentos actuales: %s/%s', 
                    session.get('intentos_admin', 0), MAX_INTENTOS)
    
    # CRÍTICO: Asegurar que la sesión se guarde antes de renderizar
    # Esto es necesario para que el token CSRF se guarde en la cookie
    session.modified = True
    
    # Crear respuesta y asegurar que la cookie de sesión se envíe
    response = make_response(render_template('admin.html', form=form, 
                         intentos_actuales=session.get('intentos_admin', 0),
                         max_intentos=MAX_INTENTOS))
    
    # Asegurar que la cookie de sesión se establezca correctamente
    # Flask debería hacer esto automáticamente, pero lo forzamos aquí
    app.logger.info('[ADMIN] Sesión antes de enviar respuesta: %s', dict(session))
    
    return response

@app.route('/admin/reset-intentos', methods=['POST'])
def admin_reset_intentos():
    """Ruta para resetear los intentos de login manualmente"""
    session['intentos_admin'] = 0
    session['ultimo_intento'] = int(time.time())
    session.modified = True
    flash('✅ Intentos de login reseteados. Puedes intentar nuevamente.', 'success')
    app.logger.info('[ADMIN] Intentos reseteados manualmente')
    return redirect(url_for('admin'))

@app.route('/super_admin_bd')
def super_admin_bd():
    # Log detallado para debugging
    app.logger.info('[SUPER_ADMIN_BD] Verificando acceso - usuario_id: %s, rol: "%s"', 
                    session.get('usuario_id'), session.get('rol'))
    
    if 'usuario_id' not in session:
        flash('Debes iniciar sesión como SUPER ADMIN BD.', 'danger')
        app.logger.warning('[SUPER_ADMIN_BD] Intento de acceso sin usuario_id en sesión')
        return redirect(url_for('admin'))
    
    rol_actual = str(session.get('rol', '')).strip().lower()
    if rol_actual != 'base de datos':
        flash(f'Debes iniciar sesión como SUPER ADMIN BD. Rol actual: "{session.get("rol")}"', 'danger')
        app.logger.warning('[SUPER_ADMIN_BD] Intento de acceso sin permisos - usuario_id: %s, rol: "%s"', 
                          session.get('usuario_id'), session.get('rol'))
        return redirect(url_for('admin'))

    app.logger.info('[SUPER_ADMIN_BD] Acceso concedido a: %s', session.get('nombre'))
    
    try:
        # Obtener estadísticas financieras
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Obtener pedidos con información financiera completa
        cur.execute("""
            SELECT 
                cp.id as numero_factura,
                cp.producto_id,
                cp.producto_titulo,
                cp.cantidad,
                cp.producto_precio as precio_final,
                pv.precio_proveedor,
                cp.monto_total as cliente_paga,
                cp.nombre,
                cp.apellido,
                cp.email,
                cp.paypal_order_id,
                cp.paypal_capture_id,
                cp.estado_pago,
                cp.afiliado_id,
                cp.afiliado_codigo,
                cp.creado_en,
                a.comision_porcentaje as comision_afiliado_pct,
                cm.comision_manual as comision_manual_activa
            FROM shopfusion.cliente_compraron_productos cp
            LEFT JOIN shopfusion.productos_vendedor pv ON cp.producto_id = pv.id
            LEFT JOIN shopfusion.afiliados a ON cp.afiliado_id = a.id
            LEFT JOIN shopfusion.comisiones_manuales_temporales cm 
                ON cp.afiliado_id = cm.afiliado_id 
                AND cm.activa = TRUE 
                AND cm.fecha_expiracion > CURRENT_TIMESTAMP
            ORDER BY cp.creado_en DESC
            LIMIT 100
        """)
        pedidos_financieros = cur.fetchall()
        
        # Calcular estadísticas financieras
        total_ventas = 0.0
        total_pago_proveedor = 0.0
        total_margen = 0.0
        total_comisiones_afiliados = 0.0
        total_ganancia_neta = 0.0
        
        for pedido in pedidos_financieros:
            cliente_paga_total = float(pedido.get('cliente_paga') or 0)
            precio_proveedor = float(pedido.get('precio_proveedor') or 0)
            cantidad = int(pedido.get('cantidad') or 1)
            precio_final_unitario = float(pedido.get('precio_final') or (cliente_paga_total / cantidad if cantidad > 0 else cliente_paga_total))
            
            # Cliente paga = precio_final * cantidad (puede ser diferente al monto_total si hay descuentos)
            cliente_paga = precio_final_unitario * cantidad
            pago_proveedor_total = precio_proveedor * cantidad
            margen_total = (precio_final_unitario - precio_proveedor) * cantidad
            
            # Calcular comisión del afiliado (se calcula sobre el margen, no sobre el total de venta)
            comision_afiliado = 0.0
            if pedido.get('afiliado_id'):
                comision_pct = float(pedido.get('comision_manual_activa') or pedido.get('comision_afiliado_pct') or 50.0)
                # La comisión se calcula sobre el margen (precio_final - precio_proveedor)
                comision_afiliado = (margen_total * comision_pct) / 100
            
            # Ganancia neta = margen - comisión del afiliado
            ganancia_neta = margen_total - comision_afiliado
            
            total_ventas += cliente_paga
            total_pago_proveedor += pago_proveedor_total
            total_margen += margen_total
            total_comisiones_afiliados += comision_afiliado
            total_ganancia_neta += ganancia_neta
        
        # Obtener pagos pendientes para afiliados
        cur.execute("""
            SELECT 
                ca.id,
                ca.afiliado_id,
                a.nombre as afiliado_nombre,
                a.email as afiliado_email,
                a.codigo_afiliado,
                ca.compra_id,
                cp.producto_titulo,
                cp.monto_total as monto_venta,
                ca.comision_porcentaje,
                ca.monto_comision,
                ca.estado,
                ca.fecha_comision,
                cp.creado_en as fecha_compra
            FROM shopfusion.comisiones_afiliados ca
            JOIN shopfusion.afiliados a ON ca.afiliado_id = a.id
            JOIN shopfusion.cliente_compraron_productos cp ON ca.compra_id = cp.id
            WHERE ca.estado = 'pendiente'
            ORDER BY ca.fecha_comision DESC
        """)
        pagos_pendientes = cur.fetchall()
        
        # Calcular total de pagos pendientes
        total_pagos_pendientes = sum(float(p.get('monto_comision') or 0) for p in pagos_pendientes)
        
        cur.close()
        conn.close()
        
        return render_template('superAdmin_bd.html', 
                             nombre=session.get('nombre'),
                             pedidos_financieros=pedidos_financieros,
                             estadisticas={
                                 'total_ventas': total_ventas,
                                 'total_pago_proveedor': total_pago_proveedor,
                                 'total_margen': total_margen,
                                 'total_comisiones_afiliados': total_comisiones_afiliados,
                                 'total_ganancia_neta': total_ganancia_neta,
                                 'total_pagos_pendientes': total_pagos_pendientes,
                                 'cantidad_pagos_pendientes': len(pagos_pendientes)
                             },
                             pagos_pendientes=pagos_pendientes)
    except Exception as e:
        app.logger.error(f'[SUPER_ADMIN_BD] Error al cargar datos: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return render_template('superAdmin_bd.html', 
                             nombre=session.get('nombre'),
                             pedidos_financieros=[],
                             estadisticas={
                                 'total_ventas': 0,
                                 'total_pago_proveedor': 0,
                                 'total_margen': 0,
                                 'total_comisiones_afiliados': 0,
                                 'total_ganancia_neta': 0,
                                 'total_pagos_pendientes': 0,
                                 'cantidad_pagos_pendientes': 0
                             },
                             pagos_pendientes=[])


@app.route('/api/comisiones/<int:comision_id>/marcar_pagado', methods=['POST'])
def marcar_comision_pagada(comision_id):
    """Marcar una comisión de afiliado como pagada"""
    if 'usuario_id' not in session or session.get('rol') != 'base de datos':
        return jsonify({'error': 'Acceso no autorizado'}), 403
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar que la comisión existe y está pendiente
        cur.execute("""
            SELECT id, estado, afiliado_id 
            FROM shopfusion.comisiones_afiliados 
            WHERE id = %s
        """, (comision_id,))
        comision = cur.fetchone()
        
        if not comision:
            cur.close()
            conn.close()
            return jsonify({'error': 'Comisión no encontrada'}), 404
        
        if comision['estado'] == 'pagado':
            cur.close()
            conn.close()
            return jsonify({'error': 'Esta comisión ya está marcada como pagada'}), 400
        
        # Actualizar estado a pagado y establecer fecha_pago
        cur.execute("""
            UPDATE shopfusion.comisiones_afiliados
            SET estado = 'pagado',
                fecha_pago = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (comision_id,))
        
        # Actualizar total_pagado del afiliado
        cur.execute("""
            UPDATE shopfusion.afiliados
            SET total_pagado = total_pagado + (
                SELECT monto_comision 
                FROM shopfusion.comisiones_afiliados 
                WHERE id = %s
            )
            WHERE id = %s
        """, (comision_id, comision['afiliado_id']))
        
        conn.commit()
        cur.close()
        conn.close()
        
        app.logger.info(f'[MARCAR_COMISION_PAGADA] Comisión {comision_id} marcada como pagada')
        return jsonify({'success': True, 'message': 'Comisión marcada como pagada correctamente'})
        
    except Exception as e:
        app.logger.error(f'[MARCAR_COMISION_PAGADA] Error: {e}')
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': f'Error al marcar comisión como pagada: {str(e)}'}), 500


@app.route('/api/db_overview')
def db_overview():
    if 'usuario_id' not in session or session.get('rol') != 'base de datos':
        return jsonify({'error': 'Acceso no autorizado'}), 403

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Obtener todas las tablas del esquema público
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public'
            ORDER BY table_name;
        """)
        tablas = cur.fetchall()

        resultado = []
        tablas_permitidas = obtener_tablas_permitidas()
        
        for t in tablas:
            nombre_tabla = t['table_name']
            # Validar nombre de tabla para prevenir SQL Injection
            if not validar_nombre_tabla(nombre_tabla) or nombre_tabla not in tablas_permitidas:
                continue
            
            # Usar psycopg.sql.Identifier para prevenir SQL Injection
            cur.execute(sql.SQL("SELECT * FROM {} LIMIT 10").format(sql.Identifier(nombre_tabla)))
            registros = cur.fetchall()
            columnas = list(registros[0].keys()) if registros else []

            resultado.append({
                'nombre': nombre_tabla,
                'columnas': columnas,
                'registros': registros
            })

        cur.close()
        conn.close()
        return jsonify({'tablas': resultado})

    except Exception as e:
        app.logger.error(f"[DB_OVERVIEW] Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/run_sql', methods=['POST'])
def run_sql():
    """
    ⚠️ RUTA PELIGROSA: Solo para super admin BD
    Permite ejecutar SQL arbitrario pero con validaciones mínimas
    """
    if 'usuario_id' not in session or session.get('rol') != 'base de datos':
        return jsonify({'error': 'Acceso no autorizado'}), 403

    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        if not query:
            return jsonify({'error': 'La consulta está vacía.'}), 400
        
        # ⚠️ SEGURIDAD: Bloquear comandos peligrosos
        query_upper = query.upper()
        comandos_peligrosos = ['DROP', 'TRUNCATE', 'ALTER', 'CREATE', 'GRANT', 'REVOKE', 
                              'DELETE', 'UPDATE', 'INSERT', 'COPY', '\\copy']
        for cmd in comandos_peligrosos:
            if cmd in query_upper:
                app.logger.warning(f"[RUN_SQL] Intento de ejecutar comando peligroso: {cmd}")
                return jsonify({'error': f'Comando no permitido: {cmd}'}), 403
        
        # Solo permitir SELECT para esta ruta
        if not query_upper.strip().startswith('SELECT'):
            return jsonify({'error': 'Solo se permiten consultas SELECT en esta ruta'}), 403

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Ejecutar con límite de tiempo (opcional, requiere configuración adicional)
        cur.execute(query)

        # Si hay resultados (ej: SELECT)
        if cur.description:
            columnas = [desc[0] for desc in cur.description]
            filas = [dict(zip(columnas, row)) for row in cur.fetchall()]
            resultado = filas
        else:
            # No debería llegar aquí por la validación, pero por si acaso
            conn.commit()
            resultado = []

        cur.close()
        conn.close()
        return jsonify({'result': resultado})

    except Exception as e:
        # No exponer detalles del error al cliente
        app.logger.error(f"[RUN_SQL] Error: {str(e)}")
        return jsonify({'error': 'Error al ejecutar la consulta'}), 500

@app.route('/api/get_tables')
def get_tables():
    if 'usuario_id' not in session or session.get('rol') != 'base de datos':
        return jsonify({'error': 'Acceso no autorizado'}), 403

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public' 
            ORDER BY table_name;
        """)
        tablas = [r['table_name'] for r in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify({'tablas': tablas})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_table/<tabla>')
def get_table(tabla):
    if 'usuario_id' not in session or session.get('rol') != 'base de datos':
        return jsonify({'error': 'Acceso no autorizado'}), 403

    # Validar nombre de tabla
    if not validar_nombre_tabla(tabla) or tabla not in obtener_tablas_permitidas():
        return jsonify({'error': 'Tabla no válida o no permitida'}), 400

    try:
        # Parámetros de paginación
        page = int(request.args.get('page', 1))
        per_page = 10  # 👈 cantidad de registros por página
        offset = (page - 1) * per_page

        conn = get_db_connection()
        cur = conn.cursor()

        # Contar total de registros usando sql.Identifier
        cur.execute(
            sql.SQL("SELECT COUNT(*) AS total FROM {}").format(sql.Identifier(tabla))
        )
        total = cur.fetchone()['total']
        total_pages = (total // per_page) + (1 if total % per_page else 0)

        # Obtener registros limitados usando sql.Identifier
        cur.execute(
            sql.SQL("SELECT * FROM {} ORDER BY id DESC LIMIT %s OFFSET %s").format(sql.Identifier(tabla)),
            (per_page, offset)
        )
        rows = cur.fetchall()
        columnas = list(rows[0].keys()) if rows else []

        cur.close()
        conn.close()

        return jsonify({
            'columnas': columnas,
            'registros': rows,
            'pagina_actual': page,
            'paginas_totales': total_pages,
            'total_registros': total
        })
    except Exception as e:
        app.logger.error(f"[GET_TABLE] Error: {str(e)}")
        return jsonify({'error': 'Error al obtener datos'}), 500

@app.route('/api/update_record/<tabla>', methods=['POST'])
def update_record(tabla):
    if 'usuario_id' not in session or session.get('rol') != 'base de datos':
        return jsonify({'error': 'Acceso no autorizado'}), 403

    # Validar nombre de tabla
    if not validar_nombre_tabla(tabla) or tabla not in obtener_tablas_permitidas():
        return jsonify({'error': 'Tabla no válida o no permitida'}), 400

    try:
        data = request.get_json()
        id_col = data.get('id_col')
        id_val = data.get('id_val')
        cambios = data.get('cambios', {})

        if not id_col or not id_val or not cambios:
            return jsonify({'error': 'Datos incompletos'}), 400

        # Validar nombre de columna
        if not validar_nombre_columna(id_col):
            return jsonify({'error': 'Nombre de columna inválido'}), 400

        # Validar todas las columnas en cambios
        for col in cambios.keys():
            if not validar_nombre_columna(col):
                return jsonify({'error': f'Nombre de columna inválido: {col}'}), 400

        # Construir query de forma segura
        conn = get_db_connection()
        cur = conn.cursor()
        
        set_parts = [sql.SQL("{} = %s").format(sql.Identifier(k)) for k in cambios.keys()]
        values = list(cambios.values()) + [id_val]

        cur.execute(
            sql.SQL("UPDATE {} SET {} WHERE {} = %s").format(
                sql.Identifier(tabla),
                sql.SQL(", ").join(set_parts),
                sql.Identifier(id_col)
            ),
            values
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'mensaje': 'Registro actualizado correctamente'})
    except Exception as e:
        app.logger.error(f"[UPDATE_RECORD] Error: {str(e)}")
        return jsonify({'error': 'Error al actualizar registro'}), 500


@app.route('/api/delete_record/<tabla>', methods=['POST'])
def delete_record(tabla):
    if 'usuario_id' not in session or session.get('rol') != 'base de datos':
        return jsonify({'error': 'Acceso no autorizado'}), 403

    # Validar nombre de tabla
    if not validar_nombre_tabla(tabla) or tabla not in obtener_tablas_permitidas():
        return jsonify({'error': 'Tabla no válida o no permitida'}), 400

    try:
        data = request.get_json()
        id_col = data.get('id_col')
        id_val = data.get('id_val')

        if not id_col or not id_val:
            return jsonify({'error': 'Datos incompletos'}), 400

        # Validar nombre de columna
        if not validar_nombre_columna(id_col):
            return jsonify({'error': 'Nombre de columna inválido'}), 400

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            sql.SQL("DELETE FROM {} WHERE {} = %s").format(
                sql.Identifier(tabla),
                sql.Identifier(id_col)
            ),
            [id_val]
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'mensaje': 'Registro eliminado correctamente'})
    except Exception as e:
        app.logger.error(f"[DELETE_RECORD] Error: {str(e)}")
        return jsonify({'error': 'Error al eliminar registro'}), 500


@app.route('/api/insert_record/<tabla>', methods=['POST'])
def insert_record(tabla):
    if 'usuario_id' not in session or session.get('rol') != 'base de datos':
        return jsonify({'error': 'Acceso no autorizado'}), 403

    # Validar nombre de tabla
    if not validar_nombre_tabla(tabla) or tabla not in obtener_tablas_permitidas():
        return jsonify({'error': 'Tabla no válida o no permitida'}), 400

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Datos vacíos'}), 400

        # Validar todas las columnas
        for col in data.keys():
            if not validar_nombre_columna(col):
                return jsonify({'error': f'Nombre de columna inválido: {col}'}), 400

        valores = list(data.values())
        columnas_identifiers = [sql.Identifier(col) for col in data.keys()]
        placeholders = ', '.join(['%s'] * len(valores))

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                sql.Identifier(tabla),
                sql.SQL(', ').join(columnas_identifiers),
                sql.SQL(placeholders)
            ),
            valores
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'mensaje': 'Registro insertado correctamente'})
    except Exception as e:
        app.logger.error(f"[INSERT_RECORD] Error: {str(e)}")
        return jsonify({'error': 'Error al insertar registro'}), 500

@app.route('/api/create_table', methods=['POST'])
def create_table():
    if 'usuario_id' not in session or session.get('rol') != 'base de datos':
        return jsonify({'error': 'Acceso no autorizado'}), 403
    if is_production and not ENABLE_DB_ADMIN:
        return jsonify({'error': 'Operación deshabilitada en producción'}), 403
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        columnas = data.get('columnas', {})
        if not validar_nombre_tabla(nombre):
            return jsonify({'error': 'Nombre de tabla inválido'}), 400
        defs_parts = []
        for col, tipo in columnas.items():
            if not validar_nombre_columna(col):
                return jsonify({'error': f'Nombre de columna inválido: {col}'}), 400
            if not validar_tipo_columna(tipo):
                return jsonify({'error': f'Tipo de columna inválido: {col}'}), 400
            defs_parts.append(f"{col} {tipo}")
        if not defs_parts:
            return jsonify({'error': 'No se definieron columnas válidas'}), 400
        defs = ', '.join(defs_parts)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(sql.SQL("CREATE TABLE {} ({})").format(
            sql.Identifier(nombre),
            sql.SQL(defs)
        ))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'mensaje': f"Tabla '{nombre}' creada correctamente."})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/drop_table', methods=['POST'])
def drop_table():
    if 'usuario_id' not in session or session.get('rol') != 'base de datos':
        return jsonify({'error': 'Acceso no autorizado'}), 403
    if is_production and not ENABLE_DB_ADMIN:
        return jsonify({'error': 'Operación deshabilitada en producción'}), 403
    try:
        data = request.get_json()
        nombre = data.get('nombre')
        if not validar_nombre_tabla(nombre):
            return jsonify({'error': 'Nombre de tabla inválido'}), 400
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE;").format(sql.Identifier(nombre)))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'mensaje': f"Tabla '{nombre}' eliminada correctamente."})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/panel', methods=['GET', 'POST'])
def panel():
    # Log detallado para debugging
    app.logger.info('[PANEL] Verificando acceso - usuario_id: %s, rol: "%s"', 
                    session.get('usuario_id'), session.get('rol'))
    
    if 'usuario_id' not in session:
        flash('Debes iniciar sesión como administrador.', 'danger')
        app.logger.warning('[PANEL] Intento de acceso sin usuario_id en sesión')
        return redirect(url_for('admin'))
    
    rol_actual = str(session.get('rol', '')).strip().lower()
    if rol_actual != 'admin':
        flash(f'Debes iniciar sesión como administrador. Rol actual: "{session.get("rol")}"', 'danger')
        app.logger.warning('[PANEL] Intento de acceso sin permisos - usuario_id: %s, rol: "%s"', 
                          session.get('usuario_id'), session.get('rol'))
        return redirect(url_for('admin'))
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, nombre, email, mensaje, created_at, leido, atendido, urgente FROM sugerencias ORDER BY created_at DESC")
        sugerencias = cur.fetchall()
        cur.close()
        conn.close()
        app.logger.info('[PANEL] Sugerencias cargadas correctamente')

        # Cargar tickets de soporte
        conn = get_db_connection()
        ensure_soporte_table(conn)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, nombre, email, mensaje, estado, creado_en
                FROM shopfusion.tickets_soporte
                ORDER BY creado_en DESC
            """)
            tickets_soporte = cur.fetchall()
        conn.close()

                        # Obtener sorteos existentes
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT s.id, s.titulo, s.descripcion, s.imagen,
                   COALESCE(b.cnt, 0) AS total_boletos
            FROM sorteos s
            LEFT JOIN (
                SELECT sorteo_id, COUNT(*) AS cnt
                FROM boletos
                GROUP BY sorteo_id
            ) b ON b.sorteo_id = s.id
            ORDER BY s.id DESC
        """)
        sorteos = cur.fetchall()
        cur.close()
        conn.close()

        # Crear formulario de sorteos
        form_sorteo = SorteoForm()

        # Cargar productos exclusivos
        productos_exclusivos = obtener_productos_exclusivos_admin(limit=None)
        productos_bajo_stock = [
            p for p in (productos_exclusivos or [])
            if (p.get('stock') or 0) <= STOCK_BAJO_UMBRAL
        ]
        
        # Cargar afiliados para gestión de comisiones (con comisiones manuales temporales)
        conn = get_db_connection()
        cur = conn.cursor()
        pagos_en_afiliados = afiliados_pago_columns_exist(conn)
        pagos_table = afiliados_pagos_table_exists(conn) if not pagos_en_afiliados else False
        if pagos_en_afiliados:
            cur.execute("""
                SELECT a.id, a.nombre, a.email, a.codigo_afiliado, a.comision_porcentaje, 
                       a.total_ganancias, a.total_pagado, a.total_ventas, a.estado, a.creado_en,
                       a.pais, a.metodo_pago, a.banco, a.numero_cuenta, a.titular_cuenta,
                       a.paypal_email, a.skrill_email, a.frecuencia_pago,
                       cmt.comision_manual as comision_manual_activa,
                       cmt.fecha_expiracion as comision_manual_expiracion,
                       cmt.activa as tiene_comision_manual
                FROM shopfusion.afiliados a
                LEFT JOIN shopfusion.comisiones_manuales_temporales cmt 
                    ON a.id = cmt.afiliado_id AND cmt.activa = TRUE
                ORDER BY a.creado_en DESC
            """)
        elif pagos_table:
            cur.execute("""
                SELECT a.id, a.nombre, a.email, a.codigo_afiliado, a.comision_porcentaje, 
                       a.total_ganancias, 0::numeric as total_pagado, a.total_ventas, a.estado, a.creado_en,
                       ap.pais, ap.metodo_pago, ap.banco, ap.numero_cuenta, ap.titular_cuenta,
                       ap.paypal_email, ap.skrill_email, ap.frecuencia_pago,
                       cmt.comision_manual as comision_manual_activa,
                       cmt.fecha_expiracion as comision_manual_expiracion,
                       cmt.activa as tiene_comision_manual
                FROM shopfusion.afiliados a
                LEFT JOIN shopfusion.afiliados_pagos ap ON a.id = ap.afiliado_id
                LEFT JOIN shopfusion.comisiones_manuales_temporales cmt 
                    ON a.id = cmt.afiliado_id AND cmt.activa = TRUE
                ORDER BY a.creado_en DESC
            """)
        else:
            cur.execute("""
                SELECT a.id, a.nombre, a.email, a.codigo_afiliado, a.comision_porcentaje, 
                       a.total_ganancias, a.total_ventas, a.estado, a.creado_en,
                       0::numeric as total_pagado,
                       NULL as pais, NULL as metodo_pago, NULL as banco, NULL as numero_cuenta,
                       NULL as titular_cuenta, NULL as paypal_email, NULL as skrill_email,
                       NULL as frecuencia_pago,
                       cmt.comision_manual as comision_manual_activa,
                       cmt.fecha_expiracion as comision_manual_expiracion,
                       cmt.activa as tiene_comision_manual
                FROM shopfusion.afiliados a
                LEFT JOIN shopfusion.comisiones_manuales_temporales cmt 
                    ON a.id = cmt.afiliado_id AND cmt.activa = TRUE
                ORDER BY a.creado_en DESC
            """)
        afiliados = cur.fetchall()
        for af in afiliados:
            af['total_ganancias'] = float(af.get('total_ganancias') or 0)
            af['total_pagado'] = float(af.get('total_pagado') or 0)
            af['saldo_pendiente'] = max(af['total_ganancias'] - af['total_pagado'], 0)
        
        # Obtener comisión predeterminada del sistema
        cur.execute("""
            SELECT valor FROM shopfusion.configuracion_sistema
            WHERE clave = 'comision_predeterminada'
        """)
        resultado = cur.fetchone()
        comision_predeterminada = float(resultado['valor']) if resultado else 50.0
        
        cur.close()
        conn.close()

        # Cargar vacantes
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, titulo, descripcion, requisitos, activa, creado_en
            FROM shopfusion.vacantes
            ORDER BY creado_en DESC
        """)
        vacantes = cur.fetchall()
        cur.close()
        conn.close()

        # Cargar pedidos/compras
        conn = get_db_connection()
        cur = conn.cursor()
        has_link_proveedor = link_proveedor_column_exists(conn)
        columnas_ok = ensure_estado_entrega_columns(conn)
        columnas_entrega_disponibles = columnas_ok or has_estado_entrega_columns(conn)
        columnas_envio = ensure_compras_envio_columns(conn)
        has_envio_cols = columnas_envio and all(
            col in columnas_envio for col in (
                'provincia', 'ciudad', 'tipo_identificacion', 'numero_identificacion'
            )
        )
        env_tipo_expr = "COALESCE(d.tipo_identificacion, c.tipo_identificacion, '')" if has_envio_cols else "COALESCE(d.tipo_identificacion, '')"
        env_num_expr = "COALESCE(d.numero_identificacion, c.numero_identificacion, '')" if has_envio_cols else "COALESCE(d.numero_identificacion, '')"
        env_prov_expr = "COALESCE(d.provincia, c.provincia, '')" if has_envio_cols else "COALESCE(d.provincia, '')"
        env_ciudad_expr = "COALESCE(d.ciudad, c.ciudad, '')" if has_envio_cols else "COALESCE(d.ciudad, '')"
        env_tipo_fallback = "COALESCE(d.tipo_identificacion, c.tipo_identificacion, '')" if has_envio_cols else "COALESCE(d.tipo_identificacion, '')"
        env_num_fallback = "COALESCE(d.numero_identificacion, c.numero_identificacion, '')" if has_envio_cols else "COALESCE(d.numero_identificacion, '')"
        env_prov_fallback = "COALESCE(d.provincia, c.provincia, '')" if has_envio_cols else "COALESCE(d.provincia, '')"
        env_ciudad_fallback = "COALESCE(d.ciudad, c.ciudad, '')" if has_envio_cols else "COALESCE(d.ciudad, '')"
        entregas_ok = ensure_pedidos_entregas_table(conn)
        if has_link_proveedor and columnas_entrega_disponibles:
            cur.execute(f"""
                SELECT
                    c.id as numero_factura,
                    c.producto_id,
                    c.producto_titulo,
                    c.producto_precio,
                    c.cantidad,
                    c.nombre,
                    c.apellido,
                    c.email,
                    COALESCE(d.telefono, c.telefono) AS telefono,
                    'Ecuador' as pais,
                    COALESCE(d.direccion, c.direccion) AS direccion,
                    {env_prov_expr} AS envio_provincia,
                    {env_ciudad_expr} AS envio_ciudad,
                    {env_tipo_expr} AS envio_tipo_identificacion,
                    {env_num_expr} AS envio_numero_identificacion,
                    c.paypal_order_id,
                    c.paypal_capture_id,
                    c.monto_total,
                    c.moneda,
                    c.estado_pago,
                    COALESCE(c.estado_entrega, pe.entregado::text) AS estado_entrega,
                    COALESCE(c.fecha_entrega, pe.fecha_entregado) AS fecha_entrega,
                    COALESCE(pe.entregado, FALSE) AS entregado,
                    COALESCE(d.nombre, c.nombre) AS nombre_envio,
                    COALESCE(d.apellido, c.apellido) AS apellido_envio,
                    {env_tipo_expr} AS envio_tipo_identificacion,
                    {env_num_expr} AS envio_numero_identificacion,
                    {env_prov_expr} AS envio_provincia,
                    {env_ciudad_expr} AS envio_ciudad,
                    COALESCE(d.telefono, c.telefono) AS telefono_envio,
                    COALESCE(d.direccion, c.direccion) AS direccion_envio,
                    c.afiliado_id,
                    c.afiliado_codigo,
                    c.creado_en,
                    pv.link_proveedor
                FROM shopfusion.cliente_compraron_productos c
                LEFT JOIN shopfusion.productos_vendedor pv
                    ON pv.id = c.producto_id
                LEFT JOIN shopfusion.pedidos_entregas pe
                    ON pe.pedido_id = c.id
                LEFT JOIN shopfusion.usuarios u ON u.email = c.email
                LEFT JOIN shopfusion.datos_envio_clientes d ON d.usuario_id = u.id
                ORDER BY c.creado_en DESC
                LIMIT 100
            """)
        elif columnas_entrega_disponibles:
            cur.execute(f"""
                SELECT
                    id as numero_factura,
                    producto_id,
                    producto_titulo,
                    producto_precio,
                    cantidad,
                    nombre,
                    apellido,
                    email,
                    COALESCE(d.telefono, telefono) AS telefono,
                    'Ecuador' as pais,
                    COALESCE(d.direccion, direccion) AS direccion,
                    {env_prov_expr} AS envio_provincia,
                    {env_ciudad_expr} AS envio_ciudad,
                    {env_tipo_expr} AS envio_tipo_identificacion,
                    {env_num_expr} AS envio_numero_identificacion,
                    paypal_order_id,
                    paypal_capture_id,
                    monto_total,
                    moneda,
                    estado_pago,
                    COALESCE(estado_entrega, CASE WHEN pe.entregado THEN 'entregado' ELSE 'pendiente' END) AS estado_entrega,
                    COALESCE(fecha_entrega, pe.fecha_entregado) AS fecha_entrega,
                    COALESCE(pe.entregado, FALSE) AS entregado,
                    COALESCE(d.nombre, nombre) AS nombre_envio,
                    COALESCE(d.apellido, apellido) AS apellido_envio,
                    {env_tipo_expr} AS envio_tipo_identificacion,
                    {env_num_expr} AS envio_numero_identificacion,
                    {env_prov_expr} AS envio_provincia,
                    {env_ciudad_expr} AS envio_ciudad,
                    COALESCE(d.telefono, telefono) AS telefono_envio,
                    COALESCE(d.direccion, direccion) AS direccion_envio,
                    afiliado_id,
                    afiliado_codigo,
                    creado_en,
                    NULL as link_proveedor
                FROM shopfusion.cliente_compraron_productos
                LEFT JOIN shopfusion.pedidos_entregas pe
                    ON pe.pedido_id = id
                LEFT JOIN shopfusion.usuarios u ON u.email = email
                LEFT JOIN shopfusion.datos_envio_clientes d ON d.usuario_id = u.id
                ORDER BY creado_en DESC
                LIMIT 100
            """)
        else:
            # Fallback sin columnas de entrega (permiso insuficiente)
            app.logger.warning('[PEDIDOS] Mostrando pedidos sin columnas de entrega (permiso insuficiente para ALTER)')
            if has_link_proveedor:
                cur.execute(f"""
                    SELECT 
                        c.id as numero_factura,
                        c.producto_id,
                        c.producto_titulo,
                        c.producto_precio,
                        c.cantidad,
                        c.nombre,
                        c.apellido,
                        c.email,
                        c.telefono,
                        c.pais,
                        c.direccion,
                        c.paypal_order_id,
                        c.paypal_capture_id,
                        c.monto_total,
                        c.moneda,
                        c.estado_pago,
                        CASE WHEN pe.entregado THEN 'entregado' ELSE 'pendiente' END AS estado_entrega,
                        pe.fecha_entregado AS fecha_entrega,
                        COALESCE(pe.entregado, FALSE) AS entregado,
                        {env_tipo_fallback} AS envio_tipo_identificacion,
                        {env_num_fallback} AS envio_numero_identificacion,
                        {env_prov_fallback} AS envio_provincia,
                        {env_ciudad_fallback} AS envio_ciudad,
                        c.telefono AS telefono_envio,
                        c.direccion AS direccion_envio,
                        c.nombre AS nombre_envio,
                        c.apellido AS apellido_envio,
                        c.afiliado_id,
                        c.afiliado_codigo,
                        c.creado_en,
                        pv.link_proveedor
                    FROM shopfusion.cliente_compraron_productos c
                    LEFT JOIN shopfusion.productos_vendedor pv
                        ON pv.id = c.producto_id
                    LEFT JOIN shopfusion.pedidos_entregas pe
                        ON pe.pedido_id = c.id
                    LEFT JOIN shopfusion.usuarios u ON u.email = c.email
                    LEFT JOIN shopfusion.datos_envio_clientes d ON d.usuario_id = u.id
                    ORDER BY c.creado_en DESC
                    LIMIT 100
                """)
            else:
                cur.execute(f"""
                    SELECT 
                        c.id as numero_factura,
                        c.producto_id,
                        c.producto_titulo,
                        c.producto_precio,
                        c.cantidad,
                        c.nombre,
                        c.apellido,
                        c.email,
                        COALESCE(d.telefono, c.telefono) AS telefono,
                        c.pais,
                        COALESCE(d.direccion, c.direccion) AS direccion,
                        c.paypal_order_id,
                        c.paypal_capture_id,
                        c.monto_total,
                        c.moneda,
                        c.estado_pago,
                        CASE WHEN pe.entregado THEN 'entregado' ELSE 'pendiente' END AS estado_entrega,
                        pe.fecha_entregado AS fecha_entrega,
                        COALESCE(pe.entregado, FALSE) AS entregado,
                        {env_tipo_fallback} AS envio_tipo_identificacion,
                        {env_num_fallback} AS envio_numero_identificacion,
                        {env_prov_fallback} AS envio_provincia,
                        {env_ciudad_fallback} AS envio_ciudad,
                        COALESCE(d.telefono, c.telefono) AS telefono_envio,
                        COALESCE(d.direccion, c.direccion) AS direccion_envio,
                        COALESCE(d.nombre, c.nombre) AS nombre_envio,
                        COALESCE(d.apellido, c.apellido) AS apellido_envio,
                        c.afiliado_id,
                        c.afiliado_codigo,
                        c.creado_en,
                        NULL as link_proveedor
                    FROM shopfusion.cliente_compraron_productos c
                    LEFT JOIN shopfusion.pedidos_entregas pe
                        ON pe.pedido_id = c.id
                    LEFT JOIN shopfusion.usuarios u ON u.email = c.email
                    LEFT JOIN shopfusion.datos_envio_clientes d ON d.usuario_id = u.id
                    ORDER BY c.creado_en DESC
                    LIMIT 100
                """)
        pedidos = cur.fetchall()
        cur.close()
        conn.close()

        return render_template(
            'panel.html',
            sugerencias=sugerencias,
            tickets_soporte=tickets_soporte,
            categorias=get_categorias(),
            sorteos=sorteos,
            form_sorteo=form_sorteo,
            productos_exclusivos=productos_exclusivos,
            productos_bajo_stock=productos_bajo_stock,
            stock_bajo_umbral=STOCK_BAJO_UMBRAL,
            afiliados=afiliados,
            vacantes=vacantes,
            pedidos=pedidos,
            comision_predeterminada=comision_predeterminada
        )

    except psycopg.OperationalError as oe:
        msg = f"[PANEL] Error de conexión a la base de datos: {str(oe)}"
        flash(msg, 'danger')
        app.logger.error(msg)
        form_sorteo = SorteoForm()
        return render_template('panel.html', sugerencias=[], tickets_soporte=[], categorias=get_categorias(), productos_exclusivos=[], productos_bajo_stock=[], stock_bajo_umbral=STOCK_BAJO_UMBRAL, sorteos=[], form_sorteo=form_sorteo, afiliados=[], vacantes=[], pedidos=[], comision_predeterminada=50.0)
    except Exception as e:
        msg = f"[PANEL] Error inesperado: {str(e)}"
        flash(msg, 'danger')
        app.logger.error(msg)
        form_sorteo = SorteoForm()
        return render_template('panel.html', sugerencias=[], tickets_soporte=[], categorias=get_categorias(), productos_exclusivos=[], productos_bajo_stock=[], stock_bajo_umbral=STOCK_BAJO_UMBRAL, sorteos=[], form_sorteo=form_sorteo, afiliados=[], vacantes=[], pedidos=[], comision_predeterminada=50.0)

@app.route('/admin/pedidos/<int:pedido_id>/estado-entrega', methods=['POST'])
def admin_actualizar_estado_entrega(pedido_id):
    """Permite al admin marcar un pedido como entregado/no entregado (marcar leído)."""
    if 'usuario_id' not in session or str(session.get('rol', '')).lower() != 'admin':
        flash('No autorizado', 'danger')
        return redirect(url_for('admin'))

    val = request.form.get('entregado')
    entregar = str(val).lower() in ['1', 'true', 'on', 'yes', 'entregado'] if val is not None else False
    nuevo_estado = 'entregado' if entregar else 'pendiente'

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Guardar en tabla auxiliar de entregas (sin tocar tabla base)
            ensure_pedidos_entregas_table(conn)
            if nuevo_estado == 'entregado':
                cur.execute(
                    """
                    INSERT INTO shopfusion.pedidos_entregas (pedido_id, entregado, fecha_entregado)
                    VALUES (%s, TRUE, CURRENT_TIMESTAMP)
                    ON CONFLICT (pedido_id)
                    DO UPDATE SET entregado = EXCLUDED.entregado,
                                  fecha_entregado = EXCLUDED.fecha_entregado;
                    """,
                    (pedido_id,)
                )
            else:
                cur.execute(
                    """
                    INSERT INTO shopfusion.pedidos_entregas (pedido_id, entregado, fecha_entregado)
                    VALUES (%s, FALSE, NULL)
                    ON CONFLICT (pedido_id)
                    DO UPDATE SET entregado = EXCLUDED.entregado,
                                  fecha_entregado = EXCLUDED.fecha_entregado;
                    """,
                    (pedido_id,)
                )
            conn.commit()
        flash(f'Estado de entrega actualizado a "{nuevo_estado}"', 'success')
        app.logger.info('[PEDIDOS] Pedido %s marcado como %s', pedido_id, nuevo_estado)
    except Exception as e:
        app.logger.error('[PEDIDOS] No se pudo actualizar estado de entrega: %s', e)
        flash('No se pudo actualizar el estado del pedido', 'danger')
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return redirect(url_for('panel') + '#pedidos')
@app.route('/agregar_sorteo', methods=['GET', 'POST'])
def agregar_sorteo():
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))

    form_sorteo = SorteoForm()

    if form_sorteo.validate_on_submit():
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sorteos (titulo, descripcion, imagen)
                VALUES (%s, %s, %s)
            """, (
                form_sorteo.titulo.data.strip(),
                form_sorteo.descripcion.data.strip(),
                form_sorteo.imagen.data.strip()
            ))
            conn.commit()
            cur.close()
            conn.close()
            flash('✅ Sorteo agregado correctamente.', 'success')
            return redirect(url_for('panel'))
        except Exception as e:
            flash(f"❌ Error al agregar sorteo: {e}", 'danger')
            return redirect(url_for('panel'))

    # 🔹 Si no es POST válido, recarga el panel con todo lo necesario
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, titulo, descripcion, imagen FROM sorteos ORDER BY id DESC")
        sorteos = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        sorteos = []
        flash(f"⚠️ Error al cargar datos: {e}", "danger")

    return render_template(
        'panel.html',
        sugerencias=[],
        categorias=get_categorias(),
        productos_exclusivos=[],
        productos_bajo_stock=[],
        stock_bajo_umbral=STOCK_BAJO_UMBRAL,
        sorteos=sorteos,
        form_sorteo=form_sorteo,
        afiliados=[],
        vacantes=[],
        pedidos=[],
        comision_predeterminada=50.0
    )


@app.route('/eliminar_sorteo/<int:id>')
def eliminar_sorteo(id):
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM sorteos WHERE id = %s", (id,))
        conn.commit()
        cur.close()
        conn.close()
        flash("Sorteo eliminado correctamente.", "success")
    except Exception as e:
        flash(f"Error al eliminar sorteo: {e}", "danger")
    return redirect(url_for('panel'))

@app.route('/admin/sorteos/<int:sorteo_id>/editar', methods=['GET', 'POST'])
def admin_editar_sorteo(sorteo_id):
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, titulo, descripcion, imagen FROM sorteos WHERE id = %s", (sorteo_id,))
        sorteo = cur.fetchone()
        if not sorteo:
            flash('Sorteo no encontrado.', 'danger')
            conn.close()
            return redirect(url_for('panel'))
        if request.method == 'POST':
            titulo = (request.form.get('titulo') or '').strip()
            descripcion = (request.form.get('descripcion') or '').strip()
            imagen = (request.form.get('imagen') or '').strip()
            if not titulo or not descripcion:
                flash('Título y descripción son obligatorios.', 'danger')
                conn.close()
                return redirect(url_for('admin_editar_sorteo', sorteo_id=sorteo_id))
            cur.execute("""
                UPDATE sorteos
                SET titulo = %s, descripcion = %s, imagen = %s
                WHERE id = %s
            """, (titulo, descripcion, imagen, sorteo_id))
            conn.commit()
            conn.close()
            flash('Sorteo actualizado correctamente.', 'success')
            return redirect(url_for('panel'))
        conn.close()
        return render_template('admin_editar_sorteo.html', sorteo=sorteo)
    except Exception as e:
        app.logger.error(f"[ADMIN_EDITAR_SORTEO] Error: {e}")
        flash('No se pudo editar el sorteo.', 'danger')
        return redirect(url_for('panel'))

@app.route('/admin/sorteos/<int:sorteo_id>/inscritos')
def admin_sorteo_inscritos(sorteo_id):
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, titulo, descripcion, imagen FROM sorteos WHERE id = %s", (sorteo_id,))
        sorteo = cur.fetchone()
        if not sorteo:
            conn.close()
            flash('Sorteo no encontrado.', 'danger')
            return redirect(url_for('panel'))
        cur.execute("""
            SELECT id, nombre, contacto, numero_boleto, creado_en
            FROM boletos
            WHERE sorteo_id = %s
            ORDER BY creado_en DESC
        """, (sorteo_id,))
        inscritos = cur.fetchall()
        conn.close()
        return render_template('admin_sorteo_inscritos.html', sorteo=sorteo, inscritos=inscritos)
    except Exception as e:
        app.logger.error(f"[SORTEO_INSCRITOS] Error: {e}")
        flash('No se pudieron cargar los inscritos.', 'danger')
        return redirect(url_for('panel'))


@app.route('/registrar_boleto', methods=['POST'])
def registrar_boleto():
    """
    Registra al participante después del pago y genera un número de boleto único sin sobrescribir el sorteo.
    """
    try:
        nombre = request.form['nombre'].strip()
        contacto = request.form['contacto'].strip()
        sorteo_id = request.form['sorteo_id']

        if not nombre or not contacto:
            flash("Por favor completa todos los campos.", "warning")
            return redirect(url_for('index'))

        conn = get_db_connection()
        cur = conn.cursor()

        # 👉 Número base para el primer boleto (25 será el primero)
        BASE_INICIAL = 24

        # 🔢 Obtener el último número de boleto registrado PERO SOLO DE ESTE SORTEO
        cur.execute("""
            SELECT numero_boleto
            FROM boletos
            WHERE sorteo_id = %s
            ORDER BY numero_boleto DESC
            LIMIT 1;
        """, (sorteo_id,))
        ultimo = cur.fetchone()

        if ultimo and ultimo['numero_boleto'] is not None:
            ultimo_numero = int(ultimo['numero_boleto'])
        else:
            ultimo_numero = BASE_INICIAL  # → si no hay boletos de este sorteo, empieza en 25

        nuevo_boleto = ultimo_numero + 1

        # 🧾 Insertar nuevo registro sin reemplazar nada
        cur.execute(
            """
            INSERT INTO boletos (nombre, contacto, numero_boleto, sorteo_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            (nombre, contacto, nuevo_boleto, sorteo_id)
        )

        conn.commit()
        cur.close()
        conn.close()

        # 🎉 Mensaje de éxito más descriptivo
        flash(
            f"🎟️ ¡Gracias por participar, {nombre}! "
            f"Tu número de boleto es: {nuevo_boleto}. "
            "Guárdalo. No te preocupes si lo pierdes: nosotros lo tenemos registrado "
            "y si eres el ganador te contactaremos.",
            "success"
        )

        return redirect(url_for('index', boleto=nuevo_boleto))

    except Exception as e:
        # ⚠️ Usamos 'error' para que el mensaje sí se muestre en tu template
        flash(f"❌ Error al registrar boleto: {e}", "error")
        return redirect(url_for('index'))


@app.route('/pago_confirmado', methods=['POST'])
def pago_confirmado():
    """Guarda una bandera de pago confirmado en la sesión."""
    session['pago_confirmado'] = True
    return jsonify({'status': 'ok'})




@app.route('/eliminar_sugerencia/<int:id>')
def eliminar_sugerencia(id):
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        app.logger.warning('[ELIMINAR_SUGERENCIA] Intento sin permisos')
        return redirect(url_for('admin'))
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT nombre FROM sugerencias WHERE id=%s", [id])
        sugerencia = cur.fetchone()
        cur.execute("DELETE FROM sugerencias WHERE id=%s", [id])
        conn.commit()
        cur.close()
        conn.close()
        msg = f"[ELIMINAR_SUGERENCIA] Sugerencia eliminada: {sugerencia['nombre'] if sugerencia else id}"
        flash('Sugerencia eliminada correctamente', 'success')
        app.logger.info(msg)
        return redirect(url_for('panel'))
    except psycopg.OperationalError as oe:
        msg = f"[ELIMINAR_SUGERENCIA] Error de conexión: {str(oe)}"
        flash(msg, 'danger')
        app.logger.error(msg)
        return redirect(url_for('panel'))
    except Exception as e:
        msg = f"[ELIMINAR_SUGERENCIA] Error inesperado: {str(e)}"
        flash(msg, 'danger')
        app.logger.error(msg)
        return redirect(url_for('panel'))

@app.post('/admin/soporte/<int:ticket_id>/eliminar')
def admin_eliminar_ticket(ticket_id):
    """Eliminar ticket de soporte."""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    try:
        conn = get_db_connection()
        ensure_soporte_table(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM shopfusion.tickets_soporte WHERE id = %s", (ticket_id,))
            conn.commit()
        conn.close()
        flash('Ticket eliminado correctamente.', 'success')
        return redirect(url_for('panel'))
    except Exception as e:
        app.logger.error(f"[ADMIN_ELIMINAR_TICKET] {e}")
        flash('No se pudo eliminar el ticket.', 'danger')
        return redirect(url_for('panel'))

@app.route('/marcar_sugerencia_atendida/<int:id>')
def marcar_sugerencia_atendida(id):
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        app.logger.warning('[MARCAR_SUGERENCIA_ATENDIDA] Intento sin permisos')
        return redirect(url_for('admin'))
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT nombre FROM sugerencias WHERE id=%s", [id])
        sugerencia = cur.fetchone()
        cur.execute("UPDATE sugerencias SET atendido=TRUE, leido=TRUE WHERE id=%s", [id])
        conn.commit()
        cur.close()
        conn.close()
        msg = f"[MARCAR_SUGERENCIA_ATENDIDA] Sugerencia marcada como atendida: {sugerencia['nombre'] if sugerencia else id}"
        flash('Sugerencia marcada como atendida', 'success')
        app.logger.info(msg)
        return redirect(url_for('panel'))
    except psycopg.OperationalError as oe:
        msg = f"[MARCAR_SUGERENCIA_ATENDIDA] Error de conexión: {str(oe)}"
        flash(msg, 'danger')
        app.logger.error(msg)
        return redirect(url_for('panel'))
    except Exception as e:
        msg = f"[MARCAR_SUGERENCIA_ATENDIDA] Error inesperado: {str(e)}"
        flash(msg, 'danger')
        app.logger.error(msg)
        return redirect(url_for('panel'))

@app.route('/marcar_sugerencia_urgente/<int:id>')
def marcar_sugerencia_urgente(id):
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        app.logger.warning('[MARCAR_SUGERENCIA_URGENTE] Intento sin permisos')
        return redirect(url_for('admin'))
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT nombre, urgente FROM sugerencias WHERE id=%s", [id])
        sugerencia = cur.fetchone()
        nuevo_estado = not sugerencia['urgente'] if sugerencia else False
        cur.execute("UPDATE sugerencias SET urgente=%s, leido=TRUE WHERE id=%s", [nuevo_estado, id])
        conn.commit()
        cur.close()
        conn.close()
        msg = f"[MARCAR_SUGERENCIA_URGENTE] Sugerencia marcada como {'urgente' if nuevo_estado else 'no urgente'}: {sugerencia['nombre'] if sugerencia else id}"
        flash(f"Sugerencia marcada como {'urgente' if nuevo_estado else 'no urgente'}", 'success')
        app.logger.info(msg)
        return redirect(url_for('panel'))
    except psycopg.OperationalError as oe:
        msg = f"[MARCAR_SUGERENCIA_URGENTE] Error de conexión: {str(oe)}"
        flash(msg, 'danger')
        app.logger.error(msg)
        return redirect(url_for('panel'))
    except Exception as e:
        msg = f"[MARCAR_SUGERENCIA_URGENTE] Error inesperado: {str(e)}"
        flash(msg, 'danger')
        app.logger.error(msg)
        return redirect(url_for('panel'))

@app.route('/usuario')
def usuario():
    if 'usuario_id' not in session:
        msg = "[USUARIO] Intento de acceso sin iniciar sesión"
        flash('Debes iniciar sesión primero', 'danger')
        app.logger.warning(msg)
        return redirect(url_for('login'))
    
    usuario_id = session.get('usuario_id')
    usuario_email = session.get('email') or None
    paypal_email_session = session.get('ultima_paypal_email')
    
    # Obtener información del usuario de la BD
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Obtener email del usuario si no está en sesión
            if not usuario_email:
                cur.execute("SELECT email FROM usuarios WHERE id = %s", (usuario_id,))
                usuario_data = cur.fetchone()
                if usuario_data:
                    usuario_email = usuario_data.get('email')
                    session['email'] = usuario_email
            
            # Obtener compras del cliente por email (cuenta o el ·ltimo email usado en PayPal)
            compras = []
            emails_busqueda = []
            if usuario_email:
                emails_busqueda.append(usuario_email)
            if paypal_email_session and paypal_email_session not in emails_busqueda:
                emails_busqueda.append(paypal_email_session)

            if emails_busqueda:
                cur.execute("""
                    SELECT 
                        id,
                        producto_id,
                        producto_titulo,
                        producto_precio,
                        cantidad,
                        monto_total,
                        moneda,
                        estado_pago,
                        COALESCE(creado_en, CURRENT_TIMESTAMP) as fecha_compra,
                        nombre,
                        apellido,
                        paypal_order_id
                    FROM shopfusion.cliente_compraron_productos
                    WHERE email = ANY(%s)
                    ORDER BY COALESCE(creado_en, CURRENT_TIMESTAMP) DESC
                    LIMIT 50
                """, (emails_busqueda,))
                compras = cur.fetchall()
    except Exception as e:
        app.logger.error(f"[USUARIO] Error al obtener datos: {e}")
        compras = []
    finally:
        conn.close()
    
    app.logger.info('[USUARIO] Acceso: %s', session.get('nombre'))
    return render_template('usuario.html', 
                         nombre=session.get('nombre'),
                         compras=compras)

@app.route('/select-usuario-tipo')
def select_usuario_tipo():
    """Página de selección de tipo de usuario para registro/login"""
    return render_template('select_usuario_tipo.html')

@app.route('/carrito')
def carrito():
    """Ruta para el carrito de compras - BD para clientes, cookies para visitantes y afiliados"""
    from flask import g
    
    # Verificar si es usuario autenticado (cliente o afiliado)
    usuario_id = None
    es_afiliado = False
    
    if hasattr(g, 'current_user') and g.current_user:
        usuario_id = g.current_user['usuario_id']
    elif 'usuario_id' in session and session.get('rol') == 'cliente':
        usuario_id = session.get('usuario_id')
    elif session.get('afiliado_auth') and 'afiliado_id' in session:
        es_afiliado = True
    
    if usuario_id:
        # Cliente autenticado: obtener carrito desde BD
        app.logger.info(f"[CARRITO] Usuario cliente autenticado detectado: {usuario_id}")
        carrito_items = obtener_carrito_usuario(usuario_id)
    elif es_afiliado:
        # Afiliado autenticado: obtener carrito desde BD
        afiliado_id = session.get('afiliado_id')
        app.logger.info(f"[CARRITO] Afiliado autenticado detectado: {afiliado_id}")
        carrito_items = obtener_carrito_afiliado(afiliado_id)
        if isinstance(carrito_items, dict) and carrito_items.get('error') == 'Operación no permitida: los afiliados no pueden comprar productos':
            # Forzar logout silencioso y redirigir al login de afiliados
            session.pop('afiliado_id', None)
            session.pop('afiliado_nombre', None)
            session.pop('afiliado_codigo', None)
            session.pop('afiliado_email', None)
            session.pop('afiliado_comision', None)
            session.pop('afiliado_auth', None)
            session.modified = True
            app.logger.info('[SECURITY] Afiliado forzado a cerrar sesión por operación no permitida')
            return redirect(url_for('afiliados_login'))
        # Limpiar carrito de cookies si existe
        if 'carrito' in session:
            session.pop('carrito', None)
            session.modified = True
    else:
        # Visitante: usar cookies (con límite de $50)
        carrito_items = session.get('carrito', [])
    
    # Obtener información completa de productos desde BD
    productos_completos = []
    if carrito_items:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                for item in carrito_items:
                    producto_id = item.get('producto_id')
                    if producto_id:
                        cur.execute("""
                            SELECT id, titulo, descripcion, precio, precio_oferta, 
                                   categoria, imagenes, stock, estado
                            FROM productos_vendedor
                            WHERE id = %s AND estado = 'activo' AND stock > 0
                        """, (producto_id,))
                        producto = cur.fetchone()
                        if producto:
                            # Parsear imágenes
                            imagenes = producto.get('imagenes', '[]')
                            if isinstance(imagenes, str):
                                try:
                                    imagenes = json.loads(imagenes) if imagenes.startswith('[') else [imagenes]
                                except:
                                    imagenes = [imagenes] if imagenes else []
                            elif not isinstance(imagenes, list):
                                imagenes = []
                            # Si existe un precio guardado en el carrito, úsalo (afiliados/clientes); si no, usa el vigente
                            precio_guardado = item.get('precio')
                            if precio_guardado is not None:
                                precio_final = float(precio_guardado or 0)
                            else:
                                precio_final = float(producto.get('precio_oferta') or producto.get('precio') or 0)
                            productos_completos.append({
                                'producto_id': producto['id'],
                                'nombre': producto['titulo'],
                                'descripcion': producto.get('descripcion', ''),
                                'categoria': producto.get('categoria', 'General'),
                                'precio': precio_final,
                                'imagen': imagenes[0] if imagenes else '/static/images/placeholder.jpg',
                                'stock': producto.get('stock', 0),
                                'cantidad': item.get('cantidad', 1)
                            })
        except Exception as e:
            app.logger.error(f"[CARRITO] Error al obtener productos: {e}")
        finally:
            conn.close()
    
    # Calcular totales y descuentos (afiliado)
    subtotal = 0
    for item in productos_completos:
        precio = float(item.get('precio', 0) or 0)
        cantidad = int(item.get('cantidad', 1) or 1)
        subtotal += precio * cantidad

    descuento_disponible = 0.0
    descuento_aplicado = 0.0
    if es_afiliado:
        try:
            descuento_disponible = obtener_descuento_disponible_afiliado(afiliado_id)
            descuento_aplicado = min(subtotal, descuento_disponible or 0)
        except Exception as e:
            app.logger.error(f"[CARRITO] No se pudo calcular descuento afiliado: {e}")
            descuento_disponible = 0.0
            descuento_aplicado = 0.0

    total = max(subtotal - descuento_aplicado, 0)
    
    app.logger.info('[CARRITO] Acceso - Items en sesión: %d, Productos encontrados: %d', len(carrito_items), len(productos_completos))
    
    # Limpiar productos que ya no existen o no tienen stock
    if carrito_items and len(productos_completos) < len(carrito_items):
        productos_ids = [p.get('producto_id') for p in productos_completos]
        
        if usuario_id:
            # Usuario registrado: los productos ya se filtran en la query de BD
            # No necesitamos limpiar manualmente, la BD ya filtra por estado='activo' y stock>0
            app.logger.info('[CARRITO] Carrito de BD ya filtrado automáticamente')
        else:
            # Visitante: actualizar cookies eliminando productos no encontrados
            carrito_limpio = [item for item in carrito_items if item.get('producto_id') in productos_ids]
            if len(carrito_limpio) != len(carrito_items):
                session['carrito'] = carrito_limpio
                session.modified = True
                app.logger.info('[CARRITO] Carrito de cookies limpiado: %d -> %d items', len(carrito_items), len(carrito_limpio))
    
    return render_template('carrito.html', 
                         carrito=productos_completos if productos_completos else [], 
                         subtotal=subtotal,
                         descuento_aplicado=descuento_aplicado,
                         descuento_disponible=descuento_disponible,
                         total=total,
                         es_afiliado=es_afiliado,
                         config={'PAYPAL_CLIENT_ID': PAYPAL_CLIENT_ID})

@app.route('/api/carrito/agregar', methods=['POST'])
@limiter.limit("20 per minute")
def carrito_agregar():
    """Agregar producto al carrito - BD para usuarios, cookies para visitantes"""
    try:
        # Helper: cerrar sesión de afiliado sin mostrar mensaje si se detecta operación prohibida
        def _force_logout_afiliado(is_api=True):
            session.pop('afiliado_id', None)
            session.pop('afiliado_nombre', None)
            session.pop('afiliado_codigo', None)
            session.pop('afiliado_email', None)
            session.pop('afiliado_comision', None)
            session.pop('afiliado_auth', None)
            session.modified = True
            app.logger.info('[SECURITY] Afiliado forzado a cerrar sesión por operación no permitida')
            if is_api:
                return ('', 204)
            return redirect(url_for('afiliados_login'))

        from flask import g
        data = request.get_json() or {}
        producto_id = int(data.get('producto_id', 0))
        cantidad = int(data.get('cantidad', 1))
        
        if not producto_id or cantidad < 1:
            return jsonify({'error': 'Datos inválidos'}), 400
        
        # Verificar si es usuario autenticado (cliente o afiliado)
        usuario_id = None
        es_afiliado = False
        
        if hasattr(g, 'current_user') and g.current_user:
            usuario_id = g.current_user['usuario_id']
        elif 'usuario_id' in session and session.get('rol') == 'cliente':
            usuario_id = session.get('usuario_id')
        elif session.get('afiliado_auth') and 'afiliado_id' in session:
            es_afiliado = True
        
        if usuario_id:
            # Usuario cliente autenticado: usar BD (sin límite)
            app.logger.info(f"[CARRITO_AGREGAR] Usuario cliente autenticado detectado: {usuario_id}")
            resultado = agregar_al_carrito_usuario(usuario_id, producto_id, cantidad)
            if 'error' in resultado:
                app.logger.error(f"[CARRITO_AGREGAR] Error: {resultado.get('error')}")
                return jsonify(resultado), 400
            return jsonify({
                'success': True,
                'message': 'Producto agregado al carrito',
                'total_items': resultado.get('total_items', 0),
                'carrito_count': resultado.get('carrito_count', 0)
            })
        elif es_afiliado:
            # Afiliado autenticado: usar BD (sin límite de $50)
            afiliado_id = session.get('afiliado_id')
            app.logger.info(f"[CARRITO_AGREGAR] Afiliado autenticado detectado: {afiliado_id}")
            resultado = agregar_al_carrito_afiliado(afiliado_id, producto_id, cantidad)
            # Si el servicio devuelve el error prohibido, forzar logout sin mensaje
            if isinstance(resultado, dict) and resultado.get('error') == 'Operación no permitida: los afiliados no pueden comprar productos':
                return _force_logout_afiliado(is_api=True)
            if 'error' in resultado:
                app.logger.error(f"[CARRITO_AGREGAR] Error: {resultado.get('error')}")
                return jsonify(resultado), 400
            carrito_afiliado = obtener_carrito_afiliado(afiliado_id)
            if isinstance(carrito_afiliado, dict) and carrito_afiliado.get('error') == 'Operación no permitida: los afiliados no pueden comprar productos':
                return _force_logout_afiliado(is_api=True)
            subtotal = sum(float(i.get('precio', 0) or 0) * int(i.get('cantidad', 1) or 1) for i in carrito_afiliado)
            descuento_disponible = obtener_descuento_disponible_afiliado(afiliado_id)
            descuento_aplicado = min(subtotal, descuento_disponible or 0)
            total_final = max(subtotal - descuento_aplicado, 0)
            total_items = sum(int(i.get('cantidad', 1) or 1) for i in carrito_afiliado)
            return jsonify({
                'success': True,
                'message': 'Producto agregado al carrito',
                'total_items': total_items,
                'carrito_count': resultado.get('carrito_count', 0),
                'subtotal': round(subtotal, 2),
                'descuento_aplicado': round(descuento_aplicado, 2),
                'descuento_disponible': round(descuento_disponible or 0, 2),
                'total_final': round(total_final, 2)
            })
        else:
            # Visitante: usar cookies
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, titulo, precio, precio_oferta, stock, estado
                        FROM productos_vendedor
                        WHERE id = %s AND estado = 'activo'
                    """, (producto_id,))
                    producto = cur.fetchone()
                    
                    if not producto:
                        return jsonify({'error': 'Producto no encontrado'}), 404
                    
                    stock_disponible = producto.get('stock', 0)
                    if stock_disponible < cantidad:
                        return jsonify({'error': f'Solo hay {stock_disponible} unidades disponibles'}), 400
                    
                    precio_final = float(producto.get('precio_oferta') or producto.get('precio') or 0)
                    
                    # Obtener carrito actual de cookies
                    carrito = session.get('carrito', [])
                    
                    # Verificar límite de $50 para visitantes
                    total_actual = calcular_total_carrito_visitante(carrito)
                    nuevo_total = total_actual + (precio_final * cantidad)
                    
                    if nuevo_total > 50.0:
                        return jsonify({
                            'error': f'Los visitantes solo pueden comprar hasta $50. Total actual: ${total_actual:.2f}, intentas agregar: ${precio_final * cantidad:.2f}',
                            'limite_excedido': True
                        }), 400
                    
                    # Verificar si el producto ya está en el carrito
                    encontrado = False
                    for item in carrito:
                        if item.get('producto_id') == producto_id:
                            nueva_cantidad = item.get('cantidad', 0) + cantidad
                            if nueva_cantidad > stock_disponible:
                                return jsonify({'error': f'No puedes agregar más. Stock disponible: {stock_disponible}'}), 400
                            item['cantidad'] = nueva_cantidad
                            encontrado = True
                            break
                    
                    # Si no está, agregarlo
                    if not encontrado:
                        carrito.append({
                            'producto_id': producto_id,
                            'cantidad': cantidad,
                            'precio': precio_final
                        })
                    
                    # Guardar en sesión
                    session['carrito'] = carrito
                    session.modified = True
                    
                    total_items = sum(item.get('cantidad', 0) for item in carrito)
                    
                    return jsonify({
                        'success': True,
                        'message': 'Producto agregado al carrito',
                        'total_items': total_items,
                        'carrito_count': len(carrito)
                    })
            finally:
                conn.close()
            
    except Exception as e:
        app.logger.error(f"[CARRITO_AGREGAR] Error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': 'Error al agregar producto'}), 500

@app.route('/api/carrito/actualizar', methods=['POST'])
@limiter.limit("20 per minute")
def carrito_actualizar():
    """Actualizar cantidad de un producto en el carrito - BD para usuarios, cookies para visitantes"""
    try:
        from flask import g
        data = request.get_json() or {}
        producto_id = int(data.get('producto_id', 0))
        cantidad = int(data.get('cantidad', 1))
        
        if not producto_id or cantidad < 1:
            return jsonify({'error': 'Datos inválidos'}), 400
        
        # Verificar si es usuario autenticado (cliente o afiliado)
        usuario_id = None
        es_afiliado = False
        
        if hasattr(g, 'current_user') and g.current_user:
            usuario_id = g.current_user['usuario_id']
        elif 'usuario_id' in session and session.get('rol') == 'cliente':
            usuario_id = session.get('usuario_id')
        elif session.get('afiliado_auth') and 'afiliado_id' in session:
            es_afiliado = True
            usuario_id = None
        
        if usuario_id:
            # Usuario cliente autenticado: usar BD (sin límite)
            resultado = actualizar_cantidad_carrito_usuario(usuario_id, producto_id, cantidad)
            if 'error' in resultado:
                return jsonify(resultado), 400
            return jsonify(resultado)
        elif es_afiliado:
            # Afiliado autenticado: usar BD (sin límite de $50)
            afiliado_id = session.get('afiliado_id')
            resultado = actualizar_cantidad_carrito_afiliado(afiliado_id, producto_id, cantidad)
            if isinstance(resultado, dict) and resultado.get('error') == 'Operación no permitida: los afiliados no pueden comprar productos':
                # Forzar logout silencioso
                session.pop('afiliado_id', None)
                session.pop('afiliado_nombre', None)
                session.pop('afiliado_codigo', None)
                session.pop('afiliado_email', None)
                session.pop('afiliado_comision', None)
                session.pop('afiliado_auth', None)
                session.modified = True
                app.logger.info('[SECURITY] Afiliado forzado a cerrar sesión por operación no permitida')
                return ('', 204)
            if 'error' in resultado:
                return jsonify(resultado), 400
            
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT precio, precio_oferta, stock
                        FROM productos_vendedor
                        WHERE id = %s
                    """, (producto_id,))
                    producto = cur.fetchone()
                    precio_final = float(producto.get('precio_oferta') or producto.get('precio') or 0) if producto else 0
                    stock_disponible = producto.get('stock', 0) if producto else 0
            finally:
                conn.close()
            
            carrito_afiliado = obtener_carrito_afiliado(afiliado_id)
            if isinstance(carrito_afiliado, dict) and carrito_afiliado.get('error') == 'Operación no permitida: los afiliados no pueden comprar productos':
                session.pop('afiliado_id', None)
                session.pop('afiliado_nombre', None)
                session.pop('afiliado_codigo', None)
                session.pop('afiliado_email', None)
                session.pop('afiliado_comision', None)
                session.pop('afiliado_auth', None)
                session.modified = True
                app.logger.info('[SECURITY] Afiliado forzado a cerrar sesión por operación no permitida')
                return ('', 204)
            precio_unitario = precio_final
            for item in carrito_afiliado:
                if item.get('producto_id') == producto_id:
                    precio_unitario = float(item.get('precio', precio_final) or 0)
                    break
            subtotal = sum(float(i.get('precio', 0) or 0) * int(i.get('cantidad', 1) or 1) for i in carrito_afiliado)
            descuento_disponible = obtener_descuento_disponible_afiliado(afiliado_id)
            descuento_aplicado = min(subtotal, descuento_disponible or 0)
            total_final = max(subtotal - descuento_aplicado, 0)
            
            return jsonify({
                'success': True,
                'message': 'Cantidad actualizada',
                'total_items': resultado.get('total_items', 0),
                'total_precio': round(total_final, 2),
                'precio_unitario': round(precio_unitario, 2),
                'precio_total_item': round(precio_unitario * cantidad, 2),
                'stock_disponible': stock_disponible,
                'carrito_count': resultado.get('carrito_count', 0),
                'subtotal': round(subtotal, 2),
                'descuento_aplicado': round(descuento_aplicado, 2),
                'descuento_disponible': round(descuento_disponible or 0, 2),
                'total_final': round(total_final, 2)
            })
        else:
            # Visitante: usar cookies
            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, titulo, precio, precio_oferta, stock, estado
                        FROM productos_vendedor
                        WHERE id = %s AND estado = 'activo'
                    """, (producto_id,))
                    producto = cur.fetchone()
                    
                    if not producto:
                        return jsonify({'error': 'Producto no encontrado o no disponible'}), 404
                    
                    stock_disponible = producto.get('stock', 0)
                    if stock_disponible <= 0:
                        return jsonify({'error': 'Producto sin stock disponible'}), 400
                    
                    if cantidad > stock_disponible:
                        return jsonify({
                            'error': f'Solo hay {stock_disponible} unidades disponibles',
                            'stock_disponible': stock_disponible
                        }), 400
                    
                    precio_final = float(producto.get('precio_oferta') or producto.get('precio') or 0)
                    
                    # Actualizar carrito de cookies
                    carrito = session.get('carrito', [])
                    encontrado = False
                    
                    for item in carrito:
                        if item.get('producto_id') == producto_id:
                            # Verificar límite de $50 para visitantes
                            total_actual = calcular_total_carrito_visitante(carrito)
                            # Restar el precio del item actual
                            precio_item_actual = item.get('precio', 0) * item.get('cantidad', 0)
                            total_sin_item = total_actual - precio_item_actual
                            nuevo_total = total_sin_item + (precio_final * cantidad)
                            
                            if nuevo_total > 50.0:
                                return jsonify({
                                    'error': f'Los visitantes solo pueden comprar hasta $50. Total actual: ${total_sin_item:.2f}, intentas agregar: ${precio_final * cantidad:.2f}',
                                    'limite_excedido': True
                                }), 400
                            
                            item['cantidad'] = cantidad
                            item['precio'] = precio_final
                            encontrado = True
                            break
                    
                    if not encontrado:
                        return jsonify({'error': 'Producto no encontrado en el carrito'}), 404
                    
                    session['carrito'] = carrito
                    session.modified = True
                    
                    # Calcular totales
                    total_items = sum(item.get('cantidad', 0) for item in carrito)
                    total_precio = calcular_total_carrito_visitante(carrito)
                    
                    return jsonify({
                        'success': True,
                        'message': 'Cantidad actualizada',
                        'total_items': total_items,
                        'total_precio': round(total_precio, 2),
                        'precio_unitario': round(precio_final, 2),
                        'precio_total_item': round(precio_final * cantidad, 2),
                        'stock_disponible': stock_disponible
                    })
            finally:
                conn.close()
            
    except ValueError as ve:
        app.logger.error(f"[CARRITO_ACTUALIZAR] Error de validación: {ve}")
        return jsonify({'error': 'Datos inválidos'}), 400
    except Exception as e:
        app.logger.error(f"[CARRITO_ACTUALIZAR] Error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': 'Error al actualizar carrito'}), 500

@app.route('/api/carrito/eliminar', methods=['POST'])
@limiter.limit("20 per minute")
def carrito_eliminar():
    """Eliminar producto del carrito - BD para usuarios, cookies para visitantes"""
    try:
        from flask import g
        data = request.get_json() or {}
        producto_id = int(data.get('producto_id', 0))
        
        if not producto_id:
            return jsonify({'error': 'ID de producto requerido'}), 400
        
        # Verificar si es usuario autenticado (cliente o afiliado)
        usuario_id = None
        es_afiliado = False
        
        if hasattr(g, 'current_user') and g.current_user:
            usuario_id = g.current_user['usuario_id']
        elif 'usuario_id' in session and session.get('rol') == 'cliente':
            usuario_id = session.get('usuario_id')
        elif session.get('afiliado_auth') and 'afiliado_id' in session:
            es_afiliado = True
        
        if usuario_id:
            # Cliente autenticado: usar BD
            resultado = eliminar_del_carrito_usuario(usuario_id, producto_id)
            if 'error' in resultado:
                return jsonify(resultado), 400
            return jsonify(resultado)
        elif es_afiliado:
            # Afiliado autenticado: usar BD
            afiliado_id = session.get('afiliado_id')
            resultado = eliminar_del_carrito_afiliado(afiliado_id, producto_id)
            if isinstance(resultado, dict) and resultado.get('error') == 'Operación no permitida: los afiliados no pueden comprar productos':
                session.pop('afiliado_id', None)
                session.pop('afiliado_nombre', None)
                session.pop('afiliado_codigo', None)
                session.pop('afiliado_email', None)
                session.pop('afiliado_comision', None)
                session.pop('afiliado_auth', None)
                session.modified = True
                app.logger.info('[SECURITY] Afiliado forzado a cerrar sesión por operación no permitida')
                return ('', 204)
            if 'error' in resultado:
                return jsonify(resultado), 400
            carrito_afiliado = obtener_carrito_afiliado(afiliado_id)
            if isinstance(carrito_afiliado, dict) and carrito_afiliado.get('error') == 'Operación no permitida: los afiliados no pueden comprar productos':
                session.pop('afiliado_id', None)
                session.pop('afiliado_nombre', None)
                session.pop('afiliado_codigo', None)
                session.pop('afiliado_email', None)
                session.pop('afiliado_comision', None)
                session.pop('afiliado_auth', None)
                session.modified = True
                app.logger.info('[SECURITY] Afiliado forzado a cerrar sesión por operación no permitida')
                return ('', 204)
            subtotal = sum(float(i.get('precio', 0) or 0) * int(i.get('cantidad', 1) or 1) for i in carrito_afiliado)
            descuento_disponible = obtener_descuento_disponible_afiliado(afiliado_id)
            descuento_aplicado = min(subtotal, descuento_disponible or 0)
            total_final = max(subtotal - descuento_aplicado, 0)
            total_items = sum(int(i.get('cantidad', 1) or 1) for i in carrito_afiliado)
            return jsonify({
                'success': True,
                'message': 'Producto eliminado del carrito',
                'total_items': total_items,
                'carrito_count': resultado.get('carrito_count', 0),
                'subtotal': round(subtotal, 2),
                'descuento_aplicado': round(descuento_aplicado, 2),
                'descuento_disponible': round(descuento_disponible or 0, 2),
                'total_final': round(total_final, 2)
            })
        else:
            # Visitante: usar cookies
            carrito = session.get('carrito', [])
            carrito = [item for item in carrito if item.get('producto_id') != producto_id]
            
            session['carrito'] = carrito
            session.modified = True
            
            total_items = sum(item.get('cantidad', 0) for item in carrito)
            
            return jsonify({
                'success': True,
                'message': 'Producto eliminado del carrito',
                'total_items': total_items,
                'carrito_count': len(carrito)
            })
        
    except Exception as e:
        app.logger.error(f"[CARRITO_ELIMINAR] Error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': 'Error al eliminar producto'}), 500

@app.route('/api/carrito/contador', methods=['GET'])
def carrito_contador():
    """Obtener contador de items en el carrito"""
    from flask import g
    
    # Verificar si es usuario autenticado (usar g.current_user o session como fallback)
    usuario_id = None
    if hasattr(g, 'current_user') and g.current_user:
        usuario_id = g.current_user['usuario_id']
    elif 'usuario_id' in session and session.get('rol') == 'cliente':
        usuario_id = session.get('usuario_id')
    
    if usuario_id:
        # Obtener carrito desde BD
        carrito_items = obtener_carrito_usuario(usuario_id)
        total_items = sum(item.get('cantidad', 0) for item in carrito_items)
    else:
        # Visitante: usar cookies
        carrito = session.get('carrito', [])
        total_items = sum(item.get('cantidad', 0) for item in carrito)
        carrito_items = carrito
    
    return jsonify({
        'total_items': total_items,
        'carrito_count': len(carrito_items)
    })

@app.route('/api/carrito/detalles', methods=['GET'])
def carrito_detalles():
    """Obtener detalles completos del carrito para el modal"""
    from flask import g
    
    try:
        # Verificar si es usuario autenticado (cliente o afiliado)
        usuario_id = None
        es_afiliado = False
        
        if hasattr(g, 'current_user') and g.current_user:
            usuario_id = g.current_user['usuario_id']
        elif 'usuario_id' in session and session.get('rol') == 'cliente':
            usuario_id = session.get('usuario_id')
        elif session.get('afiliado_auth') and 'afiliado_id' in session:
            es_afiliado = True
        
        if usuario_id:
            # Cliente registrado: SIEMPRE usar BD, nunca cookies
            carrito_items = obtener_carrito_usuario(usuario_id)
            # Asegurar que no haya carrito en cookies para clientes registrados
            if 'carrito' in session:
                session.pop('carrito', None)
                session.modified = True
        elif es_afiliado:
            # Afiliado: usar BD (sin límite)
            afiliado_id = session.get('afiliado_id')
            carrito_items = obtener_carrito_afiliado(afiliado_id)
            if isinstance(carrito_items, dict) and carrito_items.get('error') == 'Operación no permitida: los afiliados no pueden comprar productos':
                session.pop('afiliado_id', None)
                session.pop('afiliado_nombre', None)
                session.pop('afiliado_codigo', None)
                session.pop('afiliado_email', None)
                session.pop('afiliado_comision', None)
                session.pop('afiliado_auth', None)
                session.modified = True
                app.logger.info('[SECURITY] Afiliado forzado a cerrar sesión por operación no permitida')
                return ('', 204)
            # Asegurar que no haya carrito en cookies para afiliados
            if 'carrito' in session:
                session.pop('carrito', None)
                session.modified = True
        else:
            # Visitante: usar cookies con límite de $50
            carrito_items = session.get('carrito', [])
            
            # Obtener información completa de productos desde BD
            productos_completos = []
            if carrito_items:
                conn = get_db_connection()
                try:
                    with conn.cursor() as cur:
                        for item in carrito_items:
                            producto_id = item.get('producto_id')
                            if producto_id:
                                cur.execute("""
                                    SELECT id, titulo, descripcion, precio, precio_oferta, 
                                           categoria, imagenes, stock, estado
                                    FROM productos_vendedor
                                    WHERE id = %s AND estado = 'activo' AND stock > 0
                                """, (producto_id,))
                                producto = cur.fetchone()
                                if producto:
                                    # Parsear imágenes
                                    imagenes = producto.get('imagenes', '[]')
                                    if isinstance(imagenes, str):
                                        try:
                                            imagenes = json.loads(imagenes) if imagenes.startswith('[') else [imagenes]
                                        except:
                                            imagenes = [imagenes] if imagenes else []
                                    elif not isinstance(imagenes, list):
                                        imagenes = []
                                    
                                    precio_final = float(producto.get('precio_oferta') or producto.get('precio') or 0)
                                    productos_completos.append({
                                        'producto_id': producto['id'],
                                        'nombre': producto['titulo'],
                                        'descripcion': producto.get('descripcion', ''),
                                        'categoria': producto.get('categoria', 'General'),
                                        'precio': precio_final,
                                        'imagen': imagenes[0] if imagenes else '/static/images/placeholder.jpg',
                                        'stock': producto.get('stock', 0),
                                        'cantidad': item.get('cantidad', 1)
                                    })
                except Exception as e:
                    app.logger.error(f"[CARRITO_DETALLES] Error: {e}")
                finally:
                    conn.close()
            
            carrito_items = productos_completos
        
        # Calcular totales y descuento (afiliados)
        subtotal = 0
        for item in carrito_items:
            precio = float(item.get('precio', 0) or 0)
            cantidad = int(item.get('cantidad', 1) or 1)
            subtotal += precio * cantidad

        descuento_disponible = 0.0
        descuento_aplicado = 0.0
        if es_afiliado:
            try:
                afiliado_id = session.get('afiliado_id')
                descuento_disponible = obtener_descuento_disponible_afiliado(afiliado_id)
                descuento_aplicado = min(subtotal, descuento_disponible or 0)
            except Exception as e:
                app.logger.error(f"[CARRITO_DETALLES] No se pudo calcular descuento afiliado: {e}")
                descuento_disponible = 0.0
                descuento_aplicado = 0.0

        total = max(subtotal - descuento_aplicado, 0)
        
        # Validar límite SOLO para visitantes (no para clientes ni afiliados)
        es_visitante = not usuario_id and not es_afiliado
        limite_excedido = False
        if es_visitante and subtotal > 50.0:
            limite_excedido = True
        
        # Obtener información del usuario si está autenticado
        usuario_info = None
        if usuario_id:
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    try:
                        cur.execute("""
                            SELECT nombre, email, rol, tipo_usuario
                            FROM shopfusion.usuarios
                            WHERE id = %s
                        """, (usuario_id,))
                        usuario_data = cur.fetchone()
                    except Exception as e:
                        conn.rollback()
                        if "tipo_usuario" in str(e).lower():
                            cur.execute("""
                                SELECT nombre, email, rol
                                FROM shopfusion.usuarios
                                WHERE id = %s
                            """, (usuario_id,))
                            usuario_data = cur.fetchone()
                        else:
                            raise
                    if usuario_data:
                        usuario_info = {
                            'nombre': usuario_data.get('nombre'),
                            'email': usuario_data.get('email'),
                            'rol': usuario_data.get('rol'),
                            'tipo_usuario': usuario_data.get('tipo_usuario')
                        }
                conn.close()
            except Exception as e:
                app.logger.error(f"[CARRITO_DETALLES] Error al obtener info usuario: {e}")
        elif es_afiliado:
            try:
                conn = get_db_connection()
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT nombre, email, codigo_afiliado
                        FROM shopfusion.afiliados
                        WHERE id = %s
                    """, (session.get('afiliado_id'),))
                    afiliado_data = cur.fetchone()
                    if afiliado_data:
                        usuario_info = {
                            'nombre': afiliado_data.get('nombre'),
                            'email': afiliado_data.get('email'),
                            'rol': 'afiliado',
                            'codigo_afiliado': afiliado_data.get('codigo_afiliado')
                        }
                conn.close()
            except Exception as e:
                app.logger.error(f"[CARRITO_DETALLES] Error al obtener info afiliado: {e}")
        
        return jsonify({
            'success': True,
            'carrito': carrito_items,
            'subtotal': round(subtotal, 2),
            'descuento_aplicado': round(descuento_aplicado, 2),
            'descuento_disponible': round(descuento_disponible, 2),
            'total': round(total, 2),
            'es_afiliado': es_afiliado,
            'es_visitante': es_visitante,
            'limite_excedido': limite_excedido,
            'limite_visitante': 50.0,
            'usuario_info': usuario_info
        })
    except Exception as e:
        app.logger.error(f"[CARRITO_DETALLES] Error: {e}")
        return jsonify({'error': 'Error al obtener carrito'}), 500

@app.route('/api/carrito/checkout', methods=['POST'])
@limiter.limit("10 per minute")
def carrito_checkout():
    """Procesar checkout del carrito completo con PayPal - BD para usuarios, cookies para visitantes"""
    try:
        from flask import g
        data = request.get_json() or {}
        
        order_id = data.get('orderID')
        nombre = (data.get('nombre') or '').strip()
        apellido = (data.get('apellido') or '').strip()
        email = (data.get('email') or '').strip()
        telefono = (data.get('telefono') or '').strip()
        # País fijo Ecuador
        pais = 'Ecuador'
        direccion = (data.get('direccion') or '').strip()
        provincia = (data.get('provincia') or '').strip()
        ciudad = (data.get('ciudad') or '').strip()
        tipo_identificacion = (data.get('tipo_identificacion') or '').strip()
        numero_identificacion = (data.get('numero_identificacion') or '').strip()
        
        # Validaciones básicas
        if not order_id:
            return jsonify({'error': 'Falta orderID de PayPal'}), 400
        # Completar con datos guardados si es cliente autenticado
        if 'usuario_id' in session and session.get('rol') == 'cliente':
            saved = get_envio_cliente(session.get('usuario_id')) or {}
            nombre = nombre or (saved.get('nombre') or '')
            apellido = apellido or (saved.get('apellido') or '')
            email = email or (saved.get('email') or '')
            telefono = telefono or (saved.get('telefono') or '')
            direccion = direccion or (saved.get('direccion') or '')
            provincia = provincia or (saved.get('provincia') or '')
            ciudad = ciudad or (saved.get('ciudad') or '')
            tipo_identificacion = tipo_identificacion or (saved.get('tipo_identificacion') or '')
            numero_identificacion = numero_identificacion or (saved.get('numero_identificacion') or '')
        if not all([nombre, apellido, email, telefono, direccion, provincia, ciudad, tipo_identificacion, numero_identificacion]):
            return jsonify({'error': 'Faltan datos del cliente'}), 400
        
        # Verificar si es usuario autenticado (cliente o afiliado)
        usuario_id = None
        es_afiliado = False
        
        if hasattr(g, 'current_user') and g.current_user:
            usuario_id = g.current_user['usuario_id']
        elif 'usuario_id' in session and session.get('rol') == 'cliente':
            usuario_id = session.get('usuario_id')
        elif session.get('afiliado_auth') and 'afiliado_id' in session:
            es_afiliado = True
        
        # Obtener carrito según tipo de usuario
        if usuario_id:
            # Cliente registrado: obtener de BD
            app.logger.info(f"[CARRITO_CHECKOUT] Cliente autenticado: {usuario_id}")
            carrito_items = obtener_carrito_usuario(usuario_id)
            if not carrito_items:
                return jsonify({'error': 'El carrito está vacío'}), 400
        elif es_afiliado:
            # Afiliado: obtener de BD (SIN límite de $50)
            afiliado_id = session.get('afiliado_id')
            app.logger.info(f"[CARRITO_CHECKOUT] Afiliado autenticado: {afiliado_id}")
            carrito_items = obtener_carrito_afiliado(afiliado_id)
            if isinstance(carrito_items, dict) and carrito_items.get('error') == 'Operación no permitida: los afiliados no pueden comprar productos':
                session.pop('afiliado_id', None)
                session.pop('afiliado_nombre', None)
                session.pop('afiliado_codigo', None)
                session.pop('afiliado_email', None)
                session.pop('afiliado_comision', None)
                session.pop('afiliado_auth', None)
                session.modified = True
                app.logger.info('[SECURITY] Afiliado forzado a cerrar sesión por operación no permitida')
                return ('', 204)
            if not carrito_items:
                return jsonify({'error': 'El carrito está vacío'}), 400
            # NO validar límite de $50 para afiliados
        else:
            # Visitante: obtener de cookies (CON límite de $50)
            app.logger.info("[CARRITO_CHECKOUT] Visitante - usando cookies")
            carrito_cookies = session.get('carrito', [])
            if not carrito_cookies:
                return jsonify({'error': 'El carrito está vacío'}), 400
            
            # Validar límite de $50 SOLO para visitantes
            total_visitante = calcular_total_carrito_visitante(carrito_cookies)
            if total_visitante > 50.0:
                return jsonify({
                    'error': f'Los visitantes solo pueden comprar hasta $50. Total actual: ${total_visitante:.2f}',
                    'limite_excedido': True
                }), 400
            
            # Convertir formato de cookies a formato de BD para procesamiento
            carrito_items = carrito_cookies

        # Resolver precios y calcular total esperado (server-side)
        expected_total = Decimal("0")
        items_resueltos = []
        afiliado_id_sesion = session.get('afiliado_id') if es_afiliado else None
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                comision_pct = None
                if es_afiliado and afiliado_id_sesion:
                    cur.execute("""
                        SELECT comision_porcentaje
                        FROM afiliados
                        WHERE id = %s
                    """, (afiliado_id_sesion,))
                    row = cur.fetchone()
                    comision_pct = float(row.get('comision_porcentaje') or 0) if row else 0

                for item in carrito_items:
                    producto_id = item.get('producto_id')
                    try:
                        producto_id = int(producto_id)
                    except (TypeError, ValueError):
                        return jsonify({'error': 'Producto inválido en carrito'}), 400
                    cantidad = int(item.get('cantidad', 1) or 1)

                    cur.execute("""
                        SELECT precio, precio_oferta, precio_proveedor, stock
                        FROM productos_vendedor
                        WHERE id = %s AND estado = 'activo'
                    """, (producto_id,))
                    producto = cur.fetchone()
                    if not producto:
                        return jsonify({'error': f'Producto {producto_id} no encontrado'}), 404

                    stock_actual = int(producto.get('stock') or 0)
                    if cantidad > stock_actual:
                        return jsonify({'error': f'Stock insuficiente para producto {producto_id}'}), 400

                    precio_normal = float(producto.get('precio') or 0)
                    precio_oferta_val = float(producto.get('precio_oferta') or 0)
                    if precio_oferta_val > 0 and precio_oferta_val < precio_normal:
                        precio_final = precio_oferta_val
                    else:
                        precio_final = precio_normal

                    precio_proveedor = float(producto.get('precio_proveedor') or 0)
                    if es_afiliado:
                        margen_tmp = precio_final - precio_proveedor
                        comision_tmp = (margen_tmp * comision_pct / 100) if margen_tmp > 0 else 0
                        precio_pagado = max(0, precio_final - comision_tmp)
                    else:
                        precio_pagado = precio_final

                    monto_item = precio_pagado * cantidad
                    expected_total += _to_decimal(monto_item)
                    items_resueltos.append({
                        'producto_id': producto_id,
                        'cantidad': cantidad,
                        'precio_pagado': precio_pagado,
                        'precio_proveedor': precio_proveedor,
                        'monto_item': monto_item
                    })
        finally:
            conn.close()

        # Calcular descuentos para afiliados (totales netos)
        monto_bruto_total = expected_total
        descuento_aplicado = Decimal("0")
        descuento_disponible = Decimal("0")
        if es_afiliado and afiliado_id_sesion:
            try:
                descuento_disponible = _to_decimal(obtener_descuento_disponible_afiliado(afiliado_id_sesion))
                descuento_aplicado = descuento_disponible if descuento_disponible < monto_bruto_total else monto_bruto_total
                expected_total = max(monto_bruto_total - descuento_aplicado, Decimal("0"))
            except Exception as e:
                app.logger.error(f"[CARRITO_CHECKOUT] Error al calcular descuento de afiliado: {e}")
                descuento_aplicado = Decimal("0")
                expected_total = monto_bruto_total

        # 🔑 Obtener token de acceso de PayPal
        auth = (PAYPAL_CLIENT_ID, PAYPAL_SECRET)
        response = requests.post(
            f"{PAYPAL_API_BASE}/v1/oauth2/token",
            data={'grant_type': 'client_credentials'},
            auth=auth,
            timeout=PAYPAL_TIMEOUT_SECONDS
        )
        access_token = response.json().get('access_token')
        
        if not access_token:
            return jsonify({'error': 'No se pudo obtener token de PayPal'}), 500
        
        # 💰 Capturar el pago
        capture_url = f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        capture_response = requests.post(capture_url, headers=headers, timeout=PAYPAL_TIMEOUT_SECONDS)
        result = capture_response.json()
        
        if capture_response.status_code != 201:
            app.logger.error(f"[CARRITO_CHECKOUT] Error al capturar pago: {result}")
            return jsonify({
                'error': 'Error al capturar el pago en PayPal',
                'details': result
            }), 400
        
        # Obtener información del pago
        purchase_unit = result['purchase_units'][0]
        capture = purchase_unit['payments']['captures'][0]
        amount_value = float(capture['amount']['value'])
        currency_code = capture['amount']['currency_code']
        paypal_capture_id = capture['id']
        
        payer_info = result.get('payer', {})
        paypal_email = (payer_info.get('email_address') or '').strip()
        email_cuenta = session.get('email') if session.get('rol') == 'cliente' else None
        email_para_guardar = (email_cuenta or email or paypal_email).strip()
        if paypal_email:
            session['ultima_paypal_email'] = paypal_email
            session.modified = True

        if not _amounts_match(expected_total, amount_value):
            app.logger.error(
                "[CARRITO_CHECKOUT] Monto no coincide. Esperado=%s Capturado=%s",
                _money(expected_total),
                _money(amount_value)
            )
            return jsonify({'error': 'Monto capturado no coincide con el total esperado'}), 400

        # Ajustar montos netos si se aplicó un descuento de afiliado
        if descuento_aplicado > 0 and monto_bruto_total > 0 and items_resueltos:
            restante_desc = descuento_aplicado
            for idx, item in enumerate(items_resueltos):
                base = _to_decimal(item.get('monto_item', 0))
                if idx == len(items_resueltos) - 1:
                    descuento_item = restante_desc
                else:
                    propor = (base / monto_bruto_total) if monto_bruto_total > 0 else Decimal("0")
                    descuento_item = (descuento_aplicado * propor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    if descuento_item > restante_desc:
                        descuento_item = restante_desc
                restante_desc -= descuento_item
                item['monto_item_neto'] = float(max(base - descuento_item, Decimal("0")))
        else:
            for item in items_resueltos:
                item['monto_item_neto'] = float(item.get('monto_item', 0))

        # 🧾 Registrar cada producto del carrito como compra separada
        from services_exclusivos import registrar_compra_exclusivo
        compra_ids = []
        ref_afiliado_id, ref_afiliado_codigo = get_afiliado_referido()
        ref_afiliado_id, ref_afiliado_codigo = resolver_afiliado_por_email(
            email_para_guardar,
            ref_afiliado_id,
            ref_afiliado_codigo
        )
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                for item in items_resueltos:
                    producto_id = item['producto_id']
                    cantidad = item['cantidad']
                    monto_item = item['monto_item']
                    precio_pagado = item['precio_pagado']
                    precio_proveedor = item['precio_proveedor']
                    monto_margen = (precio_pagado - precio_proveedor) * cantidad

                    # Obtener información del afiliado referido (si aplica)
                    afiliado_id = ref_afiliado_id
                    afiliado_codigo = ref_afiliado_codigo

                    # Registrar compra
                    compra_id = registrar_compra_exclusivo(
                        producto_id=int(producto_id),
                        nombre=nombre,
                        apellido=apellido,
                        email=email_para_guardar,
                        telefono=telefono,
                        pais=pais,
                        direccion=direccion,
                        provincia=provincia,
                        ciudad=ciudad,
                        tipo_identificacion=tipo_identificacion,
                        numero_identificacion=numero_identificacion,
                        cantidad=cantidad,
                        paypal_order_id=order_id,
                        paypal_capture_id=paypal_capture_id,
                        monto_total=item.get('monto_item_neto', monto_item),
                        moneda=currency_code,
                        estado_pago="pagado",
                        afiliado_id=afiliado_id,
                        afiliado_codigo=afiliado_codigo
                    )
                    compra_ids.append(compra_id)

                    # Registrar comisión si hay afiliado
                    if afiliado_id:
                        try:
                            from services_afiliados import registrar_comision
                            cur.execute("""
                                SELECT id, estado, comision_porcentaje 
                                FROM afiliados 
                                WHERE id = %s AND estado = 'activo'
                            """, (afiliado_id,))
                            afiliado = cur.fetchone()

                            if afiliado:
                                registrar_comision(
                                    afiliado_id=afiliado_id,
                                    compra_id=compra_id,
                                    monto_venta=monto_item,
                                    comision_porcentaje=float(afiliado['comision_porcentaje']),
                                    producto_id=int(producto_id),
                                    monto_margen=monto_margen
                                )
                        except Exception as e:
                            app.logger.error(f"[CARRITO_CHECKOUT] Error al registrar comisión: {e}")
        finally:
            conn.close()
        
        # Aplicar descuento usado (afiliados)
        if es_afiliado and afiliado_id_sesion and descuento_aplicado > 0:
            try:
                aplicar_descuento_afiliado(afiliado_id_sesion, float(descuento_aplicado))
            except Exception as e:
                app.logger.error(f"[CARRITO_CHECKOUT] No se pudo descontar saldo de afiliado: {e}")

        # Guardar datos de envío para cliente autenticado
        if usuario_id:
            try:
                upsert_envio_cliente(usuario_id, {
                    'usuario_id': usuario_id,
                    'tipo_identificacion': tipo_identificacion,
                    'numero_identificacion': numero_identificacion,
                    'nombre': nombre,
                    'apellido': apellido,
                    'email': email,
                    'telefono': telefono,
                    'pais': pais,
                    'provincia': provincia,
                    'ciudad': ciudad,
                    'direccion': direccion
                })
            except Exception as e:
                app.logger.error(f"[CARRITO_CHECKOUT] No se pudo guardar datos de envío: {e}")

        # Limpiar carrito después de compra exitosa
        if usuario_id:
            # Cliente registrado: limpiar de BD
            limpiar_carrito_usuario(usuario_id)
            app.logger.info(f"[CARRITO_CHECKOUT] Carrito de BD limpiado para cliente {usuario_id}")
        elif es_afiliado:
            # Afiliado: limpiar de BD
            afiliado_id = session.get('afiliado_id')
            limpiar_carrito_afiliado(afiliado_id)
            app.logger.info(f"[CARRITO_CHECKOUT] Carrito de BD limpiado para afiliado {afiliado_id}")
        else:
            # Visitante: limpiar de cookies
            session['carrito'] = []
            session.modified = True
            app.logger.info("[CARRITO_CHECKOUT] Carrito de cookies limpiado")
        
        app.logger.info(f"[CARRITO_CHECKOUT] Compra exitosa: {len(compra_ids)} productos, total: ${amount_value}")
        
        return jsonify({
            'status': 'success',
            'payer': f"{nombre} {apellido}",
            'amount': amount_value,
            'moneda': currency_code,
            'compra_ids': compra_ids,
            'productos': len(compra_ids)
        })
        
    except Exception as e:
        app.logger.error(f"[CARRITO_CHECKOUT] Error inesperado: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': 'Error inesperado al procesar el pago'}), 500

# ========== RUTAS API PARA PANEL DE CUENTA DEL CLIENTE ==========

@app.route('/api/cuenta/perfil', methods=['GET'])
def cuenta_perfil():
    """Obtener perfil del usuario autenticado"""
    try:
        from flask import g
        usuario_id = None
        if hasattr(g, 'current_user') and g.current_user:
            usuario_id = g.current_user['usuario_id']
        elif 'usuario_id' in session and session.get('rol') == 'cliente':
            usuario_id = session.get('usuario_id')
        
        if not usuario_id:
            return jsonify({'error': 'No autenticado'}), 401
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, nombre, email, rol
                    FROM shopfusion.usuarios
                    WHERE id = %s
                """, (usuario_id,))
                usuario = cur.fetchone()
                
                if not usuario:
                    return jsonify({'error': 'Usuario no encontrado'}), 404
                
                return jsonify({
                    'success': True,
                    'nombre': usuario.get('nombre'),
                    'email': usuario.get('email'),
                    'rol': usuario.get('rol')
                })
        finally:
            conn.close()
    except Exception as e:
        app.logger.error(f"[CUENTA_PERFIL] Error: {e}")
        return jsonify({'error': 'Error al obtener perfil'}), 500

@app.route('/api/cuenta/envio', methods=['GET'])
def cuenta_envio_get():
    """Datos de envío/facturación del cliente (Ecuador)."""
    try:
        from flask import g
        usuario_id = None
        if hasattr(g, 'current_user') and g.current_user:
            usuario_id = g.current_user['usuario_id']
        elif 'usuario_id' in session and session.get('rol') == 'cliente':
            usuario_id = session.get('usuario_id')
        if not usuario_id:
            return jsonify({'error': 'No autenticado'}), 401

        envio = get_envio_cliente(usuario_id) or {}
        return jsonify({
            'success': True,
            'envio': {
                'tipo_identificacion': envio.get('tipo_identificacion') or '',
                'numero_identificacion': envio.get('numero_identificacion') or '',
                'nombre': envio.get('nombre') or '',
                'apellido': envio.get('apellido') or '',
                'email': envio.get('email') or '',
                'telefono': envio.get('telefono') or '',
                'pais': envio.get('pais') or 'Ecuador',
                'provincia': envio.get('provincia') or '',
                'ciudad': envio.get('ciudad') or '',
                'direccion': envio.get('direccion') or ''
            }
        })
    except Exception as e:
        app.logger.error(f"[CUENTA_ENVIO_GET] Error: {e}")
        return jsonify({'error': 'Error al obtener datos de envío'}), 500

@app.route('/api/cuenta/envio', methods=['POST'])
def cuenta_envio_post():
    """Guardar/actualizar datos de envío/facturación del cliente."""
    try:
        from flask import g
        usuario_id = None
        if hasattr(g, 'current_user') and g.current_user:
            usuario_id = g.current_user['usuario_id']
        elif 'usuario_id' in session and session.get('rol') == 'cliente':
            usuario_id = session.get('usuario_id')
        if not usuario_id:
            return jsonify({'error': 'No autenticado'}), 401

        data = request.get_json() or {}
        required = ['tipo_identificacion', 'numero_identificacion', 'nombre', 'apellido', 'email', 'telefono', 'provincia', 'ciudad', 'direccion']
        for r in required:
            if not (data.get(r) or '').strip():
                return jsonify({'error': f'Falta {r}'}), 400
        data['pais'] = 'Ecuador'
        data['usuario_id'] = usuario_id
        upsert_envio_cliente(usuario_id, data)
        return jsonify({'success': True, 'message': 'Datos de envío guardados'})
    except Exception as e:
        app.logger.error(f"[CUENTA_ENVIO_POST] Error: {e}")
        return jsonify({'error': 'Error al guardar datos de envío'}), 500

@app.route('/api/cuenta/compras', methods=['GET'])
def cuenta_compras():
    """Obtener compras del usuario autenticado"""
    try:
        from flask import g
        usuario_id = None
        if hasattr(g, 'current_user') and g.current_user:
            usuario_id = g.current_user['usuario_id']
        elif 'usuario_id' in session and session.get('rol') == 'cliente':
            usuario_id = session.get('usuario_id')
        
        if not usuario_id:
            return jsonify({'error': 'No autenticado'}), 401
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT email FROM shopfusion.usuarios WHERE id = %s", (usuario_id,))
                usuario = cur.fetchone()
                if not usuario:
                    return jsonify({'error': 'Usuario no encontrado'}), 404
                
                email = usuario.get('email')
                emails_busqueda = [email] if email else []
                paypal_email_sesion = session.get('ultima_paypal_email')
                if paypal_email_sesion and paypal_email_sesion not in emails_busqueda:
                    emails_busqueda.append(paypal_email_sesion)

                cur.execute("""
                    SELECT id, producto_id, producto_titulo, cantidad, monto_total, 
                           moneda, estado_pago, COALESCE(creado_en, CURRENT_TIMESTAMP) as creado_en, paypal_order_id
                    FROM shopfusion.cliente_compraron_productos
                    WHERE email = ANY(%s)
                    ORDER BY COALESCE(creado_en, CURRENT_TIMESTAMP) DESC
                """, (emails_busqueda,))
                
                compras = cur.fetchall()
                
                return jsonify({
                    'success': True,
                    'compras': [dict(compra) for compra in compras]
                })
        finally:
            conn.close()
    except Exception as e:
        app.logger.error(f"[CUENTA_COMPRAS] Error: {e}")
        return jsonify({'error': 'Error al obtener compras'}), 500

@app.route('/api/cuenta/direcciones', methods=['GET'])
def cuenta_direcciones():
    """Obtener direcciones guardadas del usuario más datos de envío (Ecuador)."""
    try:
        from flask import g
        usuario_id = None
        afiliado_id = None
        tipo = 'cliente'
        if hasattr(g, 'current_user') and g.current_user:
            usuario_id = g.current_user['usuario_id']
        elif 'usuario_id' in session and session.get('rol') == 'cliente':
            usuario_id = session.get('usuario_id')
        elif session.get('afiliado_auth') and session.get('afiliado_id'):
            afiliado_id = session.get('afiliado_id')
            tipo = 'afiliado'
        
        if not usuario_id and not afiliado_id:
            return jsonify({'error': 'No autenticado'}), 401
        
        conn = get_db_connection()
        try:
            ensure_direcciones_tables(conn)
            ensure_envio_clientes_table(conn)
            envio = None
            with conn.cursor() as cur:
                direcciones = []
                if tipo == 'cliente':
                    cur.execute("SELECT email, nombre FROM shopfusion.usuarios WHERE id = %s", (usuario_id,))
                    usuario = cur.fetchone()
                    if not usuario:
                        return jsonify({'error': 'Usuario no encontrado'}), 404
                    
                    cur.execute("""
                        SELECT id, pais, ciudad, direccion, telefono
                        FROM shopfusion.direcciones_clientes
                        WHERE usuario_id = %s
                        ORDER BY actualizado_en DESC, creado_en DESC
                    """, (usuario_id,))
                    direcciones = cur.fetchall()

                    # Fallback: recuperar de compras históricas si aún no hay direcciones guardadas
                    if not direcciones:
                        email = usuario.get('email')
                        cur.execute("""
                            SELECT DISTINCT ON (pais, direccion, telefono)
                                   NULL AS id, pais, '' AS ciudad, direccion, telefono
                            FROM shopfusion.cliente_compraron_productos
                            WHERE email = %s AND direccion IS NOT NULL AND direccion != ''
                            ORDER BY pais, direccion, telefono, creado_en DESC
                        """, (email,))
                        direcciones = cur.fetchall()
                    envio = get_envio_cliente(usuario_id)
                else:
                    cur.execute("""
                        SELECT id, pais, ciudad, direccion, telefono
                        FROM shopfusion.direcciones_afiliados
                        WHERE afiliado_id = %s
                        ORDER BY actualizado_en DESC, creado_en DESC
                    """, (afiliado_id,))
                    direcciones = cur.fetchall()
                
                direcciones_formateadas = []
                for dir in direcciones:
                    direcciones_formateadas.append({
                        'id': dir.get('id'),
                        'pais': dir.get('pais', 'Ecuador'),
                        'ciudad': dir.get('ciudad', ''),
                        'direccion': dir.get('direccion', ''),
                        'telefono': dir.get('telefono', ''),
                        'provincia': envio.get('provincia') if tipo == 'cliente' and envio else '',
                        'tipo_identificacion': envio.get('tipo_identificacion') if tipo == 'cliente' and envio else '',
                        'numero_identificacion': envio.get('numero_identificacion') if tipo == 'cliente' and envio else '',
                        'nombre': envio.get('nombre') if tipo == 'cliente' and envio else (usuario.get('nombre') if tipo == 'cliente' else ''),
                        'apellido': envio.get('apellido') if tipo == 'cliente' and envio else ''
                    })
                
                return jsonify({
                    'success': True,
                    'direcciones': direcciones_formateadas,
                    'tipo': tipo
                })
        finally:
            conn.close()
    except Exception as e:
        app.logger.error(f"[CUENTA_DIRECCIONES] Error: {e}")
        return jsonify({'error': 'Error al obtener direcciones'}), 500

@app.route('/api/cuenta/direcciones/agregar', methods=['POST'])
def cuenta_direcciones_agregar():
    """Agregar nueva dirección"""
    try:
        from flask import g
        usuario_id = None
        afiliado_id = None
        tipo = 'cliente'
        if hasattr(g, 'current_user') and g.current_user:
            usuario_id = g.current_user['usuario_id']
        elif 'usuario_id' in session and session.get('rol') == 'cliente':
            usuario_id = session.get('usuario_id')
        elif session.get('afiliado_auth') and session.get('afiliado_id'):
            afiliado_id = session.get('afiliado_id')
            tipo = 'afiliado'
        
        if not usuario_id and not afiliado_id:
            return jsonify({'error': 'No autenticado'}), 401
        
        data = request.get_json() or {}
        pais = (data.get('pais') or '').strip()
        ciudad = (data.get('ciudad') or '').strip()
        direccion = (data.get('direccion') or '').strip()
        telefono = (data.get('telefono') or '').strip()
        
        if not all([pais, ciudad, direccion, telefono]):
            return jsonify({'error': 'Faltan datos de la dirección'}), 400
        
        conn = get_db_connection()
        try:
            ensure_direcciones_tables(conn)
            with conn.cursor() as cur:
                if tipo == 'cliente':
                    cur.execute("SELECT nombre, email FROM shopfusion.usuarios WHERE id = %s", (usuario_id,))
                    usuario = cur.fetchone()
                    if not usuario:
                        return jsonify({'error': 'Usuario no encontrado'}), 404
                    
                    cur.execute("""
                        INSERT INTO shopfusion.direcciones_clientes
                            (usuario_id, pais, ciudad, direccion, telefono, principal, actualizado_en)
                        VALUES (%s, %s, %s, %s, %s, FALSE, CURRENT_TIMESTAMP)
                        ON CONFLICT (usuario_id, pais, ciudad, direccion, telefono)
                        DO UPDATE SET actualizado_en = CURRENT_TIMESTAMP
                        RETURNING id;
                    """, (usuario_id, pais, ciudad, direccion, telefono))
                else:
                    cur.execute("""
                        INSERT INTO shopfusion.direcciones_afiliados
                            (afiliado_id, pais, ciudad, direccion, telefono, principal, actualizado_en)
                        VALUES (%s, %s, %s, %s, %s, FALSE, CURRENT_TIMESTAMP)
                        ON CONFLICT (afiliado_id, pais, ciudad, direccion, telefono)
                        DO UPDATE SET actualizado_en = CURRENT_TIMESTAMP
                        RETURNING id;
                    """, (afiliado_id, pais, ciudad, direccion, telefono))
                conn.commit()
                nueva_id = cur.fetchone()['id']
                
                return jsonify({
                    'success': True,
                    'id': nueva_id,
                    'message': 'Dirección guardada. Se usará en tu próxima compra.',
                    'tipo': tipo
                })
        finally:
            conn.close()
    except Exception as e:
        app.logger.error(f"[CUENTA_DIRECCIONES_AGREGAR] Error: {e}")
        return jsonify({'error': 'Error al agregar dirección'}), 500

@app.route('/api/cuenta/direcciones/eliminar/<int:dir_id>', methods=['POST'])
def cuenta_direcciones_eliminar(dir_id):
    """Eliminar dirección"""
    try:
        from flask import g
        usuario_id = None
        afiliado_id = None
        if hasattr(g, 'current_user') and g.current_user:
            usuario_id = g.current_user['usuario_id']
        elif 'usuario_id' in session and session.get('rol') == 'cliente':
            usuario_id = session.get('usuario_id')
        elif session.get('afiliado_auth') and session.get('afiliado_id'):
            afiliado_id = session.get('afiliado_id')
        
        if not usuario_id and not afiliado_id:
            return jsonify({'error': 'No autenticado'}), 401

        conn = get_db_connection()
        try:
            ensure_direcciones_tables(conn)
            with conn.cursor() as cur:
                if usuario_id:
                    cur.execute("""
                        DELETE FROM shopfusion.direcciones_clientes
                        WHERE id = %s AND usuario_id = %s
                    """, (dir_id, usuario_id))
                else:
                    cur.execute("""
                        DELETE FROM shopfusion.direcciones_afiliados
                        WHERE id = %s AND afiliado_id = %s
                    """, (dir_id, afiliado_id))
                conn.commit()
        finally:
            conn.close()

        return jsonify({
            'success': True,
            'message': 'Dirección eliminada'
        })
    except Exception as e:
        app.logger.error(f"[CUENTA_DIRECCIONES_ELIMINAR] Error: {e}")
        return jsonify({'error': 'Error al eliminar dirección'}), 500

@app.route('/api/cuenta/facturas', methods=['GET'])
def cuenta_facturas():
    """Obtener facturas del usuario"""
    try:
        from flask import g
        usuario_id = None
        if hasattr(g, 'current_user') and g.current_user:
            usuario_id = g.current_user['usuario_id']
        elif 'usuario_id' in session and session.get('rol') == 'cliente':
            usuario_id = session.get('usuario_id')
        
        if not usuario_id:
            return jsonify({'error': 'No autenticado'}), 401
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT email FROM shopfusion.usuarios WHERE id = %s", (usuario_id,))
                usuario = cur.fetchone()
                if not usuario:
                    return jsonify({'error': 'Usuario no encontrado'}), 404
                
                email = usuario.get('email')
                emails_busqueda = [email] if email else []
                paypal_email_sesion = session.get('ultima_paypal_email')
                if paypal_email_sesion and paypal_email_sesion not in emails_busqueda:
                    emails_busqueda.append(paypal_email_sesion)

                cur.execute("""
                    SELECT id, producto_titulo, cantidad, monto_total, moneda, 
                           estado_pago, COALESCE(creado_en, CURRENT_TIMESTAMP) as creado_en, paypal_order_id, paypal_capture_id,
                           nombre, apellido, email, telefono, pais, direccion
                    FROM shopfusion.cliente_compraron_productos
                    WHERE email = ANY(%s)
                    ORDER BY COALESCE(creado_en, CURRENT_TIMESTAMP) DESC
                """, (emails_busqueda,))
                
                facturas = cur.fetchall()
                
                return jsonify({
                    'success': True,
                    'facturas': [dict(factura) for factura in facturas]
                })
        finally:
            conn.close()
    except Exception as e:
        app.logger.error(f"[CUENTA_FACTURAS] Error: {e}")
        return jsonify({'error': 'Error al obtener facturas'}), 500

@app.route('/api/cuenta/facturas/descargar/<int:factura_id>', methods=['GET'])
def cuenta_facturas_descargar(factura_id):
    """Descargar factura"""
    return redirect(url_for('index'))

@app.route('/api/cuenta/cambiar-password', methods=['POST'])
@limiter.limit("5 per minute")
def cuenta_cambiar_password():
    """Cambiar contraseña del usuario"""
    try:
        from flask import g
        usuario_id = None
        if hasattr(g, 'current_user') and g.current_user:
            usuario_id = g.current_user['usuario_id']
        elif 'usuario_id' in session and session.get('rol') == 'cliente':
            usuario_id = session.get('usuario_id')
        
        if not usuario_id:
            return jsonify({'error': 'No autenticado'}), 401
        
        data = request.get_json() or {}
        current_password = data.get('current_password', '').strip()
        new_password = data.get('new_password', '').strip()
        
        if not current_password or not new_password:
            return jsonify({'error': 'Faltan datos'}), 400
        
        if len(new_password) < 6:
            return jsonify({'error': 'La nueva contraseña debe tener al menos 6 caracteres'}), 400
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, password FROM shopfusion.usuarios WHERE id = %s", (usuario_id,))
                usuario = cur.fetchone()
                
                if not usuario:
                    return jsonify({'error': 'Usuario no encontrado'}), 404
                
                if not check_password_hash(usuario['password'], current_password):
                    return jsonify({'error': 'Contraseña actual incorrecta'}), 400
                
                new_password_hash = generate_password_hash(new_password)
                cur.execute("""
                    UPDATE shopfusion.usuarios
                    SET password = %s
                    WHERE id = %s
                """, (new_password_hash, usuario_id))
                conn.commit()
                
                app.logger.info(f"[CUENTA_CAMBIAR_PASSWORD] Contraseña cambiada para usuario {usuario_id}")
                
                return jsonify({
                    'success': True,
                    'message': 'Contraseña cambiada correctamente'
                })
        finally:
            conn.close()
    except Exception as e:
        app.logger.error(f"[CUENTA_CAMBIAR_PASSWORD] Error: {e}")
        return jsonify({'error': 'Error al cambiar contraseña'}), 500

@app.route('/api/cuenta/solicitar-proveedor', methods=['POST'])
def cuenta_solicitar_proveedor():
    """Solicitar ser proveedor"""
    try:
        from flask import g
        usuario_id = None
        if hasattr(g, 'current_user') and g.current_user:
            usuario_id = g.current_user['usuario_id']
        elif 'usuario_id' in session and session.get('rol') == 'cliente':
            usuario_id = session.get('usuario_id')
        
        if not usuario_id:
            return jsonify({'error': 'No autenticado'}), 401
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT nombre, email FROM shopfusion.usuarios WHERE id = %s", (usuario_id,))
                usuario = cur.fetchone()
                if not usuario:
                    return jsonify({'error': 'Usuario no encontrado'}), 404
                
                mensaje = f"Solicitud para ser proveedor de: {usuario.get('nombre')} ({usuario.get('email')})"
                cur.execute("""
                    INSERT INTO shopfusion.sugerencias (nombre, email, mensaje, urgente)
                    VALUES (%s, %s, %s, TRUE)
                """, (usuario.get('nombre'), usuario.get('email'), mensaje))
                conn.commit()
                
                app.logger.info(f"[CUENTA_SOLICITAR_PROVEEDOR] Solicitud de usuario {usuario_id}")
                
                return jsonify({
                    'success': True,
                    'message': 'Solicitud enviada correctamente. Te contactaremos pronto.'
                })
        finally:
            conn.close()
    except Exception as e:
        app.logger.error(f"[CUENTA_SOLICITAR_PROVEEDOR] Error: {e}")
        return jsonify({'error': 'Error al enviar solicitud'}), 500

@app.route('/api/cuenta/solicitar-afiliado', methods=['POST'])
def cuenta_solicitar_afiliado():
    """Solicitar ser afiliado"""
    try:
        from flask import g
        usuario_id = None
        if hasattr(g, 'current_user') and g.current_user:
            usuario_id = g.current_user['usuario_id']
        elif 'usuario_id' in session and session.get('rol') == 'cliente':
            usuario_id = session.get('usuario_id')
        
        if not usuario_id:
            return jsonify({'error': 'No autenticado'}), 401
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT nombre, email FROM shopfusion.usuarios WHERE id = %s", (usuario_id,))
                usuario = cur.fetchone()
                if not usuario:
                    return jsonify({'error': 'Usuario no encontrado'}), 404
                
                mensaje = f"Solicitud para ser afiliado de: {usuario.get('nombre')} ({usuario.get('email')})"
                cur.execute("""
                    INSERT INTO shopfusion.sugerencias (nombre, email, mensaje, urgente)
                    VALUES (%s, %s, %s, TRUE)
                """, (usuario.get('nombre'), usuario.get('email'), mensaje))
                conn.commit()
                
                app.logger.info(f"[CUENTA_SOLICITAR_AFILIADO] Solicitud de usuario {usuario_id}")
                
                return jsonify({
                    'success': True,
                    'message': 'Solicitud enviada correctamente. Te contactaremos pronto.'
                })
        finally:
            conn.close()
    except Exception as e:
        app.logger.error(f"[CUENTA_SOLICITAR_AFILIADO] Error: {e}")
        return jsonify({'error': 'Error al enviar solicitud'}), 500

@app.route('/api/cuenta/logout', methods=['POST'])
def cuenta_logout():
    """Cerrar sesión del usuario"""
    try:
        from flask import g
        token = None
        
        if request.cookies.get('auth_token'):
            token = request.cookies.get('auth_token')
        elif hasattr(g, 'auth_token'):
            token = g.auth_token
        elif session.get('auth_token'):
            token = session.get('auth_token')
        
        if token:
            from services_auth import cerrar_sesion
            cerrar_sesion(token)
        
        session.clear()
        
        response = make_response(jsonify({
            'success': True,
            'message': 'Sesión cerrada correctamente'
        }))
        response.set_cookie('auth_token', '', expires=0)
        
        app.logger.info('[CUENTA_LOGOUT] Sesión cerrada')
        
        return response
    except Exception as e:
        app.logger.error(f"[CUENTA_LOGOUT] Error: {e}")
        return jsonify({'error': 'Error al cerrar sesión'}), 500

@app.route('/logout')
def logout():
    # Cerrar sesión en BD
    token = request.cookies.get('auth_token') or session.get('auth_token')
    if token:
        cerrar_sesion(token)
    
    # Limpiar session y cookie
    session.clear()
    response = make_response(redirect(url_for('index')))
    response.set_cookie('auth_token', '', expires=0)
    flash('Sesión cerrada exitosamente', 'success')
    app.logger.info('[LOGOUT] Sesión cerrada')
    return response

@app.route('/catalogo')
def catalogo():
    """Redirige al inicio donde están todos los productos"""
    return redirect(url_for('index'))

@app.route('/exclusivos')
def exclusivos():
    """Redirige al inicio donde están todos los productos"""
    return redirect(url_for('index'))


@app.route('/admin/productos-exclusivos', methods=['GET', 'POST'])
def listar_productos_exclusivos():
    # 🔐 Solo admin
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))

    if request.method == 'POST':
        titulo = (request.form.get('titulo') or '').strip()
        descripcion = (request.form.get('descripcion') or '').strip()
        precio_proveedor_raw = (request.form.get('precio_proveedor') or '').strip()
        precio_raw = (request.form.get('precio') or '').strip()
        precio_oferta_raw = (request.form.get('precio_oferta') or '').strip()
        categoria = (request.form.get('categoria') or '').strip() or None
        stock_raw = (request.form.get('stock') or '0').strip()
        estado = (request.form.get('estado') or 'activo').strip() or 'activo'
        imagenes_raw = (request.form.get('imagenes') or '').strip()
        envio_gratis = request.form.get('envio_gratis') == 'on'
        importado = request.form.get('importado') == 'on'
        link_proveedor = (request.form.get('link_proveedor') or '').strip()

        errores = []

        if not titulo:
            errores.append('El título es obligatorio.')
        if not descripcion:
            errores.append('La descripción es obligatoria.')

        # Validar precio proveedor
        try:
            precio_proveedor = float(precio_proveedor_raw) if precio_proveedor_raw else 0.0
            if precio_proveedor < 0:
                raise ValueError
        except ValueError:
            errores.append('El precio proveedor debe ser un número positivo.')
        
        # Validar precio
        try:
            precio = float(precio_raw)
            if precio < 0:
                raise ValueError
            if precio_proveedor and precio <= precio_proveedor:
                errores.append('El precio de venta debe ser mayor al precio proveedor.')
        except ValueError:
            errores.append('El precio debe ser un número positivo.')

        # Validar stock
        try:
            stock = int(stock_raw or 0)
            if stock < 0:
                raise ValueError
        except ValueError:
            errores.append('El stock debe ser un número entero mayor o igual a 0.')

        # Precio oferta opcional
        precio_oferta = None
        if precio_oferta_raw:
            try:
                precio_oferta = float(precio_oferta_raw)
                if precio_oferta < 0:
                    raise ValueError
            except ValueError:
                errores.append('El precio de oferta debe ser un número positivo.')

        # Procesar imágenes: convertir "url1, url2" -> ["url1","url2"]
        imagenes_list = []
        if imagenes_raw:
            partes = [u.strip() for u in imagenes_raw.split(',')]
            imagenes_list = [u for u in partes if u]

        if errores:
            for e in errores:
                flash(e, 'danger')
        else:
            try:
                nuevo_id = crear_producto_exclusivo({
                    'titulo': titulo,
                    'descripcion': descripcion,
                    'precio': precio,
                    'precio_oferta': precio_oferta,
                    'precio_proveedor': precio_proveedor,
                    'categoria': categoria,
                    'stock': stock,
                    'estado': estado,
                    'imagenes': imagenes_list,
                    'envio_gratis': envio_gratis,
                    'importado': importado,
                    'mas_vendido': (request.form.get('mas_vendido') == 'on'),
                    'link_proveedor': link_proveedor or None,
                })
                flash(f'Producto exclusivo creado correctamente (ID {nuevo_id}).', 'success')
                return redirect(url_for('listar_productos_exclusivos'))
            except Exception as e:
                print('Error al crear producto exclusivo:', e)
                flash('Ocurrió un error al crear el producto exclusivo.', 'danger')

    # GET o POST con errores -> volvemos a listar
    productos = obtener_productos_exclusivos_admin(limit=100)
    categorias = get_categorias()
    return render_template('admin_productos_exclusivos.html', productos=productos, categorias=categorias)

@app.route('/admin/productos-exclusivos/<int:producto_id>/editar', methods=['GET', 'POST'])
def editar_producto_exclusivo(producto_id):
    # 🔐 Solo admin
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))

    # Traer producto desde la BD
    producto = obtener_producto_exclusivo_por_id(producto_id)
    if not producto:
        flash('Producto no encontrado', 'danger')
        return redirect(url_for('listar_productos_exclusivos'))

    # 📝 POST: guardar cambios
    if request.method == 'POST':
        try:
            # -------- Imágenes: leer textarea y pasarlo a lista --------
            imagenes_raw = request.form.get('imagenes', '') or ''
            imagenes_list = [
                u.strip()
                for u in imagenes_raw.split(',')
                if u.strip()
            ]

            # -------- Campos normales --------
            precio_oferta_val = request.form.get('precio_oferta') or ''
            precio_oferta = float(precio_oferta_val) if precio_oferta_val else None
            
            precio_proveedor_val = request.form.get('precio_proveedor') or ''
            precio_proveedor = float(precio_proveedor_val) if precio_proveedor_val else 0.0
            
            campos = {
                "titulo": (request.form.get('titulo') or '').strip(),
                "descripcion": (request.form.get('descripcion') or '').strip(),
                "precio": float(request.form.get('precio') or 0),
                "precio_oferta": precio_oferta,
                "precio_proveedor": precio_proveedor,
                "categoria": (request.form.get('categoria') or '').strip(),
                "stock": int(request.form.get('stock') or 0),
                "estado": (request.form.get('estado') or '').strip(),
                "imagenes": imagenes_list,   # 👈 importante
                "mas_vendido": (request.form.get('mas_vendido') == 'on'),
            }

            # Actualizar en BD
            actualizar_producto_exclusivo(producto_id, campos)
            flash('Producto actualizado correctamente', 'success')
            return redirect(url_for('listar_productos_exclusivos'))

        except Exception as e:
            app.logger.error(f"[ADMIN_EXCLUSIVOS_EDIT] Error al actualizar producto {producto_id}: {e}")
            flash(f'Error al actualizar el producto: {e}', 'danger')
            return redirect(url_for('editar_producto_exclusivo', producto_id=producto_id))

    # GET → mostrar formulario prellenado
    return render_template('admin_editar_producto_exclusivo.html', producto=producto, categorias=get_categorias())


@app.route('/panel/crear-exclusivo', methods=['POST'])
def panel_crear_exclusivo():
    """Crear producto exclusivo desde el panel principal"""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    
    try:
        titulo = (request.form.get('titulo') or '').strip()
        descripcion = (request.form.get('descripcion') or '').strip()
        precio_raw = (request.form.get('precio') or '').strip()
        precio_oferta_raw = (request.form.get('precio_oferta') or '').strip()
        precio_proveedor_raw = (request.form.get('precio_proveedor') or '').strip()
        categoria = (request.form.get('categoria') or '').strip() or None
        stock_raw = (request.form.get('stock') or '0').strip()
        estado = (request.form.get('estado') or 'activo').strip() or 'activo'
        imagenes_raw = request.form.get('imagenes_hidden') or request.form.get('imagenes') or ''
        link_proveedor = (request.form.get('link_proveedor') or '').strip() or None
        
        errores = []
        
        if not titulo:
            errores.append('El título es obligatorio.')
        if not descripcion:
            errores.append('La descripción es obligatoria.')
        
        try:
            precio = float(precio_raw)
            if precio < 0:
                raise ValueError
        except ValueError:
            errores.append('El precio debe ser un número positivo.')
        
        precio_proveedor = 0.0
        if precio_proveedor_raw:
            try:
                precio_proveedor = float(precio_proveedor_raw)
                if precio_proveedor < 0:
                    raise ValueError
            except ValueError:
                errores.append('El precio de proveedor debe ser un número positivo.')
        
        try:
            stock = int(stock_raw or 0)
            if stock < 0:
                raise ValueError
        except ValueError:
            errores.append('El stock debe ser un número entero mayor o igual a 0.')
        
        precio_oferta = None
        if precio_oferta_raw:
            try:
                precio_oferta = float(precio_oferta_raw)
                if precio_oferta < 0:
                    raise ValueError
            except ValueError:
                errores.append('El precio de oferta debe ser un número positivo.')
        
        imagenes_list = []
        if imagenes_raw:
            partes = [u.strip() for u in imagenes_raw.split(',')]
            imagenes_list = [u for u in partes if u]
        
        if errores:
            for e in errores:
                flash(e, 'danger')
        else:
            nuevo_id = crear_producto_exclusivo({
                'titulo': titulo,
                'descripcion': descripcion,
                'precio': precio,
                'precio_oferta': precio_oferta,
                'precio_proveedor': precio_proveedor,
                'categoria': categoria,
                'stock': stock,
                'estado': estado,
                'imagenes': imagenes_list,
                'mas_vendido': (request.form.get('mas_vendido') == 'on'),
                'link_proveedor': link_proveedor,
            })
            flash(f'✅ Producto exclusivo creado correctamente (ID {nuevo_id}).', 'success')
            app.logger.info(f'[PANEL_CREAR_EXCLUSIVO] Producto creado: {titulo} (ID: {nuevo_id})')
    
    except Exception as e:
        app.logger.error(f'[PANEL_CREAR_EXCLUSIVO] Error: {e}')
        flash('❌ Ocurrió un error al crear el producto exclusivo.', 'danger')
    
    return redirect(url_for('panel'))


# ============================================================================
# RUTAS DE ADMINISTRACIÓN DE CATEGORÍAS
# ============================================================================

@app.route('/admin/categorias')
def admin_categorias():
    """Listar todas las categorías"""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    
    categorias = obtener_categorias(activas=False)  # Mostrar todas, incluso inactivas
    return render_template('admin_categorias.html', categorias=categorias)


@app.route('/admin/categorias/crear', methods=['GET', 'POST'])
def admin_crear_categoria():
    """Crear nueva categoría"""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    
    if request.method == 'POST':
        nombre = (request.form.get('nombre') or '').strip()
        slug = (request.form.get('slug') or '').strip() or None
        descripcion = (request.form.get('descripcion') or '').strip() or None
        icono = (request.form.get('icono') or '').strip() or None
        color = (request.form.get('color') or '').strip() or None
        orden = int(request.form.get('orden') or 0)
        
        if not nombre:
            flash('El nombre de la categoría es obligatorio.', 'danger')
            return redirect(url_for('admin_categorias'))
        
        try:
            categoria = crear_categoria(nombre, slug, descripcion, icono, color, orden)
            flash(f'✅ Categoría "{nombre}" creada correctamente.', 'success')
            return redirect(url_for('admin_categorias'))
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(url_for('admin_categorias'))
        except Exception as e:
            flash(f'❌ Error al crear categoría: {e}', 'danger')
            return redirect(url_for('admin_categorias'))
    
    return redirect(url_for('admin_categorias'))


@app.route('/admin/categorias/<int:categoria_id>/editar', methods=['POST'])
def admin_editar_categoria(categoria_id):
    """Editar categoría existente"""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    
    nombre = (request.form.get('nombre') or '').strip()
    slug = (request.form.get('slug') or '').strip() or None
    descripcion = (request.form.get('descripcion') or '').strip() or None
    icono = (request.form.get('icono') or '').strip() or None
    color = (request.form.get('color') or '').strip() or None
    orden = int(request.form.get('orden') or 0)
    activa = request.form.get('activa') == 'true'
    
    if not nombre:
        flash('El nombre de la categoría es obligatorio.', 'danger')
        return redirect(url_for('admin_categorias'))
    
    try:
        campos = {
            'nombre': nombre,
            'slug': slug,
            'descripcion': descripcion,
            'icono': icono,
            'color': color,
            'orden': orden,
            'activa': activa
        }
        actualizar_categoria(categoria_id, campos)
        flash(f'✅ Categoría actualizada correctamente.', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    except Exception as e:
        flash(f'❌ Error al actualizar categoría: {e}', 'danger')
    
    return redirect(url_for('admin_categorias'))


@app.route('/admin/categorias/<int:categoria_id>/eliminar', methods=['POST'])
def admin_eliminar_categoria(categoria_id):
    """Eliminar (desactivar) categoría"""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    
    try:
        eliminar_categoria(categoria_id)
        flash('✅ Categoría desactivada correctamente.', 'success')
    except Exception as e:
        flash(f'❌ Error al eliminar categoría: {e}', 'danger')
    
    return redirect(url_for('admin_categorias'))


@app.route('/admin/productos-exclusivos/<int:producto_id>/toggle-mas-vendido', methods=['POST'])
def toggle_mas_vendido_producto_exclusivo(producto_id):
    """Alterna la marca 'mas_vendido' de un producto exclusivo"""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))

    producto = obtener_producto_exclusivo_por_id(producto_id)
    if not producto:
        flash('Producto no encontrado', 'danger')
        return redirect(url_for('listar_productos_exclusivos'))

    try:
        nuevo_valor = not bool(producto.get('mas_vendido'))
        actualizar_producto_exclusivo(producto_id, {'mas_vendido': nuevo_valor})
        action = 'marcado' if nuevo_valor else 'desmarcado'
        flash(f'✅ Producto {action} como Más Vendido.', 'success')
        app.logger.info(f'[TOGGLE_MAS_VENDIDO] Producto {producto_id} -> {nuevo_valor}')
    except Exception as e:
        app.logger.error(f'[TOGGLE_MAS_VENDIDO] Error: {e}')
        flash('❌ Error al actualizar la marca de "Más Vendido".', 'danger')

    if request.referrer and 'panel' in request.referrer:
        return redirect(url_for('panel'))
    return redirect(url_for('listar_productos_exclusivos'))


@app.route('/admin/productos-exclusivos/<int:producto_id>/eliminar', methods=['POST'])
def eliminar_producto_exclusivo(producto_id):
    """Inactivar un producto exclusivo (stock en 0)"""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar que el producto existe
        cur.execute("SELECT titulo FROM productos_vendedor WHERE id = %s", (producto_id,))
        producto = cur.fetchone()
        
        if not producto:
            flash('Producto no encontrado', 'danger')
            return redirect(url_for('panel'))
        
        # Inactivar el producto y dejar stock en 0
        cur.execute("""
            UPDATE productos_vendedor
            SET estado = 'inactivo', stock = 0
            WHERE id = %s
        """, (producto_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        flash(f'✅ Producto exclusivo "{producto["titulo"]}" inactivado correctamente.', 'success')
        app.logger.info(f'[INACTIVAR_EXCLUSIVO] Producto inactivado: ID {producto_id}')
        
    except Exception as e:
        app.logger.error(f'[INACTIVAR_EXCLUSIVO] Error: {e}')
        flash('❌ Error al inactivar el producto exclusivo.', 'danger')
    
    # Redirigir según desde dónde se llamó
    if request.referrer and 'panel' in request.referrer:
        return redirect(url_for('panel'))
    return redirect(url_for('listar_productos_exclusivos'))


@app.route('/admin/limpiar-productos-afiliados', methods=['POST'])
def limpiar_productos_afiliados():
    """Eliminar todos los productos afiliados de la base de datos"""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Contar productos antes de eliminar
        cur.execute("SELECT COUNT(*) as count FROM productos")
        count_before = cur.fetchone()['count']
        
        # Eliminar todos los productos afiliados
        cur.execute("DELETE FROM productos")
        conn.commit()
        
        cur.close()
        conn.close()
        
        flash(f'✅ Se eliminaron {count_before} producto(s) afiliado(s) de la base de datos.', 'success')
        app.logger.info(f'[LIMPIAR_AFILIADOS] Eliminados {count_before} productos afiliados')
        
    except Exception as e:
        app.logger.error(f'[LIMPIAR_AFILIADOS] Error: {e}')
        flash('❌ Error al limpiar productos afiliados.', 'danger')
    
    return redirect(url_for('panel'))


@app.route('/')
def index():
    # 🧹 Limpiar mensajes antiguos (evita flashes acumulados)
    session.pop('_flashes', None)

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 🎁 Cargar el sorteo más reciente (si existe)
        cur.execute("""
            SELECT s.id, s.titulo, s.descripcion, s.imagen,
                   COALESCE(b.cnt, 0) AS total_boletos
            FROM sorteos s
            LEFT JOIN (
                SELECT sorteo_id, COUNT(*) AS cnt
                FROM boletos
                GROUP BY sorteo_id
            ) b ON b.sorteo_id = s.id
            ORDER BY s.id DESC
            LIMIT 1;
        """)
        sorteo = cur.fetchone() or None  # Evita error si no hay sorteo

        cur.close()
        conn.close()

        app.logger.info('[INDEX] Productos y sorteo cargados correctamente desde la base de datos')

        # 🛒 Productos exclusivos de ShopFusion (desde archivo separado)
        # Si hay parámetros de búsqueda, filtrar productos
        termino_busqueda = request.args.get('q', '').strip()
        categoria_filtro = request.args.get('categoria', '').strip()
        
        if termino_busqueda or categoria_filtro:
            from services_exclusivos import buscar_productos
            productos_exclusivos = buscar_productos(
                termino_busqueda=termino_busqueda if termino_busqueda else None,
                categoria=categoria_filtro if categoria_filtro else None,
                limit=200
            )
            if productos_exclusivos:
                flash(f'Se encontraron {len(productos_exclusivos)} producto(s)', 'success')
            else:
                flash('No se encontraron productos con los criterios de búsqueda.', 'info')
        else:
            productos_exclusivos = obtener_productos_exclusivos()
        
        # 🔥 Obtener productos más vendidos (solo si no hay búsqueda activa)
        productos_mas_vendidos = []
        if not termino_busqueda and not categoria_filtro:
            from services_exclusivos import obtener_productos_mas_vendidos
            productos_mas_vendidos = obtener_productos_mas_vendidos(limit=12)

        # 📊 Organizar productos por categorías
        # Obtener TODAS las categorías de la base de datos en orden
        from services_categorias import obtener_categorias as obtener_categorias_completas
        todas_las_categorias = obtener_categorias_completas(activas=True)
        
        # Crear diccionario con todas las categorías en orden (nombre -> orden)
        categorias_orden_dict = {}
        for cat in todas_las_categorias:
            nombre_cat = cat.get('nombre', '')
            orden_cat = cat.get('orden', 999)
            categorias_orden_dict[nombre_cat] = orden_cat
        
        # Inicializar diccionario de productos por categoría
        productos_por_categoria = {}
        
        # Mapeo de variaciones de nombres de categorías a nombres oficiales
        mapeo_categorias = {}
        for cat in todas_las_categorias:
            nombre_oficial = cat.get('nombre', '')
            slug = cat.get('slug', '').lower()
            nombre_lower = nombre_oficial.lower()
            # Mapear variaciones comunes
            mapeo_categorias[nombre_lower] = nombre_oficial
            mapeo_categorias[slug] = nombre_oficial
            # Mapear sin acentos
            nombre_sin_acentos = nombre_oficial.lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
            mapeo_categorias[nombre_sin_acentos] = nombre_oficial
        
        # Agregar mapeos adicionales comunes
        mapeo_categorias.update({
            'tecnologia': 'Tecnología',
            'tecnologa': 'Tecnología',
            'electronica': 'Electrónica',
            'hogar y jardin': 'Hogar y Jardín',
            'hogar': 'Hogar y Jardín',
            'ropa': 'Ropa y Moda',
            'moda': 'Ropa y Moda',
            'salud': 'Salud y Bienestar',
            'audio': 'Audio y Sonido',
            'belleza': 'Belleza y Cuidado Personal',
            'fitness': 'Fitness y Deportes',
            'deportes': 'Fitness y Deportes',
            'educacion': 'Educación',
            'automotriz': 'Automotriz',
            'mascotas': 'Mascotas',
            'cocina': 'Cocina',
            'decoracion': 'Decoración',
            'iluminacion': 'Iluminación',
            'accesorios': 'Accesorios Tecnológicos'  # Por defecto
        })
        
        # Agrupar productos por categoría (normalizando case-insensitive)
        def normalizar_categoria_nombre(cat):
            """Normaliza el nombre de categoría para agrupar correctamente"""
            if not cat:
                return 'Otros'
            cat = cat.strip()
            cat_lower = cat.lower()
            
            # Buscar en el mapeo primero
            if cat_lower in mapeo_categorias:
                return mapeo_categorias[cat_lower]
            
            # Si coincide exactamente con alguna categoría oficial (case-insensitive)
            for nombre_oficial in categorias_orden_dict.keys():
                if nombre_oficial.lower() == cat_lower:
                    return nombre_oficial
            
            # Si no coincide, devolver con primera letra mayúscula
            return cat.capitalize() if cat else 'Otros'
        
        # Agrupar productos por categoría
        for producto in productos_exclusivos:
            categoria_raw = producto.get('categoria') or 'Otros'
            categoria = normalizar_categoria_nombre(categoria_raw)
            
            # Actualizar la categoría en el producto para consistencia
            producto['categoria'] = categoria
            
            if categoria not in productos_por_categoria:
                productos_por_categoria[categoria] = []
            productos_por_categoria[categoria].append(producto)
        
        # Crear lista de categorías ordenadas: primero las que tienen productos, en orden de la BD
        categorias_con_productos = []
        
        # Ordenar todas las categorías por su orden en la BD
        categorias_ordenadas_bd = sorted(categorias_orden_dict.items(), key=lambda x: x[1])
        
        # Agregar solo las categorías que tienen productos, manteniendo el orden de la BD
        for nombre_cat, orden_cat in categorias_ordenadas_bd:
            if nombre_cat in productos_por_categoria and len(productos_por_categoria[nombre_cat]) > 0:
                categorias_con_productos.append(nombre_cat)
        
        # Agregar categorías que no están en la BD pero tienen productos (al final)
        for categoria in productos_por_categoria.keys():
            if categoria not in categorias_con_productos and len(productos_por_categoria[categoria]) > 0:
                categorias_con_productos.append(categoria)

        # ⚡ Verificar si hay pago confirmado en la sesión
        pago_confirmado = session.pop('pago_confirmado', False)

        # 🧠 Mensajes de éxito específicos (si llega parámetro)
        boleto = request.args.get('boleto')
        if boleto:
            flash(
                f"🎟️ ¡Gracias por participar! Tu número de boleto es: {boleto}. "
                "Guárdalo. No te preocupes si lo pierdes: nosotros lo tenemos registrado "
                "y si eres el ganador te contactaremos.",
                "success"
            )

        # Verificar si hay producto para hacer scroll
        
        # 🚀 Renderizar la plantilla principal
        # Obtener todas las categorías para el buscador
        from services_categorias import obtener_categorias as obtener_categorias_completas
        categorias_todas = obtener_categorias_completas(activas=True)
        
        template_response = render_template(
            'index.html',
            productos_por_categoria=productos_por_categoria,
            categorias_con_productos=categorias_con_productos,
            categorias_todas=categorias_todas,
            productos_mas_vendidos=productos_mas_vendidos,
            form_newsletter=SubscribeForm(),
            form_contact=ContactForm(),
            sorteo=sorteo,
            paypal_client_id=PAYPAL_CLIENT_ID,
            pago_confirmado=pago_confirmado,
            termino_busqueda=termino_busqueda,
            categoria_filtro=categoria_filtro,
        )
        
        return template_response

    except psycopg.OperationalError as e:
        msg = f"[INDEX] Error de conexión a la base de datos: {e}"
        app.logger.error(msg)
        flash("⚠️ No se pudo conectar con la base de datos. Intente más tarde.", "danger")
        return render_template(
            'index.html',
            productos_por_categoria={},
            categorias_con_productos=[],
            form_newsletter=SubscribeForm(),
            form_contact=ContactForm(),
            sorteo=None,
            paypal_client_id=PAYPAL_CLIENT_ID,
            pago_confirmado=False,
        )

    except Exception as e:
        msg = f"[INDEX] Error inesperado: {e}"
        app.logger.error(msg)
        flash("⚠️ Ocurrió un error interno al cargar la página principal.", "danger")
        return render_template(
            'index.html',
            productos_por_categoria={},
            categorias_con_productos=[],
            form_newsletter=SubscribeForm(),
            form_contact=ContactForm(),
            sorteo=None,
            paypal_client_id=PAYPAL_CLIENT_ID,
            pago_confirmado=False,
        )


@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    form = ContactForm()
    if request.method == 'POST' and form.validate_on_submit():
        try:
            nombre = form.name.data
            email = form.email.data
            mensaje = form.message.data
            if not validar_correo(email):
                raise ValueError(f"[CONTACT] Correo inválido: {email}")
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO shopfusion.sugerencias (nombre, email, mensaje)
                VALUES (%s, %s, %s)
            """, (nombre, email, mensaje))
            conn.commit()
            cur.close()
            conn.close()
            flash('Mensaje enviado. ¡Te contactaremos pronto!', 'success')
            app.logger.info('[CONTACT] Mensaje enviado por: %s', email)
            return redirect(url_for('index'))
        except ValueError as ve:
            flash(str(ve), 'danger')
            app.logger.warning(str(ve))
            return redirect(url_for('contacto'))
        except psycopg.OperationalError as oe:
            msg = f"[CONTACT] Error de conexión a la base de datos: {str(oe)}"
            flash(msg, 'danger')
            app.logger.error(msg)
            return redirect(url_for('contacto'))
        except Exception as e:
            msg = f"[CONTACT] Error inesperado: {str(e)}"
            flash(msg, 'danger')
            app.logger.error(msg)
            return redirect(url_for('contacto'))
    app.logger.info('[CONTACTO] Acceso a la página de contacto')
    return render_template('contacto.html', form=form)

@app.route('/subscribe', methods=['POST'])
def subscribe():
    form = SubscribeForm()
    if form.validate_on_submit():
        try:
            email = form.email.data
            if not validar_correo(email):
                raise ValueError(f"[SUBSCRIBE] Correo inválido: {email}")
            flash('Suscripción exitosa. ¡Recibirás nuestras ofertas!', 'success')
            app.logger.info('[SUBSCRIBE] Suscripción exitosa: %s', email)
            return redirect(url_for('index'))
        except ValueError as ve:
            flash(str(ve), 'danger')
            app.logger.warning(str(ve))
            return redirect(url_for('index'))
        except Exception as e:
            msg = f"[SUBSCRIBE] Error inesperado: {str(e)}"
            flash(msg, 'danger')
            app.logger.error(msg)
            return redirect(url_for('index'))
    flash('Error en el formulario.', 'danger')
    return redirect(url_for('index'))

@app.route('/contact', methods=['POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        try:
            nombre = form.name.data
            email = form.email.data
            mensaje = form.message.data
            if not validar_correo(email):
                raise ValueError(f"[CONTACT] Correo inválido: {email}")
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO shopfusion.sugerencias (nombre, email, mensaje)
                VALUES (%s, %s, %s)
            """, (nombre, email, mensaje))
            conn.commit()
            cur.close()
            conn.close()
            flash('Mensaje enviado. ¡Te contactaremos pronto!', 'success')
            app.logger.info('[CONTACT] Mensaje enviado por: %s', email)
            return redirect(url_for('index'))
        except ValueError as ve:
            flash(str(ve), 'danger')
            app.logger.warning(str(ve))
            return redirect(url_for('index'))
        except psycopg.OperationalError as oe:
            msg = f"[CONTACT] Error de conexión a la base de datos: {str(oe)}"
            flash(msg, 'danger')
            app.logger.error(msg)
            return redirect(url_for('index'))
        except Exception as e:
            msg = f"[CONTACT] Error inesperado: {str(e)}"
            flash(msg, 'danger')
            app.logger.error(msg)
            return redirect(url_for('index'))
    flash('Error en el formulario.', 'danger')
    return redirect(url_for('index'))

@app.route('/privacidad')
def privacidad():
    app.logger.info('[PRIVACIDAD] Acceso a la página de privacidad')
    return render_template('privacidad.html')

@app.route('/terminos')
def terminos():
    app.logger.info('[TERMINOS] Acceso a la página de términos')
    return render_template('terminos.html')

@app.route('/buscar', methods=['GET'])
def buscar():
    """Buscador normal con filtros por categoría y término de búsqueda"""
    try:
        termino = request.args.get('q', '').strip()
        categoria = request.args.get('categoria', '').strip()
        
        # Buscar productos
        from services_exclusivos import buscar_productos
        productos = buscar_productos(
            termino_busqueda=termino if termino else None,
            categoria=categoria if categoria else None,
            limit=100
        )
        
        # Obtener categorías para el filtro
        categorias_todas = obtener_categorias(activas=True)
        
        # Si es una petición AJAX, devolver JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            productos_data = []
            for p in productos:
                precio_final = p.get('precio_oferta') if (p.get('precio_oferta') and p.get('precio_oferta') < p.get('precio')) else p.get('precio')
                productos_data.append({
                    'id': p.get('id'),
                    'titulo': p.get('titulo'),
                    'descripcion': p.get('descripcion'),
                    'precio': float(precio_final),
                    'precio_original': float(p.get('precio', 0)),
                    'categoria': p.get('categoria'),
                    'stock': p.get('stock'),
                    'imagenes': p.get('imagenes', [])
                })
            return jsonify({
                'productos': productos_data,
                'total': len(productos_data)
            })
        
        # Si no es AJAX, redirigir a index con parámetros de búsqueda para mostrar resultados filtrados
        params = {}
        if termino:
            params['q'] = termino
        if categoria:
            params['categoria'] = categoria
        return redirect(url_for('index', **params))
    except Exception as e:
        app.logger.error(f"[BUSCAR] Error: {e}")
        flash('Error al realizar la búsqueda. Por favor, intenta nuevamente.', 'danger')
        return redirect(url_for('index'))

@app.route('/buscar_inteligente', methods=['POST'])
@limiter.limit("30 per minute")  # Máximo 30 búsquedas por minuto por IP
def buscar_inteligente():
    try:
        # Intentar obtener datos JSON, si no, intentar form-data
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict()
        
        consulta = data.get('query', '').strip()
        if not consulta:
            return jsonify({'error': 'La consulta no puede estar vacía'}), 400

        consulta_lower = consulta.lower()

        # === Cargar productos exclusivos de ShopFusion ===
        try:
            exclusivos_raw = obtener_productos_exclusivos() or []
        except Exception as e:
            app.logger.error(f"[BUSCAR_INTELIGENTE] Error al obtener exclusivos: {e}")
            exclusivos_raw = []

        app.logger.info(f"[BUSCAR_INTELIGENTE] Productos exclusivos obtenidos: {len(exclusivos_raw)}")

        # === 2) Normalizar catálogo de exclusivos ===
        catalogo = []

        # Normalizar EXCLUSIVOS
        for p in exclusivos_raw:
            pid = p.get('id')
            if pid is None:
                continue

            nombre = p.get('titulo') or p.get('nombre') or ''
            descripcion = p.get('descripcion') or ''
            categoria = p.get('categoria') or 'Exclusivo'
            precio = p.get('precio_oferta') or p.get('precio') or 0
            imagenes = p.get('imagenes') or []
            link = p.get('link') or p.get('url') or '#'

            catalogo.append({
                'uid': f"EXC-{pid}",
                'id': pid,
                'source': 'exclusivo',
                'nombre': nombre,
                'descripcion': descripcion,
                'categoria': categoria,
                'afiliacion': 'ShopFusion Exclusivo',
                'precio': float(precio) if precio is not None else 0.0,
                'link': link,
                'imagenes': imagenes,
            })

        if not catalogo:
            return jsonify({
                'productos': [],
                'mensaje': 'Por el momento no hay productos en el catálogo.'
            })

        # === 3) Coincidencias LITERALES (para cosas tipo "pantalla curva") ===
        exact_matches = [
            item for item in catalogo
            if consulta_lower in f"{item['nombre']} {item['descripcion']} {item['categoria']}".lower()
        ]

        def prioridad(item):
            # Todos son exclusivos
            return 0

        if exact_matches:
            exact_matches.sort(key=prioridad)
            seleccion = exact_matches[:10]

            resultados = [
                {
                    'id': item['id'],
                    'nombre': item['nombre'],
                    'descripcion': item['descripcion'],
                    'precio': item['precio'],
                    'afiliacion': item['afiliacion'],
                    'link': item['link'],
                    'imagenes': item['imagenes'],
                    'categoria': item['categoria'],
                    'es_exclusivo': item['source'] == 'exclusivo'
                }
                for item in seleccion
            ]

            return jsonify({
                'productos': resultados,
                'mensaje': f"Mostrando {len(resultados)} resultado(s) que coinciden literalmente con “{consulta}”."
            })

        # === 4) Sin coincidencias literales → usar IA para sugerencias relacionadas ===
        # (caso "celular" sin celulares, pero sí accesorios, etc.)
        if not openai_client:
            return jsonify({
                'productos': [],
                'mensaje': 'Busqueda inteligente no disponible. Configura OPENAI_API_KEY para habilitarla.'
            })
        productos_texto = [
            (
                f"UID: {item['uid']}, "
                f"Tipo: EXCLUSIVO, "
                f"Nombre: {item['nombre']}, "
                f"Descripción: {item['descripcion']}, "
                f"Categoría: {item['categoria']}, "
                f"Afiliación: {item['afiliacion']}"
            )
            for item in catalogo
        ]

        valid_uids = [item['uid'] for item in catalogo]

        prompt = f"""
Eres un asistente experto en búsqueda y recomendación de productos de una tienda online llamada ShopFusion.

Debes analizar la búsqueda del usuario y devolver los productos más relevantes del catálogo.
No inventes productos ni IDs.

### Catálogo disponible (cada producto tiene un UID único):
{json.dumps(productos_texto, ensure_ascii=False)}

### Instrucciones:
1. Interpreta la intención del usuario incluso si escribe frases largas, coloquiales o con errores.
2. Busca relaciones semánticas entre la consulta y los productos listados.
3. Devuelve **solo** un JSON válido con la forma:
   {{"ids": ["EXC-1", "EXC-5", "EXC-3"]}}
5. Los valores de "ids" deben ser únicamente UIDs incluidos en esta lista:
   {valid_uids}
6. No incluyas texto adicional, ni comentarios, ni bloques de código Markdown. Solo el JSON.
7. Devuelve hasta un máximo de 10 productos.

Consulta del usuario:
"{consulta}"
"""

        response = openai_client.ChatCompletion.create(
            model="gpt-3.5-turbo",  # puedes cambiar a otro modelo si quieres
            messages=[
                {
                    "role": "system",
                    "content": "Eres un motor de búsqueda semántico experto que entiende el lenguaje humano y devuelve únicamente JSON válido."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=250
        )

        response_content = response.choices[0].message['content'].strip()
        # No loguear el contenido completo de la respuesta para evitar exponer datos
        app.logger.info(f"[BUSCAR_INTELIGENTE] Respuesta recibida de OpenAI (longitud: {len(response_content)})")

        # Limpiar posibles ```json .. ``` del modelo
        cleaned = response_content.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        if cleaned.startswith('```'):
            cleaned = cleaned[3:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Parsear JSON
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                relevant_uids = parsed.get("ids") or parsed.get("productos_relevantes") or []
            elif isinstance(parsed, list):
                # compatibilidad si solo devuelve lista
                relevant_uids = parsed
            else:
                app.logger.error(f"[BUSCAR_INTELIGENTE] Formato JSON no soportado: {parsed}")
                relevant_uids = []
        except json.JSONDecodeError as e:
            app.logger.error(f"[BUSCAR_INTELIGENTE] Error al parsear JSON: {e} | Respuesta: {cleaned}")
            relevant_uids = []

        # Filtrar UIDs inválidos
        relevant_uids = [uid for uid in relevant_uids if uid in valid_uids]
        app.logger.info(f"[BUSCAR_INTELIGENTE] UIDs relevantes filtrados: {relevant_uids}")

        if not relevant_uids:
            return jsonify({
                'productos': [],
                'mensaje': (
                    f"No encontramos productos con el término exacto “{consulta}”, "
                    "y por ahora tampoco hay sugerencias cercanas en el catálogo. "
                    "Prueba con otra palabra o revisa nuestro catálogo completo. "
                    "NOTA: Si el problema persiste, informa a soporte técnico o envía una sugerencia."
                )
            })

        # Mapear UIDs → productos y respetar el orden
        uid_to_item = {item['uid']: item for item in catalogo}
        seleccion = [uid_to_item[uid] for uid in relevant_uids if uid in uid_to_item]

        # Ordenar por prioridad (por si el modelo no lo respetó)
        seleccion.sort(key=prioridad)
        seleccion = seleccion[:10]

        resultados = [
            {
                'id': item['id'],
                'nombre': item['nombre'],
                'descripcion': item['descripcion'],
                'precio': item['precio'],
                'afiliacion': item['afiliacion'],
                'link': item['link'],
                'imagenes': item['imagenes'],
                'categoria': item['categoria'],
                'es_exclusivo': item['source'] == 'exclusivo'
            }
            for item in seleccion
        ]

        return jsonify({
            'productos': resultados,
            'mensaje': (
                f"No tenemos productos exactamente llamados “{consulta}”, "
                f"pero encontramos {len(resultados)} artículo(s) relacionados "
                "que podrían interesarte."
            )
        })

    except Exception as e:
        msg = f"[BUSCAR_INTELIGENTE] Error inesperado: {str(e)}"
        app.logger.error(msg)
        return jsonify({'error': 'Error inesperado en la búsqueda'}), 500

@app.route('/health')
def health():
    """Endpoint de salud para utilizar en servicios de deploy (Render, Heroku, etc.)"""
    return jsonify({'status': 'ok', 'env': 'production' if is_production else 'development'}), 200


@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    error_msg = str(e)
    app.logger.error(f"[CSRF] ❌❌❌ ERROR CSRF DETECTADO ❌❌❌")
    app.logger.error(f"[CSRF] IP={request.remote_addr}, URL={request.url}, Error: {error_msg}")
    form_keys = list(request.form.keys()) if request.form else []
    session_keys = list(session.keys())
    app.logger.error(f"[CSRF] Metodo: {request.method}, form_keys: {form_keys}")
    app.logger.error(f"[CSRF] Session keys: {session_keys}")
    
    flash(f'❌ Error de seguridad (CSRF): {error_msg}. Por favor, recarga la página e intenta nuevamente.', 'danger')
    
    # Si es admin, redirigir a admin con mensaje claro
    if '/admin' in request.url or '/admin' in request.path:
        app.logger.info('[CSRF] Redirigiendo a admin después de error CSRF')
        return redirect(url_for('admin'))
    return redirect(url_for('index'))

# Handler para errores de rate limiting
@app.errorhandler(429)
def handle_rate_limit(e):
    """Maneja errores 429 (Too Many Requests) de Flask-Limiter"""
    app.logger.warning(f"[RATE_LIMIT] Límite excedido: IP={request.remote_addr}, URL={request.url}")
    if request.is_json:
        return jsonify({
            'error': 'Has realizado demasiadas solicitudes. Por favor, espera un momento antes de intentar nuevamente.'
        }), 429
    
    # Evitar bucles infinitos - no redirigir a la misma URL si ya estamos en rate limit
    flash('Has realizado demasiadas solicitudes. Por favor, espera un momento antes de intentar nuevamente.', 'warning')
    
    # Si es una ruta de registro/login, redirigir a index, sino mantener en la misma página pero mostrar error
    if '/registro' in request.path or '/login' in request.path:
        return redirect(url_for('index'))
    
    # Para otras rutas, renderizar una página de error o redirigir a index
    return redirect(url_for('index'))


@app.route('/vendedores_info')
def vendedores_info():
    return render_template('vendedores_info.html')

from flask_wtf.csrf import generate_csrf, validate_csrf
from wtforms.validators import ValidationError  # opcional para capturar errores

from flask_wtf.csrf import generate_csrf, validate_csrf
import re

USERNAME_RE = re.compile(r'^[a-z0-9._-]{3,32}$')
FRECUENCIAS = {'semanal', 'quincenal', 'mensual'}

@app.route('/registro_vendedor', methods=['GET', 'POST'])
@limiter.limit("3 per hour")  # Maximo 3 registros por hora por IP
def registro_vendedor():
    # Redirigir a la página de proveedores con información y contacto (WhatsApp)
    return redirect(url_for('proveedores'))


from flask import render_template, request, redirect, url_for, flash, session
from flask_wtf.csrf import generate_csrf, validate_csrf
from werkzeug.security import check_password_hash

@app.route('/login_vendedor', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Maximo 5 intentos de login por minuto
def login_vendedor():
    # Redirigir a la página de proveedores con información y contacto (WhatsApp)
    return redirect(url_for('proveedores'))


# ========= Helpers y guard de vendedor =========
from functools import wraps
from datetime import datetime, timedelta

def vendedor_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get('rol') != 'vendedor' or not session.get('vendedor_id'):
            if request.accept_mimetypes.accept_json:
                return jsonify({'error':'No autorizado', 'detail':'Inicia sesión como vendedor'}), 401
            flash('Debes iniciar sesión como vendedor.', 'danger')
            return redirect(url_for('login_vendedor'))
        return fn(*args, **kwargs)
    return wrapper

def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [s.strip() for s in value.split(",") if s.strip()]
    return list(value)

def is_url(s):
    return bool(re.match(r'^https?://', s or ''))

def now_utc():
    return datetime.utcnow()

# ========= Panel (vista HTML contenedor) =========
@app.route('/vendedor/panel')
@vendedor_required
def vendedor_panel():
    # Renderiza tu layout de panel; usa tu HTML existente o uno de placeholder
    # Debe incluir los assets: static/css/panel_vendedor.css y static/js/panel_vendedor.js
    return render_template('panel_vendedor.html',
                           vendedor_nombre=session.get('vendedor_nombre'),
                           vendedor_username=session.get('vendedor_username'))

# ========= Perfil básico del vendedor =========
@app.get('/api/vendedor/me')
@vendedor_required
def vendedor_me():
    vid = session['vendedor_id']
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, nombre_comercial, email, telefono, ciudad, direccion,
                       metodo_pago, banco, tipo_cuenta, numero_cuenta, paypal_email,
                       frecuencia_retiro, estado, creado_en
                FROM vendedores_ecuador
                WHERE id = %s
            """, (vid,))
            me = cur.fetchone()
        conn.close()
        if not me:
            return jsonify({'error':'No encontrado'}), 404
        return jsonify({'vendedor': me})
    except Exception as e:
        app.logger.error(f"[VND_ME] {e}")
        return jsonify({'error':'Error interno'}), 500

# ========= PRODUCTOS (CRUD con imágenes y videos) =========
# Asume tabla: productos_vendedor(
#   id serial pk, vendedor_id int, titulo text, descripcion text, precio numeric,
#   categoria text, estado text, imagenes jsonb, videos jsonb,
#   sku text, stock int, created_at timestamp, updated_at timestamp
# )

@app.get('/api/vendedor/productos')
@vendedor_required
def vnd_list_productos():
    vid = session['vendedor_id']
    q = (request.args.get('q') or '').strip()
    estado = (request.args.get('estado') or '').strip()
    categoria = (request.args.get('categoria') or '').strip()
    page = int(request.args.get('page', 1))
    per_page = min(max(int(request.args.get('per_page', 10)), 1), 100)
    off = (page-1)*per_page
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            where = ["vendedor_id=%s"]
            params = [vid]
            if q:
                where.append("(unaccent(lower(titulo)) LIKE unaccent(lower(%s)) OR unaccent(lower(descripcion)) LIKE unaccent(lower(%s)))")
                like = f"%{q}%"
                params += [like, like]
            if estado:
                where.append("estado=%s"); params.append(estado)
            if categoria:
                where.append("categoria=%s"); params.append(categoria)

            where_sql = " AND ".join(where)
            cur.execute(f"SELECT COUNT(*) AS c FROM productos_vendedor WHERE {where_sql}", params)
            total = cur.fetchone()['c']

            cur.execute(f"""
                SELECT id, titulo, descripcion, precio, categoria, estado, imagenes, videos,
                       sku, stock, created_at, updated_at
                FROM productos_vendedor
                WHERE {where_sql}
                ORDER BY id DESC
                LIMIT %s OFFSET %s
            """, params + [per_page, off])
            rows = cur.fetchall()
        conn.close()
        return jsonify({
            'items': rows,
            'page': page, 'per_page': per_page, 'total': total
        })
    except Exception as e:
        app.logger.error(f"[VND_PROD_LIST] {e}")
        return jsonify({'error':'Error al listar productos'}), 500

@app.get('/api/vendedor/productos/<int:pid>')
@vendedor_required
def vnd_get_producto(pid):
    vid = session['vendedor_id']
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
              SELECT id, titulo, descripcion, precio, categoria, estado, imagenes, videos,
                     sku, stock, created_at, updated_at
              FROM productos_vendedor
              WHERE id=%s AND vendedor_id=%s
            """, (pid, vid))
            row = cur.fetchone()
        conn.close()
        if not row:
            return jsonify({'error':'No encontrado'}), 404
        return jsonify({'item': row})
    except Exception as e:
        app.logger.error(f"[VND_PROD_GET] {e}")
        return jsonify({'error':'Error al obtener producto'}), 500

@app.post('/api/vendedor/productos')
@vendedor_required
def vnd_create_producto():
    vid = session['vendedor_id']
    try:
        data = request.get_json(force=True) or {}
        titulo = (data.get('titulo') or '').strip()
        descripcion = (data.get('descripcion') or '').strip()
        precio = float(data.get('precio') or 0)
        categoria = (data.get('categoria') or '').strip() or 'General'
        estado = (data.get('estado') or '').strip() or 'draft'
        imagenes = [u for u in as_list(data.get('imagenes')) if is_url(u)]
        videos = [u for u in as_list(data.get('videos')) if is_url(u)]
        sku = (data.get('sku') or '').strip() or None
        stock = int(data.get('stock') or 0)

        if not titulo or precio < 0:
            return jsonify({'error':'Título y precio son obligatorios'}), 400

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
              INSERT INTO productos_vendedor
                (vendedor_id, titulo, descripcion, precio, categoria, estado,
                 imagenes, videos, sku, stock, created_at, updated_at)
              VALUES
                (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s, NOW(), NOW())
              RETURNING id
            """, (vid, titulo, descripcion, precio, categoria, estado,
                  json.dumps(imagenes), json.dumps(videos), sku, stock))
            new_id = cur.fetchone()['id']
            conn.commit()
        conn.close()
        return jsonify({'ok': True, 'id': new_id}), 201
    except Exception as e:
        app.logger.error(f"[VND_PROD_CREATE] {e}")
        return jsonify({'error':'Error al crear producto'}), 500

@app.put('/api/vendedor/productos/<int:pid>')
@vendedor_required
def vnd_update_producto(pid):
    vid = session['vendedor_id']
    try:
        data = request.get_json(force=True) or {}
        fields = []
        params = []

        def setf(col, val):
            fields.append(f"{col}=%s"); params.append(val)

        if 'titulo' in data: setf('titulo', (data.get('titulo') or '').strip())
        if 'descripcion' in data: setf('descripcion', (data.get('descripcion') or '').strip())
        if 'precio' in data:
            precio = float(data.get('precio') or 0)
            if precio < 0: return jsonify({'error':'Precio inválido'}), 400
            setf('precio', precio)
        if 'categoria' in data: setf('categoria', (data.get('categoria') or '').strip())
        if 'estado' in data: setf('estado', (data.get('estado') or '').strip())
        if 'imagenes' in data:
            imgs = [u for u in as_list(data.get('imagenes')) if is_url(u)]
            setf('imagenes', json.dumps(imgs))
        if 'videos' in data:
            vids = [u for u in as_list(data.get('videos')) if is_url(u)]
            setf('videos', json.dumps(vids))
        if 'sku' in data: setf('sku', (data.get('sku') or '').strip() or None)
        if 'stock' in data: setf('stock', int(data.get('stock') or 0))

        if not fields:
            return jsonify({'error':'Sin cambios'}), 400

        params += [pid, vid]
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(f"""
              UPDATE productos_vendedor
              SET {', '.join(fields)}, updated_at=NOW()
              WHERE id=%s AND vendedor_id=%s
              RETURNING id
            """, params)
            row = cur.fetchone()
            if not row:
                conn.rollback()
                conn.close()
                return jsonify({'error':'No encontrado'}), 404
            conn.commit()
        conn.close()
        return jsonify({'ok': True, 'id': pid})
    except Exception as e:
        app.logger.error(f"[VND_PROD_UPDATE] {e}")
        return jsonify({'error':'Error al actualizar producto'}), 500

@app.delete('/api/vendedor/productos/<int:pid>')
@vendedor_required
def vnd_delete_producto(pid):
    vid = session['vendedor_id']
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
              DELETE FROM productos_vendedor
              WHERE id=%s AND vendedor_id=%s
              RETURNING id
            """, (pid, vid))
            row = cur.fetchone()
            if not row:
                conn.rollback()
                conn.close()
                return jsonify({'error':'No encontrado'}), 404
            conn.commit()
        conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        app.logger.error(f"[VND_PROD_DELETE] {e}")
        return jsonify({'error':'Error al eliminar producto'}), 500

# ========= INVENTARIO (ajustes rápidos) =========
@app.get('/api/vendedor/inventario')
@vendedor_required
def vnd_inventario_list():
    vid = session['vendedor_id']
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
              SELECT id, sku, titulo, stock
              FROM productos_vendedor
              WHERE vendedor_id=%s
              ORDER BY id DESC
            """, (vid,))
            rows = cur.fetchall()
        conn.close()
        return jsonify({'items': rows})
    except Exception as e:
        app.logger.error(f"[VND_INV_LIST] {e}")
        return jsonify({'error':'Error al listar inventario'}), 500

@app.post('/api/vendedor/inventario/ajustar')
@vendedor_required
def vnd_inventario_ajustar():
    vid = session['vendedor_id']
    try:
        data = request.get_json(force=True) or {}
        pid = int(data.get('producto_id') or 0)
        delta = int(data.get('delta') or 0)
        if not pid or delta == 0:
            return jsonify({'error':'producto_id y delta son requeridos'}), 400
        conn = get_db_connection()
        with conn.cursor() as cur:
            # opcional: registrar en una tabla de movimientos_inventario
            cur.execute("""
              UPDATE productos_vendedor
              SET stock = GREATEST(0, COALESCE(stock,0) + %s), updated_at=NOW()
              WHERE id=%s AND vendedor_id=%s
              RETURNING id, stock
            """, (delta, pid, vid))
            row = cur.fetchone()
            if not row:
                conn.rollback(); conn.close()
                return jsonify({'error':'No encontrado'}), 404
            conn.commit()
        conn.close()
        return jsonify({'ok': True, 'producto_id': row['id'], 'stock': row['stock']})
    except Exception as e:
        app.logger.error(f"[VND_INV_AJUSTE] {e}")
        return jsonify({'error':'Error al ajustar inventario'}), 500

# ========= PEDIDOS (listado y cambio de estado) =========
# Asume tabla pedidos_vendedor con vendedor_id y columnas estado, total, creado_en, etc.

@app.get('/api/vendedor/pedidos')
@vendedor_required
def vnd_pedidos_list():
    vid = session['vendedor_id']
    status = (request.args.get('status') or '').strip()
    dt_from = request.args.get('from')
    dt_to = request.args.get('to')
    page = int(request.args.get('page', 1))
    per_page = min(max(int(request.args.get('per_page', 10)), 1), 100)
    off = (page-1)*per_page
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            where = ["vendedor_id=%s"]; params=[vid]
            if status:
                where.append("estado=%s"); params.append(status)
            if dt_from:
                where.append("creado_en >= %s"); params.append(dt_from)
            if dt_to:
                where.append("creado_en < %s"); params.append(dt_to)

            where_sql = " AND ".join(where)
            cur.execute(f"SELECT COUNT(*) c FROM pedidos_vendedor WHERE {where_sql}", params)
            total = cur.fetchone()['c']

            cur.execute(f"""
              SELECT id, numero, estado, total, moneda, cliente_nombre, creado_en
              FROM pedidos_vendedor
              WHERE {where_sql}
              ORDER BY id DESC
              LIMIT %s OFFSET %s
            """, params + [per_page, off])
            rows = cur.fetchall()
        conn.close()
        return jsonify({'items': rows, 'page': page, 'per_page': per_page, 'total': total})
    except Exception as e:
        app.logger.error(f"[VND_ORDERS_LIST] {e}")
        return jsonify({'error':'Error al listar pedidos'}), 500

@app.put('/api/vendedor/pedidos/<int:oid>/estado')
@vendedor_required
def vnd_pedido_estado(oid):
    vid = session['vendedor_id']
    try:
        data = request.get_json(force=True) or {}
        nuevo = (data.get('estado') or '').strip()
        if nuevo not in ('nuevo','pagado','enviado','entregado','cancelado'):
            return jsonify({'error':'Estado inválido'}), 400
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
              UPDATE pedidos_vendedor
              SET estado=%s
              WHERE id=%s AND vendedor_id=%s
              RETURNING id
            """, (nuevo, oid, vid))
            row = cur.fetchone()
            if not row:
                conn.rollback(); conn.close()
                return jsonify({'error':'No encontrado'}), 404
            conn.commit()
        conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        app.logger.error(f"[VND_ORDER_STATE] {e}")
        return jsonify({'error':'Error al actualizar estado'}), 500

# ========= VENTAS / MÉTRICAS =========
# devuelve KPIs y serie por día

@app.get('/api/vendedor/ventas/resumen')
@vendedor_required
def vnd_ventas_resumen():
    vid = session['vendedor_id']
    rng = (request.args.get('range') or '30d').lower()
    dt_from = request.args.get('from')
    dt_to = request.args.get('to')

    today = datetime.utcnow().date()
    if rng == '7d':
        start = today - timedelta(days=6)
        end = today + timedelta(days=1)
    elif rng == '30d':
        start = today - timedelta(days=29)
        end = today + timedelta(days=1)
    elif rng == 'custom' and dt_from and dt_to:
        start = datetime.fromisoformat(dt_from).date()
        end = datetime.fromisoformat(dt_to).date() + timedelta(days=1)
    else:
        start = today - timedelta(days=29); end = today + timedelta(days=1)

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # total ventas y pedidos
            cur.execute("""
              SELECT COALESCE(SUM(total),0) as ventas, COUNT(*) as pedidos
              FROM pedidos_vendedor
              WHERE vendedor_id=%s AND estado IN ('pagado','enviado','entregado')
                AND creado_en >= %s AND creado_en < %s
            """, (vid, start, end))
            kpi = cur.fetchone()

            # serie por día
            cur.execute("""
              SELECT DATE(creado_en) d, COALESCE(SUM(total),0) total, COUNT(*) pedidos
              FROM pedidos_vendedor
              WHERE vendedor_id=%s AND estado IN ('pagado','enviado','entregado')
                AND creado_en >= %s AND creado_en < %s
              GROUP BY 1
              ORDER BY 1
            """, (vid, start, end))
            series = cur.fetchall()
        conn.close()
        return jsonify({'kpi': kpi, 'series': series, 'from': str(start), 'to': str(end)})
    except Exception as e:
        app.logger.error(f"[VND_SALES_SUM] {e}")
        return jsonify({'error':'Error al obtener métricas'}), 500

# ========= NOTIFICACIONES =========
# Asume notificaciones_vendedor(id, vendedor_id, titulo, cuerpo, created_at, leido bool)

@app.get('/api/vendedor/notificaciones')
@vendedor_required
def vnd_notif_list():
    vid = session['vendedor_id']
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
              SELECT id, titulo, cuerpo, created_at, leido
              FROM notificaciones_vendedor
              WHERE vendedor_id=%s
              ORDER BY created_at DESC
              LIMIT 100
            """, (vid,))
            rows = cur.fetchall()
        conn.close()
        return jsonify({'items': rows})
    except Exception as e:
        app.logger.error(f"[VND_NOTIF_LIST] {e}")
        return jsonify({'error':'Error al listar notificaciones'}), 500

@app.post('/api/vendedor/notificaciones/<int:nid>/leido')
@vendedor_required
def vnd_notif_mark_read(nid):
    vid = session['vendedor_id']
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
              UPDATE notificaciones_vendedor
              SET leido=TRUE
              WHERE id=%s AND vendedor_id=%s
              RETURNING id
            """, (nid, vid))
            row = cur.fetchone()
            if not row:
                conn.rollback(); conn.close()
                return jsonify({'error':'No encontrado'}), 404
            conn.commit()
        conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        app.logger.error(f"[VND_NOTIF_READ] {e}")
        return jsonify({'error':'Error al actualizar notificación'}), 500

# ========= CONFIGURACIÓN BÁSICA =========
# Asume config_vendedor(vendedor_id pk, zona_envio text, tiempo_envio text, politicas text)

@app.get('/api/vendedor/config')
@vendedor_required
def vnd_config_get():
    vid = session['vendedor_id']
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
              SELECT vendedor_id, zona_envio, tiempo_envio, politicas
              FROM config_vendedor
              WHERE vendedor_id=%s
            """, (vid,))
            row = cur.fetchone()
        conn.close()
        return jsonify({'config': row or {
            'vendedor_id': vid, 'zona_envio': None, 'tiempo_envio': None, 'politicas': None
        }})
    except Exception as e:
        app.logger.error(f"[VND_CFG_GET] {e}")
        return jsonify({'error':'Error al obtener configuración'}), 500

@app.put('/api/vendedor/config')
@vendedor_required
def vnd_config_update():
    vid = session['vendedor_id']
    try:
        data = request.get_json(force=True) or {}
        zona = (data.get('zona_envio') or '').strip() or None
        tiempo = (data.get('tiempo_envio') or '').strip() or None
        politicas = (data.get('politicas') or '').strip() or None

        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM config_vendedor WHERE vendedor_id=%s", (vid,))
            exists = cur.fetchone() is not None
            if exists:
                cur.execute("""
                  UPDATE config_vendedor
                  SET zona_envio=%s, tiempo_envio=%s, politicas=%s
                  WHERE vendedor_id=%s
                """, (zona, tiempo, politicas, vid))
            else:
                cur.execute("""
                  INSERT INTO config_vendedor (vendedor_id, zona_envio, tiempo_envio, politicas)
                  VALUES (%s,%s,%s,%s)
                """, (vid, zona, tiempo, politicas))
            conn.commit()
        conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        app.logger.error(f"[VND_CFG_UPD] {e}")
        return jsonify({'error':'Error al guardar configuración'}), 500




# ============================================================================
# RUTAS DEL SISTEMA DE AFILIADOS
# ============================================================================

@app.route('/afiliados/registro', methods=['GET', 'POST'])
@limiter.limit("3 per hour")  # Máximo 3 registros por hora por IP
def afiliados_registro():
    """Registro de nuevos afiliados"""
    form = AfiliadoRegistroForm()
    
    if form.validate_on_submit():
        try:
            nombre = form.nombre.data.strip()
            email = form.email.data.strip().lower()
            password = form.password.data
            
            # Crear afiliado
            comision_default = 10.0
            try:
                conn_cfg = get_db_connection()
                with conn_cfg.cursor() as cur:
                    cur.execute("""
                        SELECT valor FROM shopfusion.configuracion_sistema
                        WHERE clave = 'comision_predeterminada'
                        LIMIT 1
                    """)
                    cfg = cur.fetchone()
                    if cfg and cfg.get('valor') is not None:
                        comision_default = float(cfg.get('valor'))
            except Exception as e:
                app.logger.warning(f"[AFILIADOS_REGISTRO] No se pudo leer comisión predeterminada, usando {comision_default}: {e}")
            finally:
                try:
                    conn_cfg.close()
                except Exception:
                    pass
            
            resultado = crear_afiliado(
                nombre=nombre,
                email=email,
                password_hash=generate_password_hash(password),
                comision_porcentaje=comision_default  # Comisión definida por admin
            )
            
            flash(f'✅ ¡Registro exitoso! Tu código de afiliado es: {resultado["codigo_afiliado"]}', 'success')
            return redirect(url_for('afiliados_login'))
            
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            app.logger.error(f"[AFILIADOS_REGISTRO] Error: {e}")
            flash('Error al registrar. Intenta nuevamente.', 'danger')
    
    return render_template('afiliados_registro.html', form=form)


@app.route('/afiliados/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Máximo 5 intentos de login por minuto
def afiliados_login():
    """Login de afiliados"""
    if session.get('afiliado_auth'):
        return redirect(url_for('afiliados_panel'))
    
    form = AfiliadoLoginForm()
    
    if form.validate_on_submit():
        try:
            email = form.email.data.strip().lower()
            password = form.password.data
            
            afiliado = obtener_afiliado_por_email(email)
            
            if afiliado and check_password_hash(afiliado['password_hash'], password):
                if afiliado['estado'] != 'activo':
                    flash('Tu cuenta de afiliado está inactiva. Contacta al administrador.', 'warning')
                    return redirect(url_for('afiliados_login'))
                
                session['afiliado_id'] = afiliado['id']
                session['afiliado_nombre'] = afiliado['nombre']
                session['afiliado_codigo'] = afiliado['codigo_afiliado']
                session['afiliado_email'] = afiliado['email']
                session['afiliado_comision'] = afiliado['comision_porcentaje']
                session['afiliado_auth'] = True
                
                # Migrar carrito de cookies a BD si existe
                carrito_cookies = session.get('carrito', [])
                if carrito_cookies:
                    migrar_carrito_cookies_a_bd_afiliado(afiliado['id'], carrito_cookies)
                    session.pop('carrito', None)  # Limpiar carrito de cookies
                
                session.modified = True
                
                flash(f'¡Bienvenido, {afiliado["nombre"]}!', 'success')
                return redirect(url_for('afiliados_panel'))
            else:
                flash('Email o contraseña incorrectos. Si eres cliente, usa el login principal.', 'danger')
                
        except Exception as e:
            app.logger.error(f"[AFILIADOS_LOGIN] Error: {e}")
            flash('Error al iniciar sesión. Intenta nuevamente.', 'danger')
    
    return render_template('afiliados_login.html', form=form)


@app.route('/afiliados/logout')
def afiliados_logout():
    """Cerrar sesión de afiliado"""
    session.pop('afiliado_id', None)
    session.pop('afiliado_nombre', None)
    session.pop('afiliado_codigo', None)
    session.pop('afiliado_email', None)
    session.pop('afiliado_auth', None)
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('index'))


@app.route('/afiliados/panel')
def afiliados_panel():
    """Panel de control del afiliado"""
    if 'afiliado_id' not in session or not session.get('afiliado_auth'):
        flash('Debes iniciar sesión para acceder al panel', 'warning')
        return redirect(url_for('afiliados_login'))
    
    try:
        afiliado_id = session['afiliado_id']
        estadisticas = obtener_estadisticas_afiliado(afiliado_id)
        
        # Obtener datos del afiliado (usar función de services_afiliados que tiene el esquema configurado)
        from services_afiliados import get_db_connection as get_afiliados_db_connection
        conn = get_afiliados_db_connection()
        try:
            pagos_en_afiliados = afiliados_pago_columns_exist(conn)
            pagos_table = afiliados_pagos_table_exists(conn)
            with conn.cursor() as cur:
                # Usar esquema explícito para asegurar que encuentre la tabla
                if pagos_en_afiliados:
                    cur.execute("SELECT * FROM shopfusion.afiliados WHERE id = %s", (afiliado_id,))
                elif pagos_table:
                    cur.execute("""
                        SELECT a.*,
                               ap.pais, ap.metodo_pago, ap.banco, ap.numero_cuenta,
                               ap.titular_cuenta, ap.paypal_email, ap.skrill_email, ap.frecuencia_pago
                        FROM shopfusion.afiliados a
                        LEFT JOIN shopfusion.afiliados_pagos ap ON a.id = ap.afiliado_id
                        WHERE a.id = %s
                    """, (afiliado_id,))
                else:
                    cur.execute("SELECT * FROM shopfusion.afiliados WHERE id = %s", (afiliado_id,))
                afiliado = cur.fetchone()
        finally:
            conn.close()

        if afiliado:
            for field in AFILIADOS_PAGO_FIELDS:
                afiliado.setdefault(field, None)
        
        if not afiliado:
            # Limpiar sesión si el afiliado no existe
            session.pop('afiliado_id', None)
            session.pop('afiliado_nombre', None)
            session.pop('afiliado_codigo', None)
            session.pop('afiliado_email', None)
            session.pop('afiliado_comision', None)
            session.pop('afiliado_auth', None)
            flash('Tu sesión ha expirado o tu cuenta ya no existe. Por favor, inicia sesión nuevamente.', 'warning')
            app.logger.error(f"[AFILIADOS_PANEL] Afiliado {afiliado_id} no encontrado - sesión limpiada")
            return redirect(url_for('afiliados_login'))
        
        # Obtener productos disponibles
        productos = obtener_productos_exclusivos(limit=100)
        
        # Obtener descuento disponible
        descuento_disponible = obtener_descuento_disponible_afiliado(afiliado_id)
        
        # Obtener carrito del afiliado desde BD
        carrito_afiliado = obtener_carrito_afiliado(afiliado_id)
        if isinstance(carrito_afiliado, dict) and carrito_afiliado.get('error') == 'Operación no permitida: los afiliados no pueden comprar productos':
            # Forzar logout silencioso y redirigir al login de afiliados
            session.pop('afiliado_id', None)
            session.pop('afiliado_nombre', None)
            session.pop('afiliado_codigo', None)
            session.pop('afiliado_email', None)
            session.pop('afiliado_comision', None)
            session.pop('afiliado_auth', None)
            session.modified = True
            app.logger.info('[SECURITY] Afiliado forzado a cerrar sesión por operación no permitida')
            return redirect(url_for('afiliados_login'))
        total_carrito = sum(item.get('precio', 0) * item.get('cantidad', 1) for item in carrito_afiliado)
        descuento_aplicado_carrito = min(total_carrito, descuento_disponible or 0) if carrito_afiliado else 0
        total_carrito_final = max(total_carrito - descuento_aplicado_carrito, 0)
        
        # Obtener productos por categorías
        from services_categorias import obtener_categorias
        categorias = obtener_categorias() or []
        
        # Organizar productos por categoría
        productos_por_categoria = {}
        if productos:
            for producto in productos:
                categoria = producto.get('categoria') or 'Otros'
                if categoria not in productos_por_categoria:
                    productos_por_categoria[categoria] = []
                productos_por_categoria[categoria].append(producto)

        # Historial de pagos recibidos
        pagos_recibidos = []
        try:
            conn_pagos = get_db_connection()
            ensure_pagos_afiliados_log(conn_pagos)
            with conn_pagos.cursor() as cur:
                cur.execute("""
                    SELECT monto, nota, creado_en
                    FROM shopfusion.pagos_afiliados_log
                    WHERE afiliado_id = %s
                    ORDER BY creado_en DESC
                    LIMIT 50
                """, (afiliado_id,))
                pagos_recibidos = cur.fetchall()
            conn_pagos.close()
        except Exception as e:
            app.logger.error(f"[AFILIADOS_PANEL] Error al cargar pagos recibidos: {e}")
            pagos_recibidos = []

        # Compras propias del afiliado (por email)
        compras_afiliado = []
        try:
            conn_comp = get_db_connection()
            with conn_comp.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id,
                        producto_id,
                        producto_titulo,
                        cantidad,
                        monto_total,
                        moneda,
                        estado_pago,
                        creado_en as fecha_compra
                    FROM shopfusion.cliente_compraron_productos
                    WHERE email = %s
                    ORDER BY creado_en DESC
                    LIMIT 50
                """, (afiliado.get('email'),))
                compras_afiliado = cur.fetchall()
            conn_comp.close()
        except Exception as e:
            app.logger.error(f"[AFILIADOS_PANEL] Error al cargar compras del afiliado: {e}")
            compras_afiliado = []
        
        return render_template(
            'afiliados_panel.html',
            afiliado=afiliado,
            estadisticas=estadisticas,
            productos=productos,
            productos_por_categoria=productos_por_categoria,
            categorias=categorias,
            descuento_disponible=descuento_disponible,
            carrito=carrito_afiliado,
            total_carrito=total_carrito_final,
            carrito_subtotal=total_carrito,
            descuento_aplicado_carrito=descuento_aplicado_carrito,
            paypal_client_id=PAYPAL_CLIENT_ID,
            bancos_ecuador=BANCOS_ECUADOR,
            pagos_recibidos=pagos_recibidos,
            compras_afiliado=compras_afiliado
        )
    except Exception as e:
        app.logger.error(f"[AFILIADOS_PANEL] Error: {e}")
        flash('Error al cargar el panel', 'danger')
        return redirect(url_for('afiliados_login'))


@app.route('/afiliados/producto/<int:producto_id>')
def afiliados_producto_detalle(producto_id):
    """Detalle de producto para el panel de afiliados."""
    if 'afiliado_id' not in session or not session.get('afiliado_auth') or 'afiliado_email' not in session:
        return redirect(url_for('afiliados_login'))

    afiliado_codigo = session.get('afiliado_codigo')
    afiliado = obtener_afiliado_por_codigo(afiliado_codigo) if afiliado_codigo else None
    if not afiliado:
        return render_template('afiliados_producto_detalle.html', error='Afiliado no encontrado')

    producto = obtener_producto_exclusivo_por_id(producto_id)
    if not producto:
        return render_template('afiliados_producto_detalle.html', error='Producto no encontrado')

    precio_base = float(producto.get('precio') or 0)
    precio_oferta_val = float(producto.get('precio_oferta') or 0)
    precio_final = precio_oferta_val if precio_oferta_val and precio_oferta_val < precio_base else precio_base
    precio_proveedor = float(producto.get('precio_proveedor') or 0)
    margen = precio_final - precio_proveedor
    if margen < 0:
        margen = 0

    comision_pct = float(afiliado.get('comision_porcentaje') or 0)
    comision_ganada = (margen * comision_pct / 100) if margen else 0
    precio_afiliado = precio_final - comision_ganada
    if precio_afiliado < 0:
        precio_afiliado = 0

    descuento_disponible = obtener_descuento_disponible_afiliado(afiliado['id'])
    if descuento_disponible and descuento_disponible > 0:
        precio_con_descuento = max(precio_afiliado - float(descuento_disponible), 0)
    else:
        precio_con_descuento = precio_afiliado

    return render_template(
        'afiliados_producto_detalle.html',
        afiliado=afiliado,
        producto=producto,
        precio_final=precio_final,
        precio_proveedor=precio_proveedor,
        margen=margen,
        comision_pct=comision_pct,
        comision_ganada=comision_ganada,
        precio_afiliado=precio_afiliado,
        precio_con_descuento=precio_con_descuento,
        descuento_disponible=descuento_disponible
    )


# ============================
# FACTURA / RECIBO DE COMPRA
# ============================
@app.route('/factura/<int:compra_id>')
def factura_compra(compra_id):
    """Factura simple en HTML para una compra."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    id,
                    producto_id,
                    producto_titulo,
                    producto_precio,
                    cantidad,
                    monto_total,
                    moneda,
                    estado_pago,
                    creado_en,
                    nombre,
                    apellido,
                    email,
                    telefono,
                    pais,
                    direccion,
                    afiliado_id,
                    afiliado_codigo
                FROM shopfusion.cliente_compraron_productos
                WHERE id = %s
                LIMIT 1
            """, (compra_id,))
            compra = cur.fetchone()
        conn.close()
        if not compra:
            return render_template('error.html', codigo=404, mensaje='Factura no encontrada'), 404

        # Validar acceso básico: cliente/afiliado dueño del email o admin
        es_admin = session.get('rol') == 'admin'
        es_cliente = session.get('email') and session.get('email') == compra.get('email')
        es_afiliado = session.get('afiliado_auth') and session.get('afiliado_email') == compra.get('email')
        if not (es_admin or es_cliente or es_afiliado):
            return render_template('error.html', codigo=403, mensaje='No autorizado para ver esta factura'), 403

        return render_template('factura.html', compra=compra)
    except Exception as e:
        app.logger.error(f"[FACTURA] Error: {e}")
        return render_template('error.html', codigo=500, mensaje='No se pudo generar la factura'), 500


@app.route('/afiliados/configuracion/pagos', methods=['POST'])
def afiliados_configuracion_pagos():
    """Actualizar datos de pago del afiliado."""
    if 'afiliado_id' not in session or not session.get('afiliado_auth'):
        flash('Debes iniciar sesión para actualizar tus datos de pago', 'warning')
        return redirect(url_for('afiliados_login'))

    afiliado_id = session['afiliado_id']
    pais = (request.form.get('pais') or '').strip()
    metodo_pago = (request.form.get('metodo_pago') or '').strip().lower()
    banco = (request.form.get('banco') or '').strip()
    numero_cuenta = (request.form.get('numero_cuenta') or '').strip()
    titular_cuenta = (request.form.get('titular_cuenta') or '').strip()
    paypal_email = (request.form.get('paypal_email') or '').strip().lower()
    skrill_email = (request.form.get('skrill_email') or '').strip().lower()
    frecuencia_pago = (request.form.get('frecuencia_pago') or '').strip().lower()

    if not pais:
        flash('Debes indicar tu país', 'danger')
        return redirect(url_for('afiliados_panel'))

    es_ecuador = pais.lower() == 'ecuador'
    metodos_permitidos = METODOS_PAGO_ECUADOR if es_ecuador else METODOS_PAGO_INTERNACIONAL

    if frecuencia_pago not in FRECUENCIAS_PAGO:
        flash('Selecciona una frecuencia de pago valida', 'danger')
        return redirect(url_for('afiliados_panel'))

    if metodo_pago not in metodos_permitidos:
        flash('Método de pago no permitido para tu país', 'danger')
        return redirect(url_for('afiliados_panel'))

    if metodo_pago == 'transferencia':
        if banco not in BANCOS_ECUADOR:
            flash('Banco no permitido para transferencias en Ecuador', 'danger')
            return redirect(url_for('afiliados_panel'))
        if not numero_cuenta or not titular_cuenta:
            flash('Completa banco, número de cuenta y titular', 'danger')
            return redirect(url_for('afiliados_panel'))
        paypal_email = None
        skrill_email = None
    elif metodo_pago == 'paypal':
        if not paypal_email or not validar_correo(paypal_email):
            flash('Email de PayPal inválido', 'danger')
            return redirect(url_for('afiliados_panel'))
        banco = None
        numero_cuenta = None
        titular_cuenta = None
        skrill_email = None
    elif metodo_pago == 'skrill':
        if not skrill_email or not validar_correo(skrill_email):
            flash('Email de Skrill inválido', 'danger')
            return redirect(url_for('afiliados_panel'))
        banco = None
        numero_cuenta = None
        titular_cuenta = None
        paypal_email = None

    try:
        conn = get_db_connection()
        pagos_en_afiliados = afiliados_pago_columns_exist(conn)
        if pagos_en_afiliados:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE shopfusion.afiliados
                    SET pais = %s,
                        metodo_pago = %s,
                        banco = %s,
                        numero_cuenta = %s,
                        titular_cuenta = %s,
                        paypal_email = %s,
                        skrill_email = %s,
                        frecuencia_pago = %s
                    WHERE id = %s
                """, (
                    pais,
                    metodo_pago,
                    banco,
                    numero_cuenta,
                    titular_cuenta,
                    paypal_email,
                    skrill_email,
                    frecuencia_pago,
                    afiliado_id
                ))
        else:
            if not afiliados_pagos_table_exists(conn):
                flash('Tabla de pagos no disponible. Ejecuta migraciones.', 'danger')
                return redirect(url_for('afiliados_panel'))
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO shopfusion.afiliados_pagos
                        (afiliado_id, pais, metodo_pago, banco, numero_cuenta,
                         titular_cuenta, paypal_email, skrill_email, frecuencia_pago)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (afiliado_id)
                    DO UPDATE SET
                        pais = EXCLUDED.pais,
                        metodo_pago = EXCLUDED.metodo_pago,
                        banco = EXCLUDED.banco,
                        numero_cuenta = EXCLUDED.numero_cuenta,
                        titular_cuenta = EXCLUDED.titular_cuenta,
                        paypal_email = EXCLUDED.paypal_email,
                        skrill_email = EXCLUDED.skrill_email,
                        frecuencia_pago = EXCLUDED.frecuencia_pago,
                        actualizado_en = CURRENT_TIMESTAMP
                """, (
                    afiliado_id,
                    pais,
                    metodo_pago,
                    banco,
                    numero_cuenta,
                    titular_cuenta,
                    paypal_email,
                    skrill_email,
                    frecuencia_pago
                ))
        conn.commit()
        flash('Datos de pago actualizados correctamente', 'success')
    except Exception as e:
        app.logger.error(f"[AFILIADOS_PAGOS] Error: {e}")
        flash('Error al actualizar datos de pago', 'danger')
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return redirect(url_for('afiliados_panel'))


@app.route('/admin/afiliados/<int:afiliado_id>/comision', methods=['POST'])
def actualizar_comision_afiliado(afiliado_id):
    """Actualizar la comisión de un afiliado (con tiempo límite opcional)"""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    
    try:
        from datetime import datetime, timedelta
        comision = float(request.form.get('comision', 0))
        tiempo_limite_dias = request.form.get('tiempo_limite', None)
        admin_id = session.get('usuario_id')
        
        if comision < 0 or comision > 100:
            flash('La comisión debe estar entre 0 y 100%', 'danger')
            return redirect(url_for('panel'))
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Si hay tiempo límite, crear comisión manual temporal
            if tiempo_limite_dias and int(tiempo_limite_dias) > 0:
                dias = int(tiempo_limite_dias)
                fecha_expiracion = datetime.now() + timedelta(days=dias)
                
                # Desactivar comisiones manuales previas
                cur.execute("""
                    UPDATE shopfusion.comisiones_manuales_temporales
                    SET activa = FALSE
                    WHERE afiliado_id = %s AND activa = TRUE
                """, (afiliado_id,))
                
                # Crear nueva comisión manual temporal
                cur.execute("""
                    INSERT INTO shopfusion.comisiones_manuales_temporales 
                    (afiliado_id, comision_manual, fecha_expiracion, creado_por, activa)
                    VALUES (%s, %s, %s, %s, TRUE)
                """, (afiliado_id, comision, fecha_expiracion, admin_id))
                
                # Actualizar comisión actual del afiliado
                cur.execute("""
                    UPDATE shopfusion.afiliados
                    SET comision_porcentaje = %s
                    WHERE id = %s
                """, (comision, afiliado_id))
                
                flash(f'Comisión actualizada a {comision}% por {dias} día(s). Después volverá al sistema automático.', 'success')
            else:
                # Actualización permanente (sin tiempo límite)
                cur.execute("""
                    UPDATE shopfusion.afiliados
                    SET comision_porcentaje = %s
                    WHERE id = %s
                """, (comision, afiliado_id))
                
                # Desactivar comisiones manuales temporales si existían
                cur.execute("""
                    UPDATE shopfusion.comisiones_manuales_temporales
                    SET activa = FALSE
                    WHERE afiliado_id = %s AND activa = TRUE
                """, (afiliado_id,))
                
                flash(f'Comisión actualizada permanentemente a {comision}%', 'success')
            
            conn.commit()
        conn.close()
    except Exception as e:
        app.logger.error(f"[ACTUALIZAR_COMISION] Error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        flash('Error al actualizar la comisión', 'danger')
    
    return redirect(url_for('panel'))

# =====================================================================
# PAGOS A AFILIADOS (ADMIN)
# =====================================================================

def ensure_pagos_afiliados_log(conn):
    """Crea tabla de pagos a afiliados si no existe."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS shopfusion.pagos_afiliados_log (
                id SERIAL PRIMARY KEY,
                afiliado_id INTEGER NOT NULL REFERENCES shopfusion.afiliados(id) ON DELETE CASCADE,
                monto NUMERIC(12,2) NOT NULL,
                nota TEXT,
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    conn.commit()

@app.route('/admin/afiliados/<int:afiliado_id>/pago-parcial', methods=['POST'])
def pagar_parcial_afiliado(afiliado_id):
    """Registrar un pago parcial a un afiliado y descontarlo de su saldo."""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    try:
        monto = float(request.form.get('monto') or 0)
        nota = (request.form.get('nota') or '').strip()
        if monto <= 0:
            flash('El monto debe ser mayor a 0.', 'danger')
            return redirect(url_for('panel'))
        conn = get_db_connection()
        ensure_pagos_afiliados_log(conn)
        with conn.cursor() as cur:
            # Verificar si la columna total_pagado existe
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'shopfusion'
                    AND table_name = 'afiliados'
                    AND column_name = 'total_pagado'
                )
            """)
            has_total_pagado = bool(cur.fetchone().get('exists'))

            if has_total_pagado:
                cur.execute("SELECT total_ganancias, total_pagado FROM shopfusion.afiliados WHERE id = %s", (afiliado_id,))
            else:
                cur.execute("SELECT total_ganancias FROM shopfusion.afiliados WHERE id = %s", (afiliado_id,))
            afiliado = cur.fetchone()
            if not afiliado:
                flash('Afiliado no encontrado.', 'danger')
                conn.close()
                return redirect(url_for('panel'))
            saldo = float(afiliado.get('total_ganancias') or 0)
            if saldo <= 0:
                flash('El afiliado no tiene saldo pendiente.', 'info')
                conn.close()
                return redirect(url_for('panel'))
            if monto > saldo:
                monto = saldo
            if has_total_pagado:
                cur.execute("""
                    UPDATE shopfusion.afiliados
                    SET total_ganancias = GREATEST(total_ganancias - %s, 0),
                        total_pagado = COALESCE(total_pagado, 0) + %s
                    WHERE id = %s
                """, (monto, monto, afiliado_id))
            else:
                cur.execute("""
                    UPDATE shopfusion.afiliados
                    SET total_ganancias = GREATEST(total_ganancias - %s, 0)
                    WHERE id = %s
                """, (monto, afiliado_id))
            cur.execute("""
                INSERT INTO shopfusion.pagos_afiliados_log (afiliado_id, monto, nota)
                VALUES (%s, %s, %s)
            """, (afiliado_id, monto, nota))
            conn.commit()
        conn.close()
        flash(f'Pago registrado: ${monto:.2f}', 'success')
    except Exception as e:
        app.logger.error(f"[PAGO_PARCIAL_AFILIADO] Error: {e}")
        flash('No se pudo registrar el pago.', 'danger')
    return redirect(url_for('panel'))


@app.route('/admin/afiliados/<int:afiliado_id>/estado', methods=['POST'])
def cambiar_estado_afiliado(afiliado_id):
    """Cambiar el estado de un afiliado (activo/inactivo)"""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Obtener estado actual
            cur.execute("SELECT estado FROM shopfusion.afiliados WHERE id = %s", (afiliado_id,))
            afiliado = cur.fetchone()
            if not afiliado:
                flash('Afiliado no encontrado', 'danger')
                return redirect(url_for('panel'))
            
            nuevo_estado = 'inactivo' if afiliado['estado'] == 'activo' else 'activo'
            cur.execute("""
                UPDATE shopfusion.afiliados
                SET estado = %s
                WHERE id = %s
            """, (nuevo_estado, afiliado_id))
            conn.commit()
        conn.close()
        
        flash(f'Estado del afiliado cambiado a {nuevo_estado}', 'success')
    except Exception as e:
        app.logger.error(f"[CAMBIAR_ESTADO] Error: {e}")
        flash('Error al cambiar el estado', 'danger')
    
    return redirect(url_for('panel'))


@app.route('/admin/afiliados/<int:afiliado_id>/frecuencia-pago', methods=['POST'])
def actualizar_frecuencia_pago_afiliado(afiliado_id):
    """Actualizar la frecuencia de pago de un afiliado."""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesion como administrador.', 'danger')
        return redirect(url_for('admin'))

    flash('La frecuencia de pago la define el afiliado.', 'info')
    return redirect(url_for('panel'))


@app.route('/admin/comision-predeterminada', methods=['POST'])
def ajustar_comision_predeterminada():
    """Ajustar la comisión predeterminada del sistema para usuarios nuevos"""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    
    try:
        comision = float(request.form.get('comision', 0))
        if comision < 0 or comision > 100:
            flash('La comisión debe estar entre 0 y 100%', 'danger')
            return redirect(url_for('panel'))
        
        admin_id = session.get('usuario_id')
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO shopfusion.configuracion_sistema (clave, valor, descripcion, actualizado_por)
                VALUES ('comision_predeterminada', %s, 'Comisión predeterminada para usuarios nuevos', %s)
                ON CONFLICT (clave) 
                DO UPDATE SET 
                    valor = EXCLUDED.valor,
                    actualizado_por = EXCLUDED.actualizado_por,
                    actualizado_en = CURRENT_TIMESTAMP
            """, (str(comision), admin_id))
            conn.commit()
        conn.close()
        
        flash(f'Comisión predeterminada actualizada a {comision}% para usuarios nuevos', 'success')
    except Exception as e:
        app.logger.error(f"[AJUSTAR_COMISION_PRED] Error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        flash('Error al actualizar la comisión predeterminada', 'danger')
    
    return redirect(url_for('panel'))


@app.route('/admin/comision-todos-afiliados', methods=['POST'])
def ajustar_comision_todos_afiliados():
    """Ajustar la comisión de todos los afiliados a la vez"""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    
    try:
        from datetime import datetime, timedelta
        comision = float(request.form.get('comision', 0))
        tiempo_limite_dias = request.form.get('tiempo_limite', None)
        admin_id = session.get('usuario_id')
        
        if comision < 0 or comision > 100:
            flash('La comisión debe estar entre 0 y 100%', 'danger')
            return redirect(url_for('panel'))
        
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Obtener todos los afiliados activos
            cur.execute("SELECT id FROM shopfusion.afiliados WHERE estado = 'activo'")
            afiliados = cur.fetchall()
            
            if tiempo_limite_dias and int(tiempo_limite_dias) > 0:
                dias = int(tiempo_limite_dias)
                fecha_expiracion = datetime.now() + timedelta(days=dias)
                
                # Desactivar comisiones manuales previas de todos
                cur.execute("""
                    UPDATE shopfusion.comisiones_manuales_temporales
                    SET activa = FALSE
                    WHERE activa = TRUE
                """)
                
                # Crear comisiones manuales temporales para todos
                for afiliado in afiliados:
                    cur.execute("""
                        INSERT INTO shopfusion.comisiones_manuales_temporales 
                        (afiliado_id, comision_manual, fecha_expiracion, creado_por, activa)
                        VALUES (%s, %s, %s, %s, TRUE)
                    """, (afiliado['id'], comision, fecha_expiracion, admin_id))
                
                # Actualizar comisión de todos los afiliados
                cur.execute("""
                    UPDATE shopfusion.afiliados
                    SET comision_porcentaje = %s
                    WHERE estado = 'activo'
                """, (comision,))
                
                flash(f'Comisión de todos los afiliados actualizada a {comision}% por {dias} día(s). Después volverá al sistema automático.', 'success')
            else:
                # Actualización permanente (sin tiempo límite)
                # Desactivar todas las comisiones manuales temporales
                cur.execute("""
                    UPDATE shopfusion.comisiones_manuales_temporales
                    SET activa = FALSE
                    WHERE activa = TRUE
                """)
                
                # Actualizar comisión de todos los afiliados
                cur.execute("""
                    UPDATE shopfusion.afiliados
                    SET comision_porcentaje = %s
                    WHERE estado = 'activo'
                """, (comision,))
                
                flash(f'Comisión de todos los afiliados actualizada permanentemente a {comision}%', 'success')
            
            conn.commit()
        conn.close()
    except Exception as e:
        app.logger.error(f"[AJUSTAR_COMISION_TODOS] Error: {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        flash('Error al actualizar las comisiones', 'danger')
    
    return redirect(url_for('panel'))


@app.route('/trabaja-con-nosotros')
def trabaja_con_nosotros():
    return render_template('trabaja_con_nosotros.html')


@app.route('/trabaja/afiliados')
def trabaja_afiliados():
    """Página dedicada para afiliados."""
    return render_template('trabaja_afiliados.html')

@app.route('/trabaja/proveedores')
def trabaja_proveedores():
    """Página dedicada para proveedores."""
    return render_template('trabaja_proveedores.html')

@app.route('/trabaja/vacantes')
def trabaja_vacantes():
    """Página dedicada para vacantes activas."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, titulo, descripcion, requisitos, activa, creado_en
            FROM shopfusion.vacantes
            WHERE activa = TRUE
            ORDER BY creado_en DESC
        """)
        vacantes = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        app.logger.error(f"[TRABAJA_VACANTES] Error al cargar vacantes: {e}")
        vacantes = []
    return render_template('trabaja_vacantes.html', vacantes=vacantes)


@app.route('/proveedores')
def proveedores():
    """Página para proveedores que quieren vender productos"""
    try:
        categorias = obtener_categorias(activas=True) or []
    except Exception as e:
        app.logger.error(f"[PROVEEDORES] Error al cargar categorías: {e}")
        categorias = []

    # Mostrar página con invitación y listado de categorías
    return render_template(
        'proveedores.html',
        categorias=categorias,
        whatsapp=WHATSAPP_NUMBER,
        whatsapp_digits=WHATSAPP_NUMBER_DIGITS
    )


@app.route('/soporte', methods=['GET', 'POST'])
def soporte():
    """Página de soporte y tickets de atención al cliente"""
    if request.method == 'POST':
        nombre = (request.form.get('nombre') or '').strip()
        email = (request.form.get('email') or '').strip()
        mensaje = (request.form.get('mensaje') or '').strip()

        if not nombre or not email or not mensaje:
            flash('Completa nombre, email y mensaje para crear el ticket.', 'danger')
            return redirect(url_for('soporte'))
        if not validar_correo(email):
            flash('Correo inválido', 'danger')
            return redirect(url_for('soporte'))

        try:
            conn = get_db_connection()
            ensure_soporte_table(conn)
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO shopfusion.tickets_soporte (nombre, email, mensaje)
                    VALUES (%s, %s, %s)
                """, (nombre, email, mensaje))
                conn.commit()
            flash('Ticket de soporte creado. Te responderemos pronto.', 'success')
            return redirect(url_for('soporte'))
        except Exception as e:
            app.logger.error(f"[SOPORTE] Error al crear ticket: {e}")
            flash('No se pudo crear el ticket. Intenta nuevamente.', 'danger')
            return redirect(url_for('soporte'))
        finally:
            try:
                conn.close()
            except Exception:
                pass

    return render_template('soporte.html')


# ========== RUTAS PARA GESTIÓN DE VACANTES (ADMIN) ==========
@app.route('/admin/vacantes', methods=['GET', 'POST'])
def admin_vacantes():
    """Gestionar vacantes (crear, editar, eliminar)"""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    
    if request.method == 'POST':
        try:
            titulo = request.form.get('titulo', '').strip()
            descripcion = request.form.get('descripcion', '').strip()
            requisitos = request.form.get('requisitos', '').strip()
            activa = request.form.get('activa') == 'on'
            
            if not titulo or not descripcion:
                flash('Título y descripción son obligatorios', 'danger')
                return redirect(url_for('admin_vacantes'))
            
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO shopfusion.vacantes (titulo, descripcion, requisitos, activa)
                    VALUES (%s, %s, %s, %s)
                """, (titulo, descripcion, requisitos, activa))
                conn.commit()
            conn.close()
            
            flash('✅ Vacante creada correctamente', 'success')
        except Exception as e:
            app.logger.error(f"[ADMIN_VACANTES] Error: {e}")
            flash('Error al crear vacante', 'danger')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, titulo, descripcion, requisitos, activa, creado_en
            FROM shopfusion.vacantes
            ORDER BY creado_en DESC
        """)
        vacantes = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        app.logger.error(f"[ADMIN_VACANTES] Error al cargar: {e}")
        vacantes = []
    
    return render_template('admin_vacantes.html', vacantes=vacantes)

@app.route('/admin/vacantes/<int:vacante_id>/editar', methods=['GET', 'POST'])
def admin_editar_vacante(vacante_id):
    """Editar una vacante"""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    
    if request.method == 'POST':
        try:
            titulo = request.form.get('titulo', '').strip()
            descripcion = request.form.get('descripcion', '').strip()
            requisitos = request.form.get('requisitos', '').strip()
            activa = request.form.get('activa') == 'on'
            
            if not titulo or not descripcion:
                flash('Título y descripción son obligatorios', 'danger')
                return redirect(url_for('admin_editar_vacante', vacante_id=vacante_id))
            
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE shopfusion.vacantes
                    SET titulo = %s, descripcion = %s, requisitos = %s, activa = %s,
                        actualizado_en = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (titulo, descripcion, requisitos, activa, vacante_id))
                conn.commit()
            conn.close()
            
            flash('✅ Vacante actualizada correctamente', 'success')
            return redirect(url_for('admin_vacantes'))
        except Exception as e:
            app.logger.error(f"[ADMIN_EDITAR_VACANTE] Error: {e}")
            flash('Error al actualizar vacante', 'danger')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, titulo, descripcion, requisitos, activa
            FROM shopfusion.vacantes
            WHERE id = %s
        """, (vacante_id,))
        vacante = cur.fetchone()
        cur.close()
        conn.close()
        
        if not vacante:
            flash('Vacante no encontrada', 'danger')
            return redirect(url_for('admin_vacantes'))
    except Exception as e:
        app.logger.error(f"[ADMIN_EDITAR_VACANTE] Error: {e}")
        flash('Error al cargar vacante', 'danger')
        return redirect(url_for('admin_vacantes'))
    
    return render_template('admin_editar_vacante.html', vacante=vacante)

@app.route('/admin/vacantes/<int:vacante_id>/eliminar', methods=['POST'])
def admin_eliminar_vacante(vacante_id):
    """Eliminar una vacante"""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM shopfusion.vacantes WHERE id = %s", (vacante_id,))
            conn.commit()
        conn.close()
        flash('✅ Vacante eliminada correctamente', 'success')
    except Exception as e:
        app.logger.error(f"[ADMIN_ELIMINAR_VACANTE] Error: {e}")
        flash('Error al eliminar vacante', 'danger')
    
    return redirect(url_for('admin_vacantes'))

@app.route('/admin/vacantes/<int:vacante_id>/finalizar', methods=['POST'])
def admin_finalizar_vacante(vacante_id):
    """Marcar una vacante como finalizada (activa = False)."""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE shopfusion.vacantes
                SET activa = FALSE, actualizado_en = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (vacante_id,))
            conn.commit()
        conn.close()
        flash('Vacante marcada como finalizada.', 'success')
    except Exception as e:
        app.logger.error(f"[ADMIN_FINALIZAR_VACANTE] Error: {e}")
        flash('No se pudo marcar la vacante como finalizada.', 'danger')
    return redirect(url_for('admin_vacantes'))

@app.route('/admin/vacantes/<int:vacante_id>/aplicaciones')
def admin_aplicaciones_vacante(vacante_id):
    """Ver aplicaciones a una vacante"""
    if 'usuario_id' not in session or session.get('rol') != 'admin':
        flash('Debes iniciar sesión como administrador.', 'danger')
        return redirect(url_for('admin'))
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Obtener información de la vacante
        cur.execute("SELECT id, titulo FROM shopfusion.vacantes WHERE id = %s", (vacante_id,))
        vacante = cur.fetchone()
        
        # Obtener aplicaciones
        cur.execute("""
            SELECT id, nombre_completo, email, telefono, hoja_vida, mensaje, estado, creado_en
            FROM shopfusion.aplicaciones_vacantes
            WHERE vacante_id = %s
            ORDER BY creado_en DESC
        """, (vacante_id,))
        aplicaciones = cur.fetchall()
        cur.close()
        conn.close()
        
        if not vacante:
            flash('Vacante no encontrada', 'danger')
            return redirect(url_for('admin_vacantes'))
    except Exception as e:
        app.logger.error(f"[ADMIN_APLICACIONES] Error: {e}")
        flash('Error al cargar aplicaciones', 'danger')
        return redirect(url_for('admin_vacantes'))
    
    return render_template('admin_aplicaciones_vacante.html', vacante=vacante, aplicaciones=aplicaciones)

# ========== RUTA PARA APLICAR A VACANTE (PÚBLICO) ==========
@app.route('/aplicar-vacante/<int:vacante_id>', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def aplicar_vacante(vacante_id):
    """Formulario para aplicar a una vacante"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, titulo, descripcion, requisitos
            FROM shopfusion.vacantes
            WHERE id = %s AND activa = TRUE
        """, (vacante_id,))
        vacante = cur.fetchone()
        cur.close()
        conn.close()
        
        if not vacante:
            flash('Vacante no encontrada o no disponible', 'danger')
            return redirect(url_for('trabaja_con_nosotros'))
    except Exception as e:
        app.logger.error(f"[APLICAR_VACANTE] Error: {e}")
        flash('Error al cargar vacante', 'danger')
        return redirect(url_for('trabaja_con_nosotros'))

    # Si llega con ?enviado=1 mostramos el modal de confirmación
    show_modal = request.args.get('enviado') == '1'
    
    if request.method == 'POST':
        try:
            nombre_completo = request.form.get('nombre_completo', '').strip()
            email = request.form.get('email', '').strip()
            telefono = request.form.get('telefono', '').strip()
            hoja_vida = request.form.get('hoja_vida', '').strip()
            mensaje = request.form.get('mensaje', '').strip()

            # Validaciones básicas en servidor
            if not nombre_completo or not email or not hoja_vida:
                flash('Nombre completo, correo y Hoja de Vida son obligatorios', 'danger')
                return render_template('aplicar_vacante.html', vacante=vacante, form=request.form, show_modal=show_modal)

            if len(nombre_completo) > 200 or len(email) > 200 or len(telefono) > 50 or len(hoja_vida) > 20000:
                flash('Uno de los campos excede la longitud permitida', 'danger')
                return render_template('aplicar_vacante.html', vacante=vacante, form=request.form, show_modal=show_modal)

            # Validación simple de email
            if '@' not in email or '.' not in email.split('@')[-1]:
                flash('Email inválido', 'danger')
                return render_template('aplicar_vacante.html', vacante=vacante, form=request.form, show_modal=show_modal)

            conn = get_db_connection()
            with conn.cursor() as cur:
                # Evitar aplicaciones múltiples en corto tiempo (anti-spam)
                cur.execute("""
                    SELECT 1 FROM shopfusion.aplicaciones_vacantes
                    WHERE vacante_id=%s AND email=%s AND creado_en >= NOW() - INTERVAL '2 days'
                """, (vacante_id, email))
                if cur.fetchone():
                    # Ya existe una aplicación reciente: redirigimos a la página general
                    # con parámetros para mostrar un mensaje amigable en la UI.
                    conn.close()
                    return redirect(url_for('trabaja_con_nosotros', postulado=1, duplicado=1, vacante_id=vacante_id))

                cur.execute("""
                    INSERT INTO shopfusion.aplicaciones_vacantes 
                    (vacante_id, nombre_completo, email, telefono, hoja_vida, mensaje)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (vacante_id, nombre_completo, email, telefono, hoja_vida, mensaje))
                conn.commit()
            conn.close()

            # Redirigimos al hub 'Trabaja con nosotros' con parámetros para mostrar banner y modal
            return redirect(url_for('trabaja_con_nosotros', postulado=1, enviado=1, vacante_id=vacante_id))
        except Exception as e:
            app.logger.error(f"[APLICAR_VACANTE] Error: {e}")
            flash('Error al enviar aplicación', 'danger')
            return render_template('aplicar_vacante.html', vacante=vacante, form=request.form, show_modal=show_modal)
    
    return render_template('aplicar_vacante.html', vacante=vacante, show_modal=show_modal)

# ============================================================
# ERRORES CUSTOM
# ============================================================
@app.errorhandler(404)
def error_404(e):
    return render_template('error.html', codigo=404, mensaje='Ups, esta página no existe.'), 404

@app.errorhandler(500)
def error_500(e):
    return render_template('error.html', codigo=500, mensaje='Ocurrió un error inesperado. Intenta más tarde.'), 500

if __name__ == '__main__':
    # Ejecuta migraciones/control de esquema antes de iniciar en produccion.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
