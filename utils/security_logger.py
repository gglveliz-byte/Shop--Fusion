import logging
import os
from datetime import datetime
from flask import request, current_app
from logging.handlers import RotatingFileHandler

# Asegurar que la carpeta de logs existe
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configuración del Logger de Seguridad
security_logger = logging.getLogger('security_sentinel')
security_logger.setLevel(logging.INFO)

# Formato forense: Tiempo | IP | Evento | Usuario | Detalles
formatter = logging.Formatter(
    '[%(asctime)s] [%(levelname)s] [IP: %(remote_addr)s] - %(message)s'
)

# Rotación de logs: 5MB por archivo, máximo 5 archivos de respaldo
file_handler = RotatingFileHandler(
    'logs/security.log', 
    maxBytes=5*1024*1024, 
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)
security_logger.addHandler(file_handler)

def log_security_event(event_type, status, user_id=None, details=""):
    """
    Registra un evento de seguridad con detalles forenses.
    
    event_type: 'LOGIN', 'LOGOUT', 'CONFIG_CHANGE', 'BRUTE_FORCE_DETECTED', etc.
    status: 'SUCCESS', 'FAILURE', 'BLOCKED'
    """
    # Intentar obtener la IP real (solo si hay contexto web)
    from flask import has_request_context, has_app_context
    remote_addr = '0.0.0.0'
    
    if has_request_context():
        # FASE 6.2: Solo confiar en X-Forwarded-For si la petición proviene de un proxy de confianza.
        # Leer la lista desde la configuración centralizada (config.py → TRUSTED_PROXIES).
        trusted_proxies = set()
        if has_app_context():
            trusted_proxies = current_app.config.get('TRUSTED_PROXIES', {'127.0.0.1', '::1'})

        direct_ip = request.remote_addr or '0.0.0.0'

        if direct_ip in trusted_proxies:
            # Proxy de confianza: leer el header y tomar solo la primera IP de la cadena
            forwarded_for = request.headers.get('X-Forwarded-For', direct_ip)
            remote_addr = forwarded_for.split(',')[0].strip()
        else:
            # Conexión directa o proxy no confiable: usar la IP de la conexión TCP real
            remote_addr = direct_ip

    extra = {'remote_addr': remote_addr}
    
    log_msg = f"[{event_type}] [{status}] | User: {user_id or 'Guest'} | Details: {details}"
    
    if status == 'FAILURE' or status == 'BLOCKED':
        security_logger.warning(log_msg, extra=extra)
    else:
        security_logger.info(log_msg, extra=extra)

    # También enviar al log de la aplicación para visibilidad inmediata en consola (solo si hay app context)
    if has_app_context():
        current_app.logger.info(f"SECURITY EVENT: {log_msg}")
