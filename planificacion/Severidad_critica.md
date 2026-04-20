# 🔴 Severidad Crítica (FASE 1)
**Nivel de Prioridad:** Máxima / Blocker.
**Objetivo:** Evitar la toma de control del sistema por parte de atacantes externos y fugas pasivas de información.

Este documento provee a los desarrolladores con el código exacto, las alternativas arquitectónicas y el análisis de riesgos al intervenir estas áreas sensibles.

---

## 1. Eliminar Fugas de Sesión (`/check-session`)
**El Problema:** El endpoint en `routes/auth.py` no está protegido y devuelve el rol del usuario actual. Esto permite enumeración de roles.

### Código de Solución Recomendado:
La mejor solución es **eliminar** la ruta por completo suprimiendo estas líneas en `auth.py`:
```python
# ELIMINAR ESTE BLOQUE COMPLETO
@bp.route('/check-session')
def check_session():
    if current_user.is_authenticated:
        return {'authenticated': True, 'user_type': session.get('user_type')}
    return {'authenticated': False}
```

### 🔁 Alternativa (Si el Frontend lo necesita):
Si tu Vanilla JS necesita imperativamente esta ruta para pintar la UI (por ejemplo, ocultar el botón "Login"), en lugar de borrarlo, protégelo bloqueando información sensible y usando un Rate Limiter:
```python
from flask_limiter import Limiter

@bp.route('/check-session')
@limiter.limit("10 per minute") # Evita bombardeos de requests
def check_session():
    # Devuelve solo un booleano genérico, jamás devuelvas el 'user_type' o el 'id'
    return {'logged_in': current_user.is_authenticated}
```

### ⚠️ Riesgos de Modificar esto:
Si eliminas la ruta abruptamente y tu `index.html` hace llamadas fetch recurrentes a `/check-session` mediante Javascript, la consola del navegador del cliente se llenará de errores `404 Not Found` y algunas partes dinámicas de tu interfaz podrían congelarse. Es mandatorio revisar si `index.html` llama a esta URL antes de borrarla.

---

## 2. Refactorización a Variables de Entorno (Aislamiento Total)
**El Problema:** Claves quemadas en `app.py`, `init_db.py` y `config.py`. Exponer `debug=True` habilita el depurador Werkzeug, otorgando acceso a la terminal del servidor si hay un error.

### Código de Solución Recomendado:
**Paso A (Terminal):** Instalar módulo:
`pip install python-dotenv`

**Paso B (En `config.py` y `app.py`):**
```python
import os
from dotenv import load_dotenv

load_dotenv() # Carga variables del archivo físico .env

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24))
    DATABASE_URL = os.environ.get('DATABASE_URL')
    WHATSAPP_NUMBER = os.environ.get('WHATSAPP_NUMBER')
    ADMIN_USER = os.environ.get('ADMIN_USER')
```
*En `app.py` línea 87:*
```python
if __name__ == "__main__":
    # Lee 'FLASK_DEBUG' del txt, por defecto asume Falso por seguridad extrema.
    is_debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=is_debug)
```

### 🔁 Alternativas:
Para la etapa Multitenant SaaS, en lugar de un archivo `.env` plano, se pueden usar gestores empresariales como **AWS Secrets Manager** o inyectar las credenciales mediante los *Pipelines de CI/CD* (GitHub Actions) al momento del despliegue.

### ⚠️ Riesgos de Modificar esto:
Si el desarrollador olvida crear el archivo `.env` manual en producción, el servidor colapsará de inmediato (`app.run` no conectará a la BD). Esto no es un error, es un patrón de diseño llamado **"Fail-Fast"** (Falla Rápido). Es 1000 veces preferible que la tienda no arranque a que arranque con credenciales nulas o valores por defecto.

---

## 3. Vulnerabilidad de Request Forgery (CSRF)
**El Problema:** La ausencia de candados en peticiones POST permite que sitios maliciosos tercerizados envíen acciones directas a los endpoints administrados (Ej: Forzar creación de productos).

### Código de Solución Recomendado:
Asegurarse de tener `Flask-WTF` instalado.
**En `app.py`:**
```python
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config.from_object(Config)
csrf = CSRFProtect(app) # ⬅️ Inicialización Global del Escudo CSRF
```
**En cualquier archivo de `templates/`:** (Ejemplo: `auth/admin_login.html`)
Debes inyectar obligatoriamente la llamada a `csrf_token()` en todo formulario:
```html
<form method="POST" action="/auth/admin/login">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/> <!-- ⬅️ ESTO ES VITAL -->
    <!-- resto de tus inputs... -->
</form>
```

### 🔁 Alternativas:
Utilizar Autenticación sin estado (*Stateless Authentication*) basaba puramente en **JWT Token Headers** (Ej: enviar `Authorization: Bearer <token>` en cada Fetch JS). Elimina la necesidad de CSRF, pero requiere reescribir por completo la arquitectura de `flask_login` actual.

### ⚠️ Riesgos de Modificar esto:
El riesgo de implementación aquí es **brutal**. Si te olvidas de inyectar el código `<input type="hidden">` incluso en uno solo de tus formularios POST a lo largo del sistema web, el servidor Flask **bloqueará la solicitud y lanzará un Error 400 Bad Request** de forma rígida y los clientes no podrán comprar o el administrador no podrá validar pedidos. Hay que hacer esto con pinzas en cada `html`.

---

## 4. Peligro Crítico de "Bypass" de Autenticación (`None == None`)
**El Problema:** La comparación insegura en memoria. Si el atacante altera el payload e instruye enviar nulos, Python evalúa el login y da acceso sin contraseña.

### Código de Solución Recomendado:
En `routes/auth.py` en la zona de Admin Login:
```python
import hmac
from flask import current_app, abort

# 1. Recuperar info vital y sanitizar strings
username_input = request.form.get('username', '')
password_input = request.form.get('password', '')

admin_env = current_app.config.get('ADMIN_USER')
pass_env = current_app.config.get('ADMIN_PASS')

# 2. Hard Check: Jamás evaluar Nulos
if not admin_env or not pass_env:
    # La configuración del servidor está rota, negamos servicio
    return abort(500, description="Servidor mal configurado")

if not username_input or not password_input:
    flash('Credenciales vacías', 'error')
    return render_template('auth/admin_login.html')

# 3. Comparación Segura de Tiempos (Mitiga fuerza bruta de tiempo de CPU)
is_valid_user = hmac.compare_digest(username_input, admin_env)
is_valid_pass = hmac.compare_digest(password_input, pass_env)

if is_valid_user and is_valid_pass:
    # Continuar con el login de flask_login...
```

### 🔁 Alternativas:
Obligar siempre al Administrador a loguearse contra la Tabla `Admin` de la Base de Datos (`Admin.query.filter_by...`) de la cual se asegura la no-nulidad usando las restricciones nativas del esquema SQL, anulando por completo la autenticación por variables de entorno. 

### ⚠️ Riesgos de Modificar esto:
Utilizar `hmac.compare_digest()` es obligatorio por ciberseguridad, pero tiene un defecto si lo programamos ciegamente: la función falla agresivamente (lanza `TypeError`) si llega a recibir un valor `None` o de tipo Entero. Por ello, el paso #2 en donde bloqueamos usuarios vacíos es obligatorio para evitar una "Caída del Servidor (Denial of Service)".
