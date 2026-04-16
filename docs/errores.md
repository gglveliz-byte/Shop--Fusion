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

## Errores Arquitectónicos y de Negocio (¡Nuevos Hallazgos Críticos!)

### 🔴 E41: Ausencia de Control de Inventario (Stock)
- **Problema**: `Producto` permite ventas ilimitadas (solo tiene boolean `activo`).
- **Ubicación**: `models.py` (Línea 121), `routes/tienda.py`
- **Riesgo**: Sobreventa de productos físicos, reembolsos forzados y problemas legales.
- **Para desarrolladores nuevos**: Abre `models.py`. Agrega `stock = db.Column(db.Integer, default=0)` en el modelo `Producto`. Luego, en `routes/tienda.py`, antes de procesar el pago o checkout, debes asegurarte de que `producto.stock >= cantidad_solicitada` y restarlo al confirmar.

### 🔴 E42: Almacenamiento Volátil de Imágenes
- **Problema**: Las imágenes se suben a `/static/uploads/`, lo cual es efímero en hosts como Render/Heroku.
- **Ubicación**: `config.py` (Línea 28), `routes/admin.py`
- **Riesgo**: Al reiniciar el servidor (cada deploy), todos los productos perderán sus imágenes locales.
- **Para desarrolladores nuevos**: Necesitan integrar Cloud Storage. Crea funciones para conectarte con Amazon S3 o Cloudinary usando `boto3` o sus respectivos SDKs. Actualiza en `models.py` para leer siempre URLs absolutas.

### 🟡 E43: Confirmaciones PayPal sin Webhooks
- **Problema**: El checkout confía en `/api/paypal/capture-order` invocado por el frontend sincrónicamente.
- **Ubicación**: `routes/tienda.py` (Línea 560+)
- **Riesgo**: Si el usuario cierra el navegador o pierde internet entre el pago en PayPal y la llamada API, el pedido no se registrará en tu BD, pero su dinero será cobrado.
- **Para desarrolladores nuevos**: Explora la documentación de PayPal Webhooks. Crea una nueva ruta `@bp.route('/api/paypal/webhook', methods=['POST'])` para que PayPal le confirme directamente a tu servidor (backend) cuando haya capturado un pago correctamente.

### 🟡 E44: Estados Logísticos Básicos Faltantes
- **Problema**: El e-commerce solo controla `pendiente`, `pagado` y `cancelado`. Faltan estados físicos de entrega.
- **Ubicación**: `models.py` (Líneas 182)
- **Riesgo**: Imposible llevar control o informar al cliente sobre la fase de preparación o envío.
- **Para desarrolladores nuevos**: Agrega en `Pedido` estados nuevos como `preparando`, `enviado`, `entregado`. Suma un campo `tracking_url = db.Column(db.String(255), nullable=True)` para ingresar las guías logísticas del proveedor de entregas.

---

## Plan de Implementación (Reestructurado)

### Fase 1 (Semana 1): Errores Críticos y Seguridad Urgente
1. Agregar protección CSRF con `Flask-WTF` (E24) - **¡Elevado por gravedad!**
2. Validar campo `codigo` (E2)
3. Implementar control de `stock` para evitar sobreventa (E41)
4. Modificar config de sesiones Web (*SESSION_COOKIE_SECURE*) (Sessions/E16)
5. Configurar variables de entorno y limpiar Secrets en `config.py` (E3)

### Fase 2 (Semana 2): Seguridad y Manejo de Pagos
1. Integrar PayPal Webhooks para validación asíncrona de pagos (E43)
2. Proteger logins con rate limiting `flask-limiter` (E38)
3. Cambiar contraseñas débiles por defecto en `init_db.py` (E4)
4. Limpiar credenciales de `README.md` (E40, Cred)

### Fase 3 (Semana 3): Infraestructura y Archivos
1. Migrar sistema de uploads locales (`/static/uploads`) a AWS S3 o Cloudinary (E42)
2. Agregar validación de archivos (formatos y tamaños) en uploads (E24)
3. Centralizar formateo de números en un nuevo `utils.py` (E7)
4. Implementar logging global en todo el proyecto (E5)

### Fase 4 (Semana 4): Negocio y Logística
1. Expandir BD de Pedidos para Tracking (`preparando`, `enviado`, `tracking_url`) (E44)
2. Implementar WTForms para validación rígida (E8, E29)
3. Sanitizar entradas con `escape` en JSON y Base de Datos (E25)
4. Ajustar consultas SQL crudas en `migrate_db.py` (E30)

### Fase 5 (Semana 5): Base de Datos y Performance
1. Agregar índices (`index=True`) en `models.py` (E12)
2. Optimizar queries tipo N+1 usando `joinedload` (E11)
3. Implementar paginación en listados administrativos (E17)
4. Mejorar rendimiento en CSS eliminando variables pesadas (E33)

### Fase 6 (Semana 6): Testing, QA y Accesibilidad
1. Crear tests unitarios con `pytest` (cobertura +70%) (E19, E20)
2. Pruebas focales en checkout y cálculo de comisiones.
3. Mejorar interfaz visual de Accesibilidad (etiquetas ARIA, colores) (E27, E28)
4. Validar y purgar manipulación de localStorage en el frontend (E31)

### Fase 7 (Semana 7): Monitoreo de Producción y Asincronía
1. Centralizar captura de Errores JS en Frontend y 500 en Backend (E32, E25).
2. Configurar alertas Sentry.
3. Incorporar Celery + Redis para emails y tasks asíncronas (E21).

### Fase 8 (Meta SaaS 🚀): Migración Arquitectura Multi-tenant
1. Separar configs de PayPal/WhatsApp hacia un nuevo modelo de BD `Tenant` o `AdminStore`.
2. Habilitar dominios personalizados en enrutador mapeando a `TenantID`.
3. Containerización general con Docker.

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

### Total de Errores/Riesgos Identificados: 44
- **🔴 Críticos (6)**: E1, E2, E3, E38, E41, E42
- **🟡 Importantes (18)**: E4-E37, E39, E40, E43, E44
- **🟢 Mejoras (20)**: E8, E9, E13-E37 (excluidos críticos e importantes)
---

## 🧪 Notas Finales: Ideas Experimentales y Opciones de Rollback

A continuación, se documentan los riesgos vinculados a una **rama de desarrollo experimental** que intentó refactorizar el flujo de login del Administrador central en `app.py`, `routes/auth.py` y `config.py` (sincronizando credenciales permanentemente contra las variables de entorno).

Estos cambios **no son permanentes** y se exponen aquí como "Opciones", detallando por qué este modelo de autenticación trae riesgos si se decide implementar a futuro (a modo de bitácora para el equipo):

### Opción/Idea 1: Login Vía Variables de Entorno (Riesgo de Bypass)
- **El concepto evaluado:** Forzar al Administrador a loguearse comparando su formulario con un `current_app.config['ADMIN_USER']`.
- **Problema de la implementación:** Si en un despliegue alguien olvida configurar el `.env`, la variable local será `None`. Si un atacante altera un request de login mandando campos vacíos (`username=None`), el login valida `None == None` y lo deja entrar gratis como Administrador Máximo.
- **Si se retoma a futuro:** Asegurarse de usar una capa protectora previa: `if not username or not current_app.config['ADMIN_USER']:` lanzar error, o usar `hmac.compare_digest`.

### Opción/Idea 2: Sincronización Forzada de Hash (Antipatrón de DB)
- **El concepto evaluado:** Por garantizar consistencia, se usaba `admin.set_password(password)` y `db.session.commit()` *cada vez* que el usuario entraba.
- **Problema de la implementación:** Bcrypt/Werkzeug consume mucha memoria y CPU al hashear. Escribir a la base de datos en cada intento de login roba conexiones y resiente severamente el servidor si entraran muchos administradores a la vez.
- **Si se retoma a futuro:** Condicionar la carga a la base de datos. Solo llamar a la función `set_password` si la contraseña vieja ya no cincuerda con la nueva.

### Opción/Idea 3: WhatsApp Hardcodeado
- **El concepto evaluado:** Poner directamente `WHATSAPP_NUMBER = '+51906540885'` en el archivo config de Python.
- **Problema de la implementación:** Rompe las normas de flexibilidad. Expondrá teléfonos personales si liberan el código y forzará a todos los ambientes locales a apuntar al WhatsApp del dueño principal.
- **Si se retoma a futuro:** Envolver todo número fijo de este modo: `os.environ.get('WHATSAPP_NUMBER', '+51906540885')`.
