import os
from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config

# Importar db desde models
from models import db, setup_login_manager

# Inicializar login manager
login_manager = LoginManager()

# [MODIFICACIÓN SEGURIDAD E22 / FASE 3]
# Inicialización de protección CSRF global para mitigación de E22 y blindaje E43.
import logging
from logging.handlers import RotatingFileHandler

# [FASE 5 / SEGURIDAD E5]
# Configuración de Logging Profesional para trazabilidad y auditoría.
if not os.path.exists('logs'):
    os.mkdir('logs')

logging.basicConfig(level=logging.INFO)
file_handler = RotatingFileHandler('logs/shop_fusion.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)

csrf = CSRFProtect()


def create_app(config_class=Config):
    """Factory para crear la aplicación Flask"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar extensiones con la app
    db.init_app(app)
    login_manager.init_app(app)
    
    # [FASE 3 / SEGURIDAD E22]
    # Inicialización de CSRF para protección criptográfica (E43) y validación de formularios (E22)
    csrf.init_app(app)

    #INICIA LOS CAMBIOS INDICADOS EN FASE 1
    # Configuración de la vista de login por defecto para redirecciones automáticas de Flask-Login.
    # Ayuda a evitar errores 500 cuando el contexto de usuario no es válido.
    login_manager.login_view = 'auth.admin_login'
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
    #FIN DE LOS CAMBIOS INDICADOS EN FASE 1

    # Configurar user loader
    setup_login_manager(login_manager)

    # Crear carpeta de uploads si no existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # [FASE 5 / E5] Activar log en archivo
    app.logger.addHandler(file_handler)
    app.logger.info('Shop Fusion Startup')

    # Registrar blueprints (rutas)
    from routes import auth, admin, afiliado, tienda
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(afiliado.bp)
    app.register_blueprint(tienda.bp)
    
    # [Fase 1 / WHITE-LABEL] Inyectar configuración de marca globalmente
    @app.context_processor
    def inject_branding():
        from models import Configuracion
        try:
            config = Configuracion.query.first()
            return dict(config_web=config)
        except Exception:
            # Si falla (ej: tabla no creada aún), devolvemos un diccionario vacío para evitar errores 500
            return dict(config_web=None)

    # [FASE 3 / E43] Eximir el webhook de PayPal de la protección CSRF
    csrf.exempt('routes.tienda.paypal_webhook')

    # Manejadores de errores
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template(
            'error.html',
            error_code=404,
            error_title='Página no encontrada',
            error_message='La página que buscas no existe o fue movida.'
        ), 404

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f'Server Error: {e}')
        return render_template(
            'error.html',
            error_code=500,
            error_title='Error del servidor',
            error_message='Algo salió mal en nuestro servidor. Intenta de nuevo más tarde.'
        ), 500

    @app.errorhandler(403)
    def forbidden(e):
        app.logger.warning(f'Forbidden Access: {e}')
        return render_template(
            'error.html',
            error_code=403,
            error_title='Acceso denegado',
            error_message='No tienes permiso para acceder a esta página.'
        ), 403

    @app.errorhandler(400)
    def bad_request(e):
        return render_template(
            'error.html',
            error_code=400,
            error_title='Solicitud incorrecta',
            error_message='La solicitud no pudo ser procesada.'
        ), 400

    # Crear tablas en la base de datos
    with app.app_context():
        db.create_all()

    return app


# 👇👇👇 ESTO ES LO QUE ARREGLA RENDER 👇👇👇
app = create_app()


# [MODIFICACIÓN SEGURIDAD E21] 
# Se cambió 'app.run(debug=True)' por 'app.run(debug=app.config["DEBUG"])'
# Archivo dependiente modificado: config.py (donde se definió DEBUG basado en variables de entorno)
# Razón: Prevenir la exposición de la consola interactiva de Werkzeug en producción.
if __name__ == "__main__":
    # El valor de debug ahora se controla desde config.py / variables de entorno
    app.run(debug=app.config.get('DEBUG', False))
