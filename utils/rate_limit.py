from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Inicializamos el limitador de velocidad.
# Usamos 'get_remote_address' para identificar a los usuarios por su IP.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"], # Límites globales generosos
    storage_uri="memory://", # Guardar datos en memoria RAM (rápido y seguro para este volumen)
    strategy="fixed-window"
)

