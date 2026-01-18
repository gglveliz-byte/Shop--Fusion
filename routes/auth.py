"""
Rutas de autenticación
Maneja login/logout para Admin y Afiliado
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user

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

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Por favor completa todos los campos', 'error')
            return render_template('auth/admin_login.html')

        # Buscar admin
        admin = Admin.query.filter_by(username=username).first()

        if admin and admin.check_password(password):
            # Login exitoso
            login_user(admin)
            session['user_type'] = 'admin'
            session['user_id'] = f'admin_{admin.id}'

            flash(f'¡Bienvenido {admin.username}!', 'success')

            # Redirigir a la página solicitada o al dashboard
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('admin.dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')

    return render_template('auth/admin_login.html')


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


@bp.route('/check-session')
def check_session():
    """Endpoint para verificar sesión (útil para debugging)"""
    if current_user.is_authenticated:
        return {
            'authenticated': True,
            'user_type': session.get('user_type'),
            'user_id': session.get('user_id')
        }
    return {'authenticated': False}
