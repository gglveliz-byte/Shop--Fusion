# 🟢 Severidad Baja (FASE 4)
**Nivel de Prioridad:** Optimizaciones a largo plazo.
**Objetivo:** Suavizar el performance (velocidad de cara al cliente y al servidor) reduciendo consultas base-datos ahogadoras.

---

## 1. El Mal de la Consultas en Cadena (The N+1 Query Problem)
**El Problema:** Al listar digamos, los 1000 pedidos en el panel del administrador (`routes/admin.py`), el ecosistema de tu código (ORM SQLAlchemy) realiza secretamente 1 petición inmensa para pedir las órdenes y luego **genera 1000 pequeñas peticiones consecutivas** cada vez que el HTML de tu Jinja (`pedidos.html`) pregunta por el nombre del relacionamiento del afiliado `{{ pedido.afiliado.username }}`. Esto destruirá la RAM y Latencia de tu base de datos y la velocidad de respuesta caerá radicalmente a los 2 años.

### Código de Solución Recomendado:
**En tu render de rutas (`admin.py`):**
Cargar las tablas acopladas en una sola bala y de manera anticipada (*Eager Loading*).
```python
from sqlalchemy.orm import joinedload

# Enviar los pedidos pero ordenándole a SQLAlchemy que incluya 
# por detrás mágicamente la tabla afiliados en UN SOLO viaje.
mis_pedidos = Pedido.query.options(joinedload(Pedido.afiliado)).all()
```

### 🔁 Alternativas:
Ejecutar código nativo bruto de SQL en lugar de depender del Framework de Modelos ORM, algo que es ultraligero y rápido, pero dificulta la legibilidad para los juniors en python. `db.session.execute('SELECT * FROM pedido JOIN afiliado ON...')`

### ⚠️ Riesgos de Modificar esto:
El exceso de `joinedload()` en listados gigantescos con 12 relaciones (`comisiones`, `productos`, `compradores`, `envios`) causará cuellos de botellas opuestos y el Backend colapsará bajo carga excesiva de memoria (Ram Bloat). Solo utilizar `joinedload` en llamadas obligatorias hacia entidades externas.

---

## 2. Estrés Criptográfico Constante
**El Problema:** Noté en tu ruta antigua `auth.py` un patrón que, en algunos momentos de evaluación, forzaba el "Hash" nativo con la librería de cifrado (Bcrypt/Werkzeug). La criptografía fue diseñada por expertos paramátricamente y es matemáticamente "lenta". Forzar evaluaciones de textos planos que fallan sin bloqueadores (rate-limiting), permite vulnerabilidades de *Denegación de Servicios (DDoS)*: un atacante inyecta 5,000 requests erráticos, tu CPU llega al 100% de uso calculando encripciones descartables, y tu tienda cae (Status 502/503).

### Código de Solución Recomendado:
Nunca utilices comparativas hash sin antes asegurar una capa de cortafuegos. Implementar la validación perimetral (Rate Limits) para evitar estrés en tu servidor antes de llegar al punto pesado (el backend).
En tu futura actualización de Multitenant:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    # Registra las IPs del infractor
    key_func=get_remote_address,
    app=app
)

# Cortamos su acceso tras 5 intentos fallidos
@bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute", error_message="Demasiados intentos.")
def login():
    # Continuar aquí la carga de Hashes criptográficos...
```

### 🔁 Alternativas:
Implementar **Cloudflare** desde afuera (Malla externa de capa 7), que intercepte y absorba ataques y bots protegiendo al servidor sin escribir código de backend.

### ⚠️ Riesgos de Modificar esto:
En implementaciones erróneas donde múltiples afiliados compartan una misma IP pública corporativa (Ej: una oficina llena de promotores que se loguean), un `Rate Limiter` basado puramente en la `Dirección IP` vetará a la oficina entera si uno de ellos introduce mal su clave 5 veces. La limitación debe calibrarse usando lógicas basadas en nombre de sesiones.
