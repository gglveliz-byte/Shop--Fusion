from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import redis

# FASE 2: Integración estricta de Redis para persistencia multi-worker
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
is_development = os.environ.get('FLASK_ENV', 'production') == 'development'

class DummyRedis:
    """Mock básico de Redis para entorno de desarrollo local sin servidor Redis activo."""
    def __init__(self):
        self.store = {}
    def exists(self, key): return key in self.store
    def ttl(self, key): return 60
    def delete(self, key): self.store.pop(key, None)
    def incr(self, key): 
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]
    def expire(self, key, time): pass
    def setex(self, key, time, value): self.store[key] = value

if is_development:
    storage_uri = "memory://"
    redis_client = DummyRedis()
else:
    storage_uri = redis_url
    redis_client = redis.from_url(redis_url, decode_responses=True)

# Inicializamos el limitador de velocidad.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=storage_uri,
    strategy="moving-window"
)