import os
from datetime import timedelta
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Config:
    """Configuración de la aplicación blindada (Hardening Fase 1)"""

    @staticmethod
    def get_required_env(name, production_only=False):
        """FASE 8: Obtiene una variable de entorno o lanza error fatal si falta (Obligatorio en Producción)."""
        val = os.environ.get(name)
        if not val:
            if production_only and os.environ.get('FLASK_ENV') != 'production':
                return None
            raise EnvironmentError(f"ERROR DE SEGURIDAD CRÍTICO: La variable de entorno '{name}' es obligatoria en este entorno.")
        return val

    # Secret key para sesiones y CSRF - OBLIGATORIO
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY or len(SECRET_KEY) < 32:
        # Error crítico: El sistema no debe arrancar sin su SECRET KEY o si esta es muy débil
        raise EnvironmentError("ERROR DE SEGURIDAD CRÍTICO: La variable 'SECRET_KEY' no está configurada o es demasiado débil (mínimo 32 caracteres).")

    # Credenciales de Administrador Único (Blindaje E21)
    ADMIN_USER = os.environ.get('ADMIN_USER')
    ADMIN_PASS = os.environ.get('ADMIN_PASS')
    
    # Validación de credenciales en arranque
    if not ADMIN_USER or not ADMIN_PASS:
        # Solo permitimos que falten si estamos en modo desarrollo local muy básico
        if os.environ.get('FLASK_ENV') == 'production':
            raise EnvironmentError("ERROR DE SEGURIDAD: ADMIN_USER o ADMIN_PASS no configurados.")

    # Configuración de base de datos
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    """Pool de conexiones para evitar agotar las conexiones bajo carga:
        pool_size: crea un máximo de N conexiones a la base de datos al mismo tiempo.
        pool_recycle: reinicia la conexión cada N segundos para evitar problemas de expiración.
        pool_pre_ping True: verifica si la conexión está activa antes de usarla.
    """
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 20,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }
    #FIN DE LOS CAMBIOS INDICADOS EN FASE 1 DE HARDENING

    # Modo Debug (Controlado estrictamente por entorno)
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
    LOGIN_ATTEMPTS_LIMIT = 5  # Máximo de intentos permitidos antes de bloquear
    LOGIN_LOCK_MINUTES = 5    # Tiempo de espera (en minutos) tras superar el límite de intentos
    
    #FIN DE LOS CAMBIOS INDICADOS EN FASE 1

    # FASE 7: Configuración robusta de WhatsApp (Evitar cadena vacía silenciosa)
    WHATSAPP_NUMBER = os.environ.get('WHATSAPP_NUMBER', '').strip()
    if not WHATSAPP_NUMBER:
        import logging
        logging.warning("⚠️ ALERTA FASE 7: WHATSAPP_NUMBER no está configurado. Las funciones de redirección a WhatsApp de la tienda principal podrían fallar.")

    # Configuración de archivos
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'ico'}

    # Configuración de Web Scraping Seguro (Fase 1)
    # Lista Blanca de dominios autorizados para la herramienta de IA (Evita SSRF y lecturas maliciosas)
    SCRAPING_WHITELIST = [
        'wikipedia.org',
        'example.com',
        'apple.com',
        'samsung.com',
        'mercadolibre.com.pe',
        'amazon.com'
    ]

    # Configuración de PayPal (FASE 8: Validación estricta en producción)
    PAYPAL_CLIENT_ID = get_required_env.__func__('PAYPAL_CLIENT_ID', production_only=True)
    PAYPAL_SECRET = get_required_env.__func__('PAYPAL_SECRET', production_only=True)
    PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')  # 'sandbox' o 'live'
    PAYPAL_WEBHOOK_ID = get_required_env.__func__('PAYPAL_WEBHOOK_ID', production_only=True)  # ID del Webhook para validación criptográfica

    # [FASE 3 / E39 - ERRORES MEDIOS] Seguridad de Cookies de Sesión
    # HTTPOnly: Impide que JavaScript acceda a la cookie (Protección XSS)
    SESSION_COOKIE_HTTPONLY = True
    # SameSite: Controla el envío de cookies en peticiones de terceros (Protección CSRF)
    SESSION_COOKIE_SAMESITE = 'Strict'
    # Secure: Solo envía cookies por HTTPS si el entorno es producción
    SESSION_COOKIE_SECURE = (os.environ.get('FLASK_ENV') == 'production')

    # Duración de la cookie permanente
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)  # 1 mes para evitar brechas de seguridad