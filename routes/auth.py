"""
Rutas de autenticación
Maneja login/logout para Admin y Afiliado
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, current_user
from datetime import datetime, timedelta  # Para manejar el bloqueo temporal de login

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Login de administrador"""
    from models import Admin

    if current_user.is_authenticated:
        # Si ya está logueado, redirigir al dashboard correspondiente
        if isinstance(current_user, Admin):
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('afiliado.dashboard'))


    #INICIA LOS CAMBIOS INDICADOS EN FASE 1
    # SEGURIDAD: Verificar si el usuario está bloqueado temporalmente por demasiados intentos fallidos
    # Ayuda a mitigar ataques de fuerza bruta al forzar un tiempo de espera
    if 'admin_login_lock' in session:
        lock_until = datetime.fromisoformat(session['admin_login_lock'])
        if datetime.now() < lock_until:
            minutos_restantes = int((lock_until - datetime.now()).total_seconds() // 60) + 1
            flash(f'Demasiados intentos fallidos. Por seguridad, espera {minutos_restantes} minuto(s).', 'error')
            return render_template('auth/admin_login.html')

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Por favor completa todos los campos', 'error')
            return render_template('auth/admin_login.html')

        # 1. Validar contra las credenciales de administrador mediante .env
        from flask import current_app
        is_correct_admin = (
            username == current_app.config['ADMIN_USER'] and 
            password == current_app.config['ADMIN_PASS']
        )

        if is_correct_admin:
            # 2. Sincronizar con el ÚNICO registro permitido en la base de datos
            from models import db
            # Siempre intentamos obtener el primer administrador (ID 1 o cualquiera que exista)
            admin = Admin.query.first()
            
            if not admin:
                # Crear el registro único si la tabla está vacía
                admin = Admin(username=username)
                db.session.add(admin)
            else:
                # Sincronizar nombre de usuario con el registro existente
                admin.username = username
            
            # Sincronizar siempre el hash de la contraseña por seguridad y consistencia
            admin.set_password(password)
            db.session.commit()

            # Login exitoso
            login_user(admin)
            session['user_type'] = 'admin'
            session['user_id'] = f'admin_{admin.id}'

            # Login exitoso: Limpiar rastros de intentos fallidos previos
            session.pop('admin_login_attempts', None)
            session.pop('admin_login_lock', None)

            flash(f'¡Bienvenido {admin.username}!', 'success')

            # Redirigir a la página solicitada o al dashboard
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('admin.dashboard'))
        else:
            # SEGURIDAD: Incrementar contador de intentos fallidos
            attempts = session.get('admin_login_attempts', 0) + 1
            session['admin_login_attempts'] = attempts
            
            # Si se supera el límite definido en config.py, se bloquea la sesión temporalmente
            if attempts >= current_app.config.get('LOGIN_ATTEMPTS_LIMIT', 5):
                lock_time = current_app.config.get('LOGIN_LOCK_MINUTES', 5)
                session['admin_login_lock'] = (datetime.now() + timedelta(minutes=lock_time)).isoformat()
                flash(f'Has superado el límite de intentos. Bloqueado por {lock_time} minutos.', 'error')
            else:
                intentos_restantes = current_app.config.get('LOGIN_ATTEMPTS_LIMIT', 5) - attempts
                flash(f'Usuario o contraseña incorrectos. Intentos restantes: {intentos_restantes}', 'error')

    return render_template('auth/admin_login.html')
    #FIN DE LOS CAMBIOS INDICADOS EN FASE 1

@bp.route('/afiliado/login', methods=['GET', 'POST'])
def afiliado_login():
    """Login de afiliado"""
    from models import Afiliado

    if current_user.is_authenticated:
        # Si ya está logueado, redirigir al dashboard correspondiente
        if isinstance(current_user, Afiliado):
            return redirect(url_for('afiliado.dashboard'))
        else:
            return redirect(url_for('admin.dashboard'))

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

            flash(f'¡Bienvenido {afiliado.nombre}!', 'success')

            # Redirigir a la página solicitada o al dashboard
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('afiliado.dashboard'))
        else:
            flash('Email o contraseña incorrectos', 'error')

    return render_template('auth/afiliado_login.html')


@bp.route('/logout')
def logout():
    """Logout general"""
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

# =====================================================================
# CÓDIGO COMENTADO Y DESACTIVADO POR SEGURIDAD (Error Crítico E39):
# Se desactiva este endpoint porque permitía Fuga de Información 
# y exposición pasiva de IDs de sesión (Information Disclosure).
# =====================================================================
# @bp.route('/check-session')
# def check_session():
#     """Endpoint para verificar sesión (útil para debugging)"""
#     if current_user.is_authenticated:
#         return {
#             'authenticated': True,
#             'user_type': session.get('user_type'),
#             'user_id': session.get('user_id')
#         }
#     return {'authenticated': False}

"""
======================================================================
REPORTE DE AUDITORÍA Y CORRECCIÓN (FASE 1)
======================================================================
Error Mitigado: E39 - Fuga de Información (Information Disclosure).

¿Qué se hizo?
- Se comentó y desactivó permanentemente el endpoint `/check-session`.

¿A qué afecta operacionalmente?
- Afectación: CERO (0). 
- Justificación: Se verificó el código del frontend (Jinja/JS) y ninguna 
  vista consume esta API. La tienda funciona puramente por renderizado 
  desde el servidor validando con `current_user.is_authenticated`.

¿Qué riesgos se eliminaron?
- Se neutralizó la enumeración de roles. Un atacante ya no puede 
  consultar externamente qué 'user_id' o 'user_type' posee una sesión,
  bloqueando una fase vital de reconocimiento para el secuestro de cuentas.
======================================================================
"""


