import os
from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
from flask_cors import CORS
from flask_mail import Mail
from config import Config
from utils.rate_limit import limiter

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
file_handler = logging.FileHandler('logs/ecommerce.log')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)

csrf = CSRFProtect()

# [FASE 3 / SOPORTE] Instancia global de Flask-Mail
mail = Mail()

# FASE 4: Inicialización de Flask-Migrate para gestión segura de esquemas BD
from flask_migrate import Migrate
migrate = Migrate()


def create_app(config_class=Config):
    """Factory para crear la aplicación Flask"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # FASE 2: Integrar ProxyFix para resolver la vulnerabilidad de Spoofing de IP
    # Asegura que request.remote_addr contenga la IP real del cliente detrás de Render/Nginx
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # FASE 9: Restringir CORS de la API de IA para evitar robo de cuota desde embebidos externos
    allowed_origins = os.environ.get('ALLOWED_ORIGINS').split(',')
    CORS(app, resources={r"/ai/*": {"origins": [origin.strip() for origin in allowed_origins]}})

    # Inicializar extensiones con la app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # [FASE 3 / SEGURIDAD E22]
    # Inicialización de CSRF para protección criptográfica (E43) y validación de formularios (E22)
    csrf.init_app(app)

    # [FASE 4 / SEGURIDAD - ANTI-DDOS]
    # Inicialización del limitador de tráfico
    limiter.init_app(app)

    # [FASE 3 / SOPORTE] Configuración y arranque de Flask-Mail
    app.config['MAIL_SERVER']   = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT']     = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS']  = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')
    mail.init_app(app)

    # [FASE 2 / SEGURIDAD - MURALLA EXTERIOR]
    # Configuración de Content Security Policy (CSP) y Headers de Seguridad
    csp = {
        'default-src': "'self'",
        'script-src': [
            "'self'",
            "'unsafe-inline'",  # Permitir scripts en línea necesarios para la lógica actual
            "https://www.paypal.com",
            "https://www.sandbox.paypal.com"
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'",  # Requerido para variables de color dinámicas (White-Label)
            "https://fonts.googleapis.com"
        ],
        'font-src': [
            "'self'",
            "https://fonts.gstatic.com"
        ],
        'img-src': [
            "'self'",
            "data:",
            "*"  # Permitir imágenes de cualquier fuente para productos externos
        ],
        'connect-src': [
            "'self'",
            "https://www.paypal.com",
            "https://www.sandbox.paypal.com"
        ],
        'frame-src': [
            "'self'",
            "https://www.paypal.com",
            "https://www.sandbox.paypal.com"
        ],
        'object-src': "'none'", # Bloquear plugins peligrosos (Flash, Java, etc.)
        'media-src': "'self'" # Permitir solo videos/audio locales (fondo de pantalla)
    }

    Talisman(
        app,
        content_security_policy=csp,
        force_https=app.config.get('FLASK_ENV') == 'production', 
        strict_transport_security=True,
        session_cookie_secure=app.config.get('FLASK_ENV') == 'production',
        frame_options='SAMEORIGIN',
        referrer_policy='strict-origin-when-cross-origin' # Protege la privacidad en enlaces externos
    )

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
    app.logger.info('Plataforma Ecommerce - Sistema Iniciado')

    # Registrar blueprints (rutas)
    from routes import auth, admin, afiliado, tienda, ai, facturacion
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(afiliado.bp)
    app.register_blueprint(tienda.bp)
    app.register_blueprint(ai.bp)
    app.register_blueprint(facturacion.bp)
    
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

    # FASE 9: Centralización declarativa de exclusiones CSRF (Previene olvidos en futuros endpoints)
    csrf_exempt_endpoints = [
        'routes.tienda.paypal_webhook',
        'routes.ai.chat',
        'routes.facturacion.generar_factura'
    ]
    for endpoint in csrf_exempt_endpoints:
        csrf.exempt(endpoint)

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

    # FASE 4: Se eliminó db.create_all() y las migraciones manuales.
    # Ahora el esquema de base de datos se gestionará profesionalmente con Flask-Migrate (Alembic)
    # mediante los comandos: flask db init, flask db migrate, flask db upgrade.

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