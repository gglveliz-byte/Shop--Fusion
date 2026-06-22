from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import redis

# FASE 2: Integración estricta de Redis para persistencia multi-worker
# Cuando se pase a producción, se debe eliminar 'redis://localhost:6379' de la línea de abajo.
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
# Instanciamos el cliente de Redis para re-usarlo en toda la app (ej. auth.py)
redis_client = redis.from_url(redis_url, decode_responses=True)

# Inicializamos el limitador de velocidad.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=redis_url,
    # FASE 2: 'moving-window' evita ataques de ráfaga
    strategy="moving-window"
)