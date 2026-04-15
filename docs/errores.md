# Registro de Errores - Shop Fusion (Resumido)

## Referencia Rápida

| Prioridad | Error | Ubicación | Acción |
|-----------|-------|-----------|--------|
| 🔴 | Import `os` faltante      | `app.py:27` | Agregar `import os` |
| 🔴 | `codigo` puede ser nulo   | `routes/admin.py:439` | Validar existencia |
| 🔴 | Config insegura           | `config.py` | Requerir vars entorno |
| � | Sin rate limiting login    | `routes/auth.py` | Usar flask-limiter |
| 🟡 | print() en producción     | `migrate_db.py`, `init_db.py` | Usar logging |
| 🟡 | Excepciones genéricas     | `routes/admin.py`, `tienda.py`, `afiliado.py` | Capturar específicas |
| 🟡 | Contraseñas débiles       | `init_db.py` | Generar aleatorias |
| 🟡 | Validación WhatsApp faltante | `routes/afiliado.py:286` | Validar formato |
| 🟡 | Cambio contraseña sin validación | `routes/afiliado.py:289` | Validar fortaleza |
| 🟡 | Endpoint expone sesión    | `routes/auth.py:101+` | Eliminar o proteger |
| 🟡 | Credenciales en docs      | `README.md`, `bd.md` | Reemplazar por placeholders |
| 🟢 | Código duplicado WhatsApp | `routes/tienda.py` | Crear función |
| 🟢 | Sin validación entrada    | Todos forms | Usar WTForms |

---

## Errores Críticos (🔴 Arreglar Ahora)

### E1: Import `os` Faltante
**Archivo**: `app.py:27` - Agregar `import os` para crear carpetas

**Para desarrolladores nuevos**: Abre el archivo `app.py` en tu editor de código (como VS Code), ve a la línea 1 (después de los otros imports como `from flask import Flask`), y agrega la línea `import os` al inicio del archivo. Esto permite usar funciones del sistema operativo como crear carpetas.

### E2: Campo `codigo` Puede Ser Nulo
**Archivo**: `routes/admin.py:439` - Validar existencia y no aplicar `.upper()` sin verificación

**Para desarrolladores nuevos**: Abre el archivo `routes/admin.py` en tu editor de código, busca la línea aproximada 439 (puede variar), donde se maneja el campo `codigo`. Agrega una verificación `if codigo:` antes de aplicar `.upper()`, para evitar errores si el campo está vacío.

### E3: Configuración Insegura
**Archivo**: `config.py` - Requerir SECRET_KEY y DATABASE_URL como variables de entorno, activar SESSION_COOKIE_SECURE en producción

**Para desarrolladores nuevos**: Abre el archivo `config.py` en tu editor de código, ve a las líneas 10-15 donde se definen las configuraciones. Cambia las asignaciones directas por `os.environ.get('VARIABLE', 'default')` para SECRET_KEY y DATABASE_URL, y agrega `SESSION_COOKIE_SECURE = True` para producción. Esto hace la configuración más segura.

---

## Errores Importantes (🟡 Arreglar Pronto)

### E4: Contraseñas Por Defecto Débiles
**Archivo**: `init_db.py`

**Para desarrolladores nuevos**: Abre el archivo `init_db.py` en tu editor de código, busca donde se establece la contraseña del admin (alrededor de la línea donde dice `admin.set_password('admin123')`). Reemplaza esa línea con el código que usa `secrets.token_urlsafe(12)` para generar una contraseña segura aleatoria.

```python
# ❌ Actual
admin.set_password('admin123')

# ✅ Solución
import secrets
password = secrets.token_urlsafe(12)
admin.set_password(password)
print(f"Contraseña: {password}")
```

### E5: Usa print() en Lugar de Logging
**Archivos**: `migrate_db.py`, `init_db.py`, `test_app.py`

**Para desarrolladores nuevos**: Abre cada archivo mencionado (`migrate_db.py`, `init_db.py`, `test_app.py`) en tu editor de código. Busca las líneas con `print()` y reemplázalas con `logging.info()` o `logging.error()`. Agrega `import logging` y `logging.basicConfig(level=logging.INFO)` al inicio de cada archivo.

```python
# ❌ Actual
print("Migrando base de datos...")

# ✅ Solución
import logging
logging.basicConfig(level=logging.INFO)
logging.info("Migrando base de datos...")
logging.error("Error: %s", error)
```

### E6: Excepciones Genéricas
**Archivos**: `routes/admin.py`, `routes/tienda.py`

**Para desarrolladores nuevos**: Abre los archivos `routes/admin.py` y `routes/tienda.py` en tu editor de código. Busca bloques `try-except` que usen `except:` genérico. Cambia a excepciones específicas como `except ValueError:` o `except Exception as e:`. Agrega logging para errores inesperados.

```python
# ❌ Actual (captura TODO)
try:
    precio = Decimal(form.precio)
except:
    flash('Error desconocido', 'error')

# ✅ Solución (específicas)
try:
    precio = Decimal(form.precio)
except ValueError:
    flash('Precio debe ser número', 'error')
except Exception as e:
    logging.exception("Error inesperado")
    flash('Error interno', 'error')
```

### E7: Código Duplicado (WhatsApp)
**Archivo**: `routes/tienda.py` (se repite 6 veces)

**Para desarrolladores nuevos**: Abre el archivo `routes/tienda.py` en tu editor de código. Busca las 6 repeticiones del código de formateo de WhatsApp. Crea un nuevo archivo `utils.py` en la raíz del proyecto y mueve la función ahí. Luego importa y usa la función en `routes/tienda.py`.

```python
# ❌ Actual (repetido varias veces)
if whatsapp.startswith('0'):
    whatsapp = '593' + whatsapp[1:]
elif not whatsapp.startswith('+') and not whatsapp.startswith('593'):
    whatsapp = '593' + whatsapp

# ✅ Solución - crear utils.py
def format_whatsapp(num):
    if not num:
        return num
    if num.startswith('0'):
        return '593' + num[1:]
    elif not num.startswith('+') and not num.startswith('593'):
        return '593' + num
    return num

# En routes:
from utils import format_whatsapp
whatsapp = format_whatsapp(whatsapp)
```

### E39: Endpoint Expone Información de Sesión
**Archivo**: `routes/auth.py:101+` - Eliminar o proteger endpoint `/check-session`

**Para desarrolladores nuevos**: Abre el archivo `routes/auth.py` en tu editor de código, busca la ruta `/check-session` (alrededor de la línea 101 o más). Elimina toda la función o protégela con autenticación, ya que expone información sensible de la sesión del usuario.

---

## Errores Menores (🟢 Mejoras)

### E8: Sin Validación de Entrada
**Archivos**: Todos los formularios

**Para desarrolladores nuevos**: Abre los archivos de rutas que manejan formularios (como `routes/admin.py`, `routes/tienda.py`) en tu editor de código. Busca donde se obtiene data de `request.form.get()`. Instala `flask-wtf` si no está, crea clases de formulario con validadores, y usa `form.validate_on_submit()` en las rutas.

```python
# ❌ Actual
precio = request.form.get('precio')

# ✅ Solución - usar WTForms
from flask_wtf import FlaskForm
from wtforms import DecimalField, validators

class ProductForm(FlaskForm):
    precio = DecimalField('Precio', [
        validators.DataRequired(),
        validators.NumberRange(min=0)
    ])

# En ruta:
form = ProductForm()
if form.validate_on_submit():
    precio = form.precio.data  # Ya validado
```

### E9: Dependencias Inestables
**Archivo**: `requirements.txt`

**Para desarrolladores nuevos**: Abre el archivo `requirements.txt` en tu editor de código. Busca la línea `Flask==3.0.0` y cámbiala a `Flask==2.3.3`. Agrega `Flask-SQLAlchemy==3.0.5` si no está. Ejecuta `pip install -r requirements.txt` en la terminal para actualizar las dependencias.

```txt
# ✅ Cambiar de:
Flask==3.0.0

# A:
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
```

---

## Problemas Técnicos Principales

| Problema | Impacto | Solución |
|----------|--------|----------|
| **Arquitectura monolítica** | `routes/tienda.py` 700+ líneas | Dividir en módulos |
| **Sin tests unitarios** | Riesgo regresiones | Agregar pytest |
| **Sin capa servicios** | Código no reutilizable | Crear `services/` |
| **Sesiones inseguras** | Vulnerabilidades | Redis + SECRET_KEY |
| **Sin logging** | Sin historial | Implementar logging |

---

## Riesgos de Seguridad Adicionales

### ⚠️ Falta de Protección CSRF
- **Problema**: Formularios sin tokens CSRF
- **Solución**: `pip install flask-wtf` + agregar token en formularios
```html
<form method="POST">
    {{ csrf_token() }}
    <!-- campos -->
</form>
```

### ⚠️ Rate Limiting Faltante
- **Problema**: Login sin protección contra fuerza bruta
- **Solución**: `pip install flask-limiter`

**Para desarrolladores nuevos**: Abre el archivo `routes/auth.py` en tu editor de código. Busca las rutas de login (alrededor de las líneas 20-50). Instala `flask-limiter`, importa `Limiter`, crea una instancia, y agrega el decorador `@limiter.limit("5 per minute")` a las rutas POST de login.

```python
from flask_limiter import Limiter
limiter = Limiter(app)
@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    pass
```

### ⚠️ Inyecciones SQL Indirectas
- **Problema**: Uso de `text()` en `migrate_db.py`
- **Solución**: Evitar `text()` cuando sea posible

### ⚠️ Sesiones Inseguras
- **Problema**: Cookies almacenan sesiones sin cifrado server-side
- **Ubicación**: `routes/auth.py`, `routes/tienda.py`, `config.py`
- **Solución**: 
```python
SESSION_COOKIE_SECURE = True  # Solo HTTPS
SESSION_COOKIE_HTTPONLY = True  # Sin acceso JS
SESSION_COOKIE_SAMESITE = 'Strict'  # Previene CSRF
SESSION_PERMANENT = False  # Expira con navegador
```

### ⚠️ Credenciales en Documentación
- **Problema**: `README.md` muestra `admin/admin123` y `afiliado123`
- **Ubicación**: `README.md`, `bd.md`
- **Solución**: Reemplazar con ejemplos genéricos, never mostrar credenciales reales

### ⚠️ Falta de Sanitización de Entrada
- **Problema**: Campos de texto no se escapan adecuadamente
- **Ubicación**: `routes/admin.py`, `routes/tienda.py`
- **Riesgo**: XSS en comentarios, descripciones, nombres
- **Solución**:
```python
from markupsafe import escape
nombre_seguro = escape(nombre_entrada)
```

### ⚠️ Exposición de Errores en Producción
- **Problema**: `app.py` no define manejador de errores 500
- **Solución**:
```python
@app.errorhandler(500)
def error_500(error):
    logging.error(f"Error 500: {error}")
    return render_template('error.html', error_code=500), 500
```

### ⚠️ Falta de Validación de Archivos
- **Problema**: No hay validación de tipo/tamaño en uploads
- **Ubicación**: `routes/admin.py`, `routes/tienda.py`
- **Riesgo**: Upload de malware o archivos grandes
- **Solución**:
```python
ALLOWED_EXTENSIONS = {'jpg', 'png', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if file.size > MAX_FILE_SIZE:
    flash('Archivo muy grande', 'error')
```

---

## Vulnerabilidades de Bases de Datos

### 🔴 E10: Contraseñas Almacenadas Directamente
- **Problema**: `admin123` se almacena en texto en logs y documentación
- **Ubicación**: `init_db.py`, `test_app.py`, `README.md`
- **Solución**: Usar hashing seguro (ya usa `werkzeug.security`, pero no en init)

### 🟡 E11: Consultas N+1
- **Problema**: Para cada pedido, carga afiliado y productos por separado
- **Ubicación**: `models.py` líneas 234, 242
- **Impacto**: Lentitud con muchos datos
- **Solución**:
```python
from sqlalchemy.orm import joinedload
pedidos = Pedido.query.options(
    joinedload(Pedido.afiliado),
    joinedload(Pedido.productos)
).all()
```

### 🟡 E12: Sin Índices en Campos de Búsqueda
- **Problema**: Campos como `codigo`, `email`, `username` sin índices
- **Ubicación**: `models.py`
- **Solución**: Agregar `index=True` en campos de búsqueda frecuente

---

## Errores en `routes/afiliado.py` (No Analizados Previamente)

### 🔴 E34: Validación Insuficiente de WhatsApp en Perfil
- **Problema**: `mi_cuenta()` acepta WhatsApp sin validar formato
- **Ubicación**: `routes/afiliado.py:286`
- **Riesgo**: Números inválidos pueden causar errores al enviar mensajes
- **Solución**: Validar formato ecuatoriano antes de guardar

### 🟡 E35: Sin Validación de Nombre en Perfil
- **Problema**: Campo nombre puede ser vacío o excesivamente largo
- **Ubicación**: `routes/afiliado.py:282`
- **Riesgo**: Nombres inválidos en reportes y comunicaciones
- **Solución**: Validar longitud (2-100 caracteres) y caracteres permitidos

### 🟡 E36: Sin Validación de Contraseña Débil en Cambio
- **Problema**: Contraseña nueva no se valida por fortaleza
- **Ubicación**: `routes/afiliado.py:289`
- **Riesgo**: Usuario puede establecer contraseña débil
- **Solución**: Requerir mínimo 8 caracteres, mayúscula, número

### 🟡 E37: Consultas N+1 en Listados de Afiliado
- **Problema**: `pedidos()` y `comisiones()` usan queries ineficientes
- **Ubicación**: `routes/afiliado.py:119-164`
- **Riesgo**: Lentitud con muchos pedidos/comisiones
- **Solución**: Usar `joinedload()` para relaciones

### 🔴 E38: Sin Rate Limiting en Login
- **Problema**: Rutas `/auth/admin/login` y `/auth/afiliado/login` sin protección contra fuerza bruta
- **Ubicación**: `routes/auth.py:11-94`
- **Riesgo**: Ataques de diccionario y fuerza bruta
- **Solución**: Implementar `flask-limiter` con máximo 5 intentos por minuto

### 🟡 E39: Endpoint Expone Información de Sesión
- **Problema**: `/auth/check-session` devuelve datos sensibles sin validación
- **Ubicación**: `routes/auth.py:101+`
- **Riesgo**: Leak de información para atacantes
- **Solución**: Eliminar endpoint o proteger con autenticación + rate limiting

### 🟡 E40: Credenciales Expuestas en README.md y bd.md
- **Problema**: Documentos muestran credenciales por defecto (admin/admin123, afiliado123)
- **Ubicación**: `README.md` líneas 96-104, `bd.md` línea referencias
- **Riesgo**: Acceso no autorizado en producción
- **Solución**: Reemplazar con placeholders genéricos
email = db.Column(db.String(255), nullable=False, unique=True, index=True)
```

---

## Riesgos de Accesibilidad y UX

### 🟢 E13: Falta de Alt Text en Imágenes
- **Problema**: Imágenes en templates sin `alt`
- **Ubicación**: `templates/**/*.html`
- **Solución**:
```html
<img src="producto.png" alt="Foto de producto: Laptop HP">
```

### 🟢 E14: Contraste Insuficiente
- **Problema**: Texto gris sobre fondo claro (WCAG falla)
- **Ubicación**: `static/css/style.css`
- **Solución**: Revisar contraste con [WebAIM](https://webaim.org/resources/contrastchecker/)

### 🟢 E15: Sin Soporte para Navegación por Teclado
- **Problema**: Usuarios no pueden navegar con Tab/Enter
- **Ubicación**: `templates/base.html`
- **Solución**: Agregar `tabindex` y `focus` states

---

## Riesgos de Performance

### 🟡 E16: Sin Caché de Templates
- **Problema**: Templates se compilan en cada request
- **Ubicación**: `app.py`
- **Solución**:
```python
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 año para static
app.jinja_env.cache = {}
```

### 🟡 E17: Paginación Faltante
- **Problema**: Carga todos los resultados sin limite (si hay 10k productos)
- **Ubicación**: `routes/admin.py`, `routes/tienda.py`
- **Solución**:
```python
from flask_sqlalchemy import Pagination
page = request.args.get('page', 1, type=int)
productos = Producto.query.paginate(page=page, per_page=20)
```

### 🟡 E18: Sin Compresión Gzip
- **Problema**: Respuestas HTTP sin comprimir
- **Ubicación**: `app.py`
- **Solución**: `pip install flask-compress` y activar

---

## Problemas de Testing y QA

### 🟡 E19: Sin Tests de Integración
- **Problema**: Rutas no se prueban automáticamente
- **Archivo**: `test_app.py` básico
- **Solución**:
```python
import pytest

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_login_admin(client):
    resp = client.post('/admin_login', data={'username': 'admin', 'password': 'admin123'})
    assert resp.status_code == 302  # Redirect to dashboard
```

### 🟡 E20: Sin Tests de Modelos
- **Problema**: Lógica de cálculo de comisiones no probada
- **Ubicación**: `models.py`
- **Solución**: Tests para `get_total_comisiones()`, `get_ganancias()`, etc.

---

## Problemas de Escalabilidad

### 🟡 E21: Sin Async Tasks
- **Problema**: Emails de confirmación/notificación bloquean requests
- **Ubicación**: `routes/tienda.py`, `routes/afiliado.py`
- **Solución**: Usar Celery + Redis para tasks asíncronas

### 🟡 E22: Sin Caché de Base de Datos
- **Problema**: Cada request va directamente a BD
- **Ubicación**: Todas las rutas
- **Solución**: Redis para cachear sesiones y datos frecuentes

### 🟡 E23: Sin API Versioning
- **Problema**: Si se cambian rutas, se rompen integraciones externas
- **Ubicación**: `routes/*.py`
- **Solución**: URLs como `/api/v1/productos`, `/api/v2/productos`

---

## Nuevos Errores Identificados en Revisión Completa

### 🔴 E24: Falta de Protección CSRF en Formularios
- **Problema**: Formularios sin tokens CSRF permiten ataques cross-site request forgery
- **Ubicación**: `templates/tienda/index.html` (formulario checkout)
- **Riesgo**: Ataques CSRF pueden crear pedidos falsos
- **Solución**:
```html
<!-- ANTES (vulnerable) -->
<form id="form-checkout" onsubmit="procesarPedido(event)">

<!-- DESPUÉS (seguro) -->
<form id="form-checkout" onsubmit="procesarPedido(event)">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
```

### 🔴 E25: Vulnerabilidades XSS en Templates
- **Problema**: Datos no sanitizados en JavaScript inline permiten inyección de scripts
- **Ubicación**: `templates/tienda/index.html` (productos JSON)
- **Riesgo**: Ataques XSS pueden robar sesiones o datos
- **Solución**:
```javascript
// ANTES (vulnerable)
let productos = {{ productos | tojson }};

// DESPUÉS (seguro)
let productos = {{ productos | tojson | safe }};
// Además, sanitizar en backend antes de pasar datos
```

### 🟡 E26: Exposición de Credenciales en Documentación
- **Problema**: Credenciales por defecto visibles en README y tests
- **Ubicación**: `README.md`, `test_app.py`
- **Riesgo**: Ataques de diccionario facilitados
- **Solución**:
```markdown
<!-- ANTES en README.md -->
Admin:
- Usuario: `admin`
- Contraseña: `admin123`

<!-- DESPUÉS -->
Admin:
- Usuario: `admin`
- Contraseña: `[CAMBIAR_EN_PRODUCCION]`
```
```python
# ANTES en test_app.py
print("3. Login admin: admin / admin123")

# DESPUÉS
print("3. Login admin: admin / [VER_CONFIG]")
```

### 🟢 E27: Problemas de Contraste en CSS
- **Problema**: Colores no cumplen estándares WCAG de accesibilidad
- **Ubicación**: `static/css/style.css` (gradientes y textos)
- **Riesgo**: Usuarios con baja visión no pueden leer
- **Solución**:
```css
/* ANTES (contraste bajo) */
--primary-color: #6366f1;

/* DESPUÉS (mejor contraste) */
--primary-color: #4f46e5; /* Más oscuro */
--text-on-primary: #ffffff;

/* Agregar media query para alto contraste */
@media (prefers-contrast: high) {
  .navbar { background: #000000; color: #ffffff; }
}
```

### 🟢 E28: Falta de Soporte para Lectores de Pantalla
- **Problema**: Elementos sin atributos ARIA ni labels descriptivos
- **Ubicación**: `templates/tienda/index.html` (botones, modales)
- **Riesgo**: Usuarios con discapacidades no pueden navegar
- **Solución**:
```html
<!-- ANTES -->
<button onclick="agregarAlCarrito()">Agregar</button>

<!-- DESPUÉS -->
<button onclick="agregarAlCarrito()" 
        aria-label="Agregar producto al carrito"
        aria-describedby="producto-nombre">
    <span class="sr-only">Agregar al carrito</span>
    Agregar
</button>
```

### 🟡 E29: Validación Insuficiente en Formularios Frontend
- **Problema**: Solo validación HTML5 básica, falta validación de formato ecuatoriano
- **Ubicación**: `templates/tienda/index.html` (formulario checkout)
- **Riesgo**: Datos inválidos enviados al servidor
- **Solución**:
```javascript
// ANTES (solo HTML5)
<input type="tel" id="cliente-telefono" required>

// DESPUÉS (validación personalizada)
function validarTelefono(telefono) {
  const regex = /^\+593\d{9}$/;
  if (!regex.test(telefono)) {
    mostrarError('Formato: +593987654321');
    return false;
  }
  return true;
}
```

### 🟡 E30: Manejo Inseguro de SQL en Migraciones
- **Problema**: Uso de `text()` sin parámetros puede ser vulnerable si se expande
- **Ubicación**: `migrate_db.py`
- **Riesgo**: Inyección SQL potencial en futuras modificaciones
- **Solución**:
```python
# ANTES
db.session.execute(text("ALTER TABLE afiliados ADD COLUMN whatsapp VARCHAR(20)"))

# DESPUÉS
db.session.execute(
    text("ALTER TABLE afiliados ADD COLUMN whatsapp VARCHAR(:length)"),
    {"length": 20}
)
```

### 🟡 E31: Carrito Vulnerable en localStorage
- **Problema**: Datos sensibles en localStorage sin validación ni encriptación
- **Ubicación**: `templates/tienda/index.html` (carrito persistence)
- **Riesgo**: Manipulación de precios/cantidades por usuario malicioso
- **Solución**:
```javascript
// ANTES
localStorage.setItem('carrito', JSON.stringify(carrito));

// DESPUÉS
function guardarCarrito() {
  const carritoValidado = carrito.map(item => ({
    id: parseInt(item.id),
    nombre: String(item.nombre).substring(0, 100),
    precio: Math.max(0, parseFloat(item.precio)),
    cantidad: Math.max(1, parseInt(item.cantidad))
  }));
  localStorage.setItem('carrito', JSON.stringify(carritoValidado));
}
```

### 🟡 E32: Falta de Manejo de Errores en JavaScript
- **Problema**: Funciones críticas sin try-catch pueden fallar silenciosamente
- **Ubicación**: `templates/tienda/index.html` (procesarPedido, etc.)
- **Riesgo**: Errores no manejados confunden al usuario
- **Solución**:
```javascript
// ANTES
async function procesarPedido(event) {
  const response = await fetch('/api/crear-pedido', { ... });
  const resultado = await response.json();
  // ...
}

// DESPUÉS
async function procesarPedido(event) {
  try {
    const response = await fetch('/api/crear-pedido', { ... });
    if (!response.ok) throw new Error('Error HTTP: ' + response.status);
    const resultado = await response.json();
    // ...
  } catch (error) {
    console.error('Error procesando pedido:', error);
    mostrarNotificacion('Error al procesar pedido: ' + error.message, 'error');
  }
}
```

### 🟢 E33: Problemas de Rendimiento en CSS
- **Problema**: Uso excesivo de sombras y gradientes afecta performance móvil
- **Ubicación**: `static/css/style.css`
- **Riesgo**: Lentitud en dispositivos móviles
- **Solución**:
```css
/* ANTES (pesado) */
.btn {
  box-shadow: var(--shadow);
  background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
}

/* DESPUÉS (optimizado) */
.btn {
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  background: var(--primary-color);
  transition: box-shadow 0.2s ease;
}

.btn:hover {
  box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}
```

---

## Plan de Implementación

### Fase 1 (Semana 1): Errores Críticos
1. Agregar `import os` en `app.py` (E1)
2. Validar campo `codigo` (E2)
3. Configurar variables de entorno en `config.py` (E3)

### Fase 2 (Semana 2): Seguridad Inmediata
1. Cambiar contraseñas por defecto en `init_db.py` (E4)
2. Implementar logging en `migrate_db.py`, `init_db.py` (E5)
3. Capturar excepciones específicas (E6)
4. Limpiar credenciales de `README.md` y `bd.md` (Cred)

### Fase 3 (Semana 3): Seguridad Web
1. Agregar CSRF con `Flask-WTF` (CSRF, E24)
2. Mejorar configuración de sesiones (Sessions)
3. Agregar rate limiting en login (RateLimit)
4. Sanitizar entrada con `escape` (Sanitization, E25)
5. Limpiar credenciales expuestas (E26)

### Fase 4 (Semana 4): Validación y Código Limpio
1. Crear `utils.py` con `format_whatsapp()` (E7)
2. Implementar WTForms para validación (E8, E29)
3. Actualizar `requirements.txt` con versiones estables (E9)
4. Agregar validación de archivos en uploads (E24)
5. Mejorar validación frontend (E29)
6. Sanitizar datos en templates (E25)

### Fase 5 (Semana 5): Base de Datos y Performance
1. Agregar índices en `models.py` (E12)
2. Optimizar queries con `joinedload` (E11)
3. Implementar paginación en listados (E17)
4. Agregar caché de templates (E16)
5. Optimizar CSS para rendimiento móvil (E33)
6. Mejorar manejo SQL en migraciones (E30)

### Fase 6 (Semana 6): Testing y Accesibilidad
1. Crear tests unitarios con `pytest` (E19, E20)
2. Tests de rutas críticas (login, creación de pedidos)
3. Tests de modelos (cálculos de comisiones)
4. Coverage > 70%
5. Agregar atributos ARIA y labels (E28)
6. Corregir contraste de colores (E27)
7. Implementar navegación por teclado

### Fase 7 (Semana 7): Manejo de Errores y Logs
1. Agregar handler personalizado para errors 500 (E25)
2. Configurar logging centralizado
3. Monitoreo en producción (Sentry)
4. Mejorar manejo de errores JavaScript (E32)
5. Validar y sanitizar datos localStorage (E31)

### Fase 7 (Semana 7): Manejo de Errores y Logs
1. Agregar handler personalizado para errors 500 (E25)
2. Configurar logging centralizado
3. Monitoreo en producción (Sentry)

### Fase 8 (Semana 8+): Escalabilidad
1. Configurar Celery + Redis para tasks asíncronas (E21)
2. Implementar Redis para caché y sesiones (E22)
3. API versioning `/api/v1/` (E23)
4. Containerización con Docker

---

## ✅ Cobertura Completa de Auditoria

### Archivos Críticos Auditados (Afectan Funcionamiento)
- ✅ `app.py` - Inicialización Flask
- ✅ `config.py` - Configuración seguridad
- ✅ `models.py` - Modelos y ORM
- ✅ `routes/auth.py` - Autenticación
- ✅ `routes/admin.py` - Panel administrador
- ✅ `routes/afiliado.py` - Panel afiliado
- ✅ `routes/tienda.py` - Tienda pública
- ✅ `init_db.py` - Inicialización BD
- ✅ `migrate_db.py` - Migraciones BD
- ✅ `test_app.py` - Tests
- ✅ `templates/` - Plantillas HTML
- ✅ `static/css/style.css` - Estilos CSS

### Archivos No Críticos (No Afectan Funcionamiento)
- ⚪ `run.bat` - Script de arranque auxiliar
- ⚪ `runtime.txt` - Especifica Python 3.12.3
- ⚪ `requirements.txt` - ✅ Analizado
- ⚪ `README.md` - ✅ Analizado (credenciales)
- ⚪ `bd.md` - Documentación técnica

### Total de Errores/Riesgos Identificados: 40
- **🔴 Críticos (4)**: E1, E2, E3, E38
- **🟡 Importantes (16)**: E4-E37, E39, E40
- **🟢 Mejoras (20)**: E8, E9, E13-E37 (excluidos críticos e importantes)

---

