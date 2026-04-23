import os
from datetime import timedelta  # <--- esto faltaba
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Config:
    """Configuración de la aplicación"""

    # Secret key para sesiones
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Configuración de base de datos
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Modo Debug (Desactivado por defecto para corregir E21)
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']

    #INICIA LOS CAMBIOS INDICADOS EN FASE 1
    # Credenciales de Administrador Único obtenidos del .env
    ADMIN_USER = os.environ.get('ADMIN_USER')
    ADMIN_PASS = os.environ.get('ADMIN_PASS')

    # Seguridad de Login: Previene ataques de fuerza bruta al limitar intentos fallidos
    LOGIN_ATTEMPTS_LIMIT = 5  # Máximo de intentos permitidos antes de bloquear
    LOGIN_LOCK_MINUTES = 5    # Tiempo de espera (en minutos) tras superar el límite de intentos
    
    #FIN DE LOS CAMBIOS INDICADOS EN FASE 1

    # Configuración de sesiones
    SESSION_COOKIE_SECURE = False  # Cambiar a True en producción con HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Configuración de WhatsApp
    WHATSAPP_NUMBER = ''  # CAMBIAR POR TU NÚMERO (sin espacios, con código de país)

    # Configuración de archivos
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

    # Configuración de PayPal
    PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID')
    PAYPAL_SECRET = os.environ.get('PAYPAL_SECRET')
    PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')  # 'sandbox' o 'live'

    # Duración de la cookie permanente
    PERMANENT_SESSION_LIFETIME = timedelta(days=180)  # 3 meses