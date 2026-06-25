"""
Rutas de autenticación
Maneja login/logout para Admin y Afiliado
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, current_user
from datetime import datetime, timedelta  
from utils.security_logger import log_security_event
from utils.rate_limit import limiter
# FASE 2: Integración de Redis para prevención de evasiones multi-worker.
from utils.rate_limit import redis_client

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", error_message='Demasiados intentos. Por seguridad, inténtalo en un minuto.')
def admin_login():
    """Login de administrador"""
    from models import Admin

    if current_user.is_authenticated:
        # Si ya está logueado, redirigir al dashboard correspondiente
        if isinstance(current_user, Admin):
            return redirect(url_for('admin.dashboard_admin'))
        else:
            return redirect(url_for('afiliado.dashboard'))


    #INICIA LOS CAMBIOS INDICADOS EN FASE 1
    # SEGURIDAD: Verificar si la IP está bloqueada temporalmente por demasiados intentos fallidos
    # FASE 2: Rastreo por IP estricta y Redis (Spoofing mitigado por ProxyFix en app.py)
    ip = request.remote_addr
    lock_key = f"admin_login_lock:{ip}"
    if redis_client.exists(lock_key):
        minutos_restantes = int(redis_client.ttl(lock_key) // 60) + 1
        log_security_event('LOGIN_ATTEMPT', 'BLOCKED', details=f"Admin login blocked for {minutos_restantes}m from {ip}")
        flash(f'Demasiados intentos fallidos. Por seguridad, espera {minutos_restantes} minuto(s).', 'error')
        return render_template('auth/admin_login.html')

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Por favor completa todos los campos', 'error')
            return render_template('auth/admin_login.html')

        # SEGURIDAD CRÍTICA (CORRECCIÓN FINAL): Validación exclusiva contra Base de Datos
        # Se elimina la validación en texto plano contra el archivo .env, previniendo exposición de credenciales.
        admin = Admin.query.filter_by(username=username).first()

        if admin and admin.check_password(password):
            # Login exitoso
            login_user(admin)
            session['user_type'] = 'admin'
            session['user_id'] = f'admin_{admin.id}'

            # Login exitoso: Limpiar rastros de intentos fallidos previos
            redis_client.delete(f"admin_failed_attempts:{ip}")
            redis_client.delete(lock_key)

            log_security_event('LOGIN', 'SUCCESS', user_id=admin.username, details="Admin login successful")
            flash(f'¡Bienvenido {admin.username}!', 'success')

            # Redirigir a la página solicitada o al dashboard
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('admin.dashboard_admin'))
        else:
            # SEGURIDAD: Incrementar contador de intentos fallidos vinculados a la IP
            attempts_key = f"admin_failed_attempts:{ip}"
            attempts = redis_client.incr(attempts_key)
            if attempts == 1:
                redis_client.expire(attempts_key, 3600) # Expirar contador tras 1 hora
            
            # Si se supera el límite definido en config.py, se bloquea la IP en Redis
            if attempts >= current_app.config.get('LOGIN_ATTEMPTS_LIMIT', 5):
                lock_time = current_app.config.get('LOGIN_LOCK_MINUTES', 5)
                redis_client.setex(lock_key, lock_time * 60, "locked")
                log_security_event('LOGIN_BRUTE_FORCE', 'BLOCKED', user_id=username, details=f"Admin locked IP {ip} for {lock_time}m after {attempts} attempts")
                flash(f'Has superado el límite de intentos. Bloqueado por {lock_time} minutos.', 'error')
            else:
                intentos_restantes = current_app.config.get('LOGIN_ATTEMPTS_LIMIT', 5) - attempts
                log_security_event('LOGIN_ATTEMPT', 'FAILURE', user_id=username, details=f"Wrong admin credentials from {ip}. Attempt {attempts}")
                flash(f'Usuario o contraseña incorrectos. Intentos restantes: {intentos_restantes}', 'error')

    return render_template('auth/admin_login.html')
    #FIN DE LOS CAMBIOS INDICADOS EN FASE 1

@bp.route('/afiliado/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", error_message='Demasiados intentos. Por seguridad, inténtalo en un minuto.')
def afiliado_login():
    """Login de afiliado"""
    from models import Afiliado

    # SEGURIDAD (E21): Verificar si la IP está bloqueada temporalmente
    ip = request.remote_addr
    lock_key = f"afiliado_login_lock:{ip}"
    if redis_client.exists(lock_key):
        minutos_restantes = int(redis_client.ttl(lock_key) // 60) + 1
        log_security_event('LOGIN_ATTEMPT', 'BLOCKED', details=f"Affiliate login blocked for {minutos_restantes}m from {ip}")
        flash(f'Demasiados intentos fallidos. Por seguridad, espera {minutos_restantes} minuto(s).', 'error')
        return render_template('auth/afiliado_login.html')

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('Por favor completa todos los campos', 'error')
            return render_template('auth/afiliado_login.html')

        # Buscar afiliado
        afiliado = Afiliado.query.filter_by(email=email).first()

        if afiliado and afiliado.check_password(password):
            # Verificar que esté activo
            if not afiliado.activo:
                flash('Tu cuenta está desactivada. Contacta al administrador.', 'error')
                return render_template('auth/afiliado_login.html')

            # Login exitoso
            login_user(afiliado)
            session['user_type'] = 'afiliado'
            session['user_id'] = f'afiliado_{afiliado.id}'
            
            # Limpiar rastros de intentos fallidos
            redis_client.delete(f"afiliado_failed_attempts:{ip}")
            redis_client.delete(lock_key)

            log_security_event('LOGIN', 'SUCCESS', user_id=afiliado.email, details="Affiliate login successful")
            flash(f'¡Bienvenido {afiliado.nombre}!', 'success')

            # Redirigir a la página solicitada o al dashboard
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('afiliado.dashboard'))
        else:
            # SEGURIDAD (E21): Incrementar contador de intentos fallidos vinculados a la IP
            attempts_key = f"afiliado_failed_attempts:{ip}"
            attempts = redis_client.incr(attempts_key)
            if attempts == 1:
                redis_client.expire(attempts_key, 3600) # Expirar contador tras 1 hora
            
            limit = current_app.config.get('LOGIN_ATTEMPTS_LIMIT', 5)
            if attempts >= limit:
                lock_time = current_app.config.get('LOGIN_LOCK_MINUTES', 5)
                redis_client.setex(lock_key, lock_time * 60, "locked")
                log_security_event('LOGIN_BRUTE_FORCE', 'BLOCKED', user_id=email, details=f"Affiliate locked IP {ip} for {lock_time}m after {attempts} attempts")
                flash(f'Has superado el límite de intentos. Bloqueado por {lock_time} minutos.', 'error')
            else:
                intentos_restantes = limit - attempts
                log_security_event('LOGIN_ATTEMPT', 'FAILURE', user_id=email, details=f"Wrong affiliate credentials from {ip}. Attempt {attempts}")
                flash(f'Email o contraseña incorrectos. Intentos restantes: {intentos_restantes}', 'error')

    return render_template('auth/afiliado_login.html')


@bp.route('/logout', methods=['POST'])
def logout():
    """Logout general — Solo POST para prevenir CSRF de cierre de sesión"""
    user_type = session.get('user_type')
    logout_user()
    session.clear()

    flash('Has cerrado sesión exitosamente', 'success')

    # Redirigir según el tipo de usuario
    if user_type == 'admin':
        return redirect(url_for('auth.admin_login'))
    elif user_type == 'afiliado':
        return redirect(url_for('auth.afiliado_login'))
    else:
        return redirect(url_for('tienda.index'))