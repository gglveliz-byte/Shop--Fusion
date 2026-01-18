from flask import Flask, render_template
from flask_login import LoginManager
from config import Config
import os

# Importar db desde models
from models import db, setup_login_manager

# Inicializar login manager
login_manager = LoginManager()

def create_app(config_class=Config):
    """Factory para crear la aplicación Flask"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar extensiones con la app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'

    # Configurar user loader
    setup_login_manager(login_manager)

    # Crear carpeta de uploads si no existe
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Registrar blueprints (rutas)
    from routes import auth, admin, afiliado, tienda
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(afiliado.bp)
    app.register_blueprint(tienda.bp)

    # Manejadores de errores
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html',
                             error_code=404,
                             error_title='Página no encontrada',
                             error_message='La página que buscas no existe o fue movida.'), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template('error.html',
                             error_code=500,
                             error_title='Error del servidor',
                             error_message='Algo salió mal en nuestro servidor. Intenta de nuevo más tarde.'), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('error.html',
                             error_code=403,
                             error_title='Acceso denegado',
                             error_message='No tienes permiso para acceder a esta página.'), 403

    @app.errorhandler(400)
    def bad_request(e):
        return render_template('error.html',
                             error_code=400,
                             error_title='Solicitud incorrecta',
                             error_message='La solicitud no pudo ser procesada.'), 400

    # Crear tablas en la base de datos
    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
