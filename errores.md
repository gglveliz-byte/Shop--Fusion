# Registro de Errores - Shop Fusion (Resumido)

## Referencia Rápida

| Prioridad | Error | Ubicación | Acción |
|-----------|-------|-----------|--------|
| 🔴 | Import `os` faltante | `app.py:27` | Agregar `import os` |
| 🔴 | `codigo` puede ser nulo | `routes/admin.py:439` | Validar existencia |
| 🔴 | Config insegura | `config.py` | Requerir vars entorno |
| 🟡 | print() en producción | `migrate_db.py`, `init_db.py` | Usar logging |
| 🟡 | Excepciones genéricas | `routes/admin.py`, `tienda.py` | Capturar específicas |
| 🟡 | Contraseñas débiles | `init_db.py` | Generar aleatorias |
| 🟢 | Código duplicado WhatsApp | `routes/tienda.py` | Crear función |
| 🟢 | Sin validación entrada | Todos forms | Usar WTForms |

---

## Errores Críticos (🔴 Arreglar Ahora)

### E1: Import `os` Faltante
**Archivo**: `app.py:27` - Agregar `import os` para crear carpetas

### E2: Campo `codigo` Puede Ser Nulo
**Archivo**: `routes/admin.py:439` - Validar existencia y no aplicar `.upper()` sin verificación

### E3: Configuración Insegura
**Archivo**: `config.py` - Requerir SECRET_KEY y DATABASE_URL como variables de entorno, activar SESSION_COOKIE_SECURE en producción

---

## Errores Importantes (🟡 Arreglar Pronto)

### E4: Contraseñas Por Defecto Débiles
**Archivo**: `init_db.py`
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

---

## Errores Menores (🟢 Mejoras)

### E8: Sin Validación de Entrada
**Archivos**: Todos los formularios
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
- **Solución**:
```python
codigo = db.Column(db.String(20), nullable=False, unique=True, index=True)
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

## Estructura Recomendada (Post-Rediseño)

```
Shop--Fusion/
├── app/
│   ├── api/          # Endpoints REST nuevos
│   ├── models/       # Modelos BD
│   ├── services/     # Lógica negocio
│   ├── utils/        # Helpers
│   ├── web/          # Rutas web
│   └── templates/    # HTML
├── tests/            # Tests
├── config/           # Configuración por entorno
├── migrations/       # Migraciones BD
└── scripts/          # Deploy
```

---

