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
    # Intentar obtener la IP real (incluso detrás de proxies como Render/Cloudflare)
    remote_addr = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in str(remote_addr):
        remote_addr = remote_addr.split(',')[0].strip()

    extra = {'remote_addr': remote_addr}
    
    log_msg = f"[{event_type}] [{status}] | User: {user_id or 'Guest'} | Details: {details}"
    
    if status == 'FAILURE' or status == 'BLOCKED':
        security_logger.warning(log_msg, extra=extra)
    else:
        security_logger.info(log_msg, extra=extra)

    # También enviar al log de la aplicación para visibilidad inmediata en consola
    current_app.logger.info(f"SECURITY EVENT: {log_msg}")
