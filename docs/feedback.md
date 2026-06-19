# AUDITORÍA BACKEND — SHOP FUSION
> Auditor archivo por archivo | Código real verificado línea a línea

---

## 📁 `routes/auth.py` (238 líneas)

### ✅ Aciertos
- Rate limiting en login (5/min) ✅
- Bloqueo por intentos fallidos en sesión ✅
- Logging de eventos de seguridad ✅
- Redirección post-login segura (evita open redirect) ✅

### 🔴 Crítico
**L62-65: Comparación de contraseña en texto plano**
```python
is_correct_admin = (
    username == admin_user_config and 
    password == admin_pass_config
)
```
La contraseña del `.env` se compara literalmente. Aunque luego se hashea con `set_password()`, la validación inicial es plaintext. Un atacante con acceso al archivo de configuración obtiene la contraseña del admin.

**Solución:** Usar `check_password_hash()` comparando contra lo almacenado en DB, o al menos almacenar un hash de la contraseña env en vez del valor plano.

### 🟠 Grave
**L16: Rate limit por IP en sesión — frágil**
```python
@limiter.limit("5 per minute", error_message='Demasiados intentos...')
```
Rate limit por IP usando `memory://` storage. Si la app se reinicia, se pierden todos los contadores. Ademas, con `X-Forwarded-For` spoofing un atacante puede evadirlo.

**L102-108: Bloqueo por sesión — evasible**
```python
attempts = session.get('admin_login_attempts', 0) + 1
```
El contador de intentos está en `session`. Si el atacante usa un nuevo session ID cada vez (borrando cookies), nunca se bloquea.

**Solución:** Mover contador de intentos a Redis/Memcached o DB con clave por IP.

### 🟡 Medio
**L185-200: Logout no usa POST**
```python
@bp.route('/logout')
def logout():
```
CSRF posible en logout. Debería ser `methods=['POST']` para evitar que un atacante engañe al admin con un link.

---

## 📁 `routes/admin.py` (701 líneas)

### ✅ Aciertos
- Decorador `@admin_required` bien implementado ✅
- Paginación en lista de productos (E17) ✅
- `joinedload` en varias consultas (E11) ✅
- `secure_filename` en uploads ✅

### 🔴 Crítico
**L486-508: N+1 masivo en lista de afiliados → **NO ESCALABLE****
```python
for afiliado in afiliados:
    total_ganado = db.session.query(...).filter(afiliado.id)...   # N
    total_generado = db.session.query(...).filter(afiliado.id)... # N
    num_ventas = Pedido.query.filter(afiliado.id)...              # N
```
Con 500 afiliados → **1,502 consultas SQL**. Esto mata el rendimiento.

**Solución:**
```python
# Subquery agregada única
totales = db.session.query(
    Comision.afiliado_id,
    func.sum(Comision.monto).filter(Comision.estado == 'pagada').label('pagado'),
    func.sum(Comision.monto).filter(Comision.estado == 'generada').label('generado'),
).group_by(Comision.afiliado_id).all()
```

### 🟠 Grave
**L96-143: Dashboard con 6 consultas independientes**
```python
total_productos = Producto.query.filter_by(activo=True).count()
total_pedidos = Pedido.query.filter(...).count()
pedidos_pendientes = Pedido.query.filter(...).count()
# ... 3 más
```
Cada COUNT es un roundtrip a PostgreSQL. Con latencia de red (~5-20ms) son ~60-120ms perdidos.

**Solución:** Una sola consulta con `db.session.query(db.func.count(), ...)`.

### 🟡 Medio
**L41-83: Configuración guarda archivos sin validar contenido**
```python
file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
```
Solo valida extensión, no el tipo MIME real. Podrían subir SVG con XSS o scripts renombrados.

**Solución:** Usar `python-magic` para verificar `mime_type` real del archivo.

**L265: Sin rollback en error**
```python
db.session.commit()
```
Si `commit()` falla, no hay `rollback()` antes. La sesión queda corrupta.

### Arquitectura
**701 líneas para 5 dominios mezclados:**
- Config (L37-89)
- Dashboard (L92-143)
- Productos CRUD (L148-374)
- Pedidos (L377-471)
- Afiliados (L474-614)
- Comisiones (L618-701)

**Recomendación:** Separar en:
- `routes/admin_productos.py`
- `routes/admin_pedidos.py`
- `routes/admin_afiliados.py`
- `routes/admin_comisiones.py`
- `routes/admin_config.py`

---

## 📁 `routes/afiliado.py` (319 líneas)

### ✅ Aciertos
- Decorador `@afiliado_required` bien ✅
- Validación de WhatsApp y contraseña fuerte ✅
- Verificación de pertenencia de pedidos (L192) ✅

### 🟠 Grave
**L79: Sin paginación en productos**
```python
productos = Producto.query.filter_by(activo=True).order_by(...).all()
```
Con 2000 productos, se cargan todos en memoria para mostrarlos en una tabla. Admin.py sí tiene `paginate()` pero aquí no.

**L164-171: Estadísticas duplicadas en vista de pedidos**
```python
total_pedidos = Pedido.query.filter_by(afiliado_id=afiliado.id).count()          # 1
pedidos_pendientes = Pedido.query.filter_by(..., estado='pendiente').count()     # 2
pedidos_pagados = Pedido.query.filter_by(..., estado='pagado').count()           # 3
pedidos_validados = Pedido.query.filter_by(..., validado_por_vendedor=True).count() # 4
```
4 consultas cuando una sola basta:
```python
estados = db.session.query(Pedido.estado, func.count(Pedido.id)) \
    .filter(Pedido.afiliado_id == afiliado.id) \
    .group_by(Pedido.estado).all()
```

### 🟡 Medio
**L38-51: Dashboard con 6 consultas de comisiones + 4 de pedidos**
```python
total_pendiente = afiliado.total_comisiones_pendientes()  # query
total_generado = afiliado.total_comisiones_generadas()    # query
total_pagado = afiliado.total_comisiones_pagadas()        # query
total_ganado = afiliado.total_ganado()                    # llama 2 de arriba
ultimas_comisiones = Comision.query...limit(5)            # query
total_pedidos = Pedido.query...count()                    # query
# ... + 3 más
```
**10 consultas para una página de dashboard.** Con `group_by` + `subquery` se reduce a 3.

---

## 📁 `routes/tienda.py` (903 líneas) 🏆 **ARCHIVO MÁS PROBLEMÁTICO**

### ✅ Aciertos
- Recalculo de precios desde servidor (E42) ✅
- Validación de stock en checkout (E41) ✅
- `format_whatsapp` usado en index ✅

### 🔴 Críticos

**L858-901: PayPal Webhook sin verificación de firma**
```python
@bp.route('/paypal-webhook', methods=['POST'])
def paypal_webhook():
    data = request.get_json()
    # NO hay verificación de headers PayPal
    # NO hay validación de IP de origen
    # NO hay idempotency key
```
Cualquier atacante que descubra esta URL puede falsificar pagos. PayPal envía headers como `PAYPAL-AUTH-ALGO`, `PAYPAL-CERT-URL`, `PAYPAL-TRANSMISSION-SIG` que deben verificarse.

**L740-755: Endpoint público expone WhatsApp de afiliados**
```python
@bp.route('/api/get-vendedor-whatsapp')
def get_vendedor_whatsapp():
    vendedor = Afiliado.query.filter_by(codigo=codigo, activo=True).first()
    return jsonify({'whatsapp': whatsapp})
```
Sin autenticación, sin rate-limit. Un scraper puede recolectar todos los números de WhatsApp de todos los vendedores enumerando códigos.

### 🟠 Graves

**L303-306: Race condition en reducción de stock**
```python
for item in carrito:
    producto = Producto.query.get(item['id'])
    if producto:
        producto.reducir_stock(int(item['cantidad']))
```
Dos pedidos simultáneos pueden leer `stock=5`, ambos validar disponibilidad, y ambos reducir. Stock final: -2. Debe usar `with_for_update()`.

**L56-71 + L793-806: Serialización manual de productos duplicada**
El bloque `for p in productos_db` para convertir a dict aparece ~3 veces (index, tienda_vendedor). Código idéntico de ~20 líneas.

**L103-108 + L338-342 + L809-813 + L844-848: Formateo WhatsApp duplicado 4 veces**
```python
if whatsapp_numero.startswith('0'):
    whatsapp_numero = '593' + whatsapp_numero[1:]
```
Ya existe `format_whatsapp()` en `utils/validators.py` pero no se usa aquí.

**L315-317: Posible error si Configuracion no tiene registros**
```python
config_web = Configuracion.query.first()
nombre_tienda = config_web.nombre_tienda if config_web else "la tienda"
```
El fallback solo cubre nombre_tienda, pero la línea 319 usa `nombre_tienda` directamente.

### 🟡 Medio

**L382-466: API `/api/crear-pedido` filtra error interno**
```python
except Exception as e:
    db.session.rollback()
    return {'success': False, 'error': str(e)}, 500
```
Expone trazas de error internas al frontend. Podría revelar estructura de DB.

**L489-511: `get_paypal_access_token()` sin manejo de errores granular**
Solo verifica status 200. No maneja 401 (token expirado), 429 (rate limit), 5xx.

### Arquitectura
**903 líneas mezclando 7 responsabilidades:**
1. Home/Index (L20-83)
2. Carrito (L117-223)
3. Checkout (L226-371)
4. API pedidos (L374-466)
5. PayPal (L487-727)
6. API pública WhatsApp (L740-755)
7. Tiendas vendedor (L760-855)
8. Webhook PayPal (L858-903)

**Recomendación:**
- `routes/tienda.py` → solo home + categorías
- `routes/carrito.py` → carrito + checkout
- `routes/paypal.py` → PayPal + webhook
- `routes/api_vendedor.py` → endpoints públicos

---

## 📁 `routes/ai.py` (37 líneas)

### ✅ Aciertos
- Rate limiting en chat (5/min) ✅
- CSRF exempt correcto ✅

### 🟡 Medio
**L24: Modelo expuesto al cliente**
```python
modelo = data.get('model', 'qwen3.6-plus')
```
Un atacante puede cambiar el modelo a uno más costoso o no disponible. Validar contra lista permitida.

**L31: Sin timeout en llamada a API externa**
```python
respuesta, razonamiento = qwen_service.get_response(mensaje, model=modelo)
```
Si Qwen se cuelga, el endpoint queda bloqueado indefinidamente. Agregar timeout de 30s.

---

## 📁 `utils/validators.py` (45 líneas)

### ✅ Aciertos
- Validación de WhatsApp con mínimo 9 dígitos ✅
- Password fuerte con mayúscula, número, especial ✅

### 🟡 Medio
**L16-21: `format_whatsapp` hardcodea código de país 593 (Ecuador)**
```python
return '593' + num
```
No funciona para otros países. Debería ser configurable.

**L43: Set de caracteres especiales incompleto**
```python
if not any(c in "!@#$%^&*()-_+=[]{}|;:,.<>?/" for c in password):
```
Faltan caracteres como `~`, ``` ` ```, `'`, `"`. Mejor usar `string.punctuation`.

---

## 📁 `utils/rate_limit.py` (12 líneas)

### ✅ Aciertos
- Límites globales (200/día, 50/hora) ✅

### 🟠 Grave
**L10: `fixed-window` permite ráfagas**
```python
strategy="fixed-window"
```
Un atacante puede hacer 200 requests justo antes del reset + 200 justo después = 400 en minutos.

**Solución:** Cambiar a `"moving-window"`.

**L9: `memory://` no persiste entre reinicios**
```python
storage_uri="memory://"
```
En producción con múltiples workers/gunicorn, cada worker tiene su propio estado en memoria. El rate limit es inefectivo.

**Solución:** Usar `redis://` como storage.

---

## 📁 `utils/security_logger.py` (52 líneas)

### ✅ Aciertos
- Rotación de logs (5MB × 5 archivos) ✅
- Formato forense con IP, timestamp, evento ✅
- Detección de X-Forwarded-For ✅

### 🟡 Medio
**L38: IP spoofeable si no hay proxy confiable**
```python
remote_addr = request.headers.get('X-Forwarded-For', request.remote_addr)
```
Si la app está directamente expuesta (sin proxy), el atacante puede fake el header. No hay validación de proxy confiable.

**L52: `current_app.logger.info()` en import-time**
```python
current_app.logger.info(f"SECURITY EVENT: {log_msg}")
```
Si se llama fuera del contexto de aplicación (ej: en test), lanza `RuntimeError: Working outside of application context`.

---

## 📁 `utils/ai_qwen.py` (86 líneas)

### ✅ Aciertos
- API key no hardcodeada ✅
- Soporte para streaming y thinking ✅

### 🟠 Grave
**L17: API key se carga pero no se valida**
```python
api_key = os.environ.get('DASHSCOPE_API_KEY')
```
Si la key es inválida, el error se propaga hasta el usuario con `str(e)`.

### 🟡 Medio
**L53: Sin timeout en requests HTTP**
```python
response_stream = self.client.chat.completions.create(
    model=model, messages=messages, stream=True
)
```
Sin `timeout` o `max_retries`. Si la API de Qwen está caída, el hilo se bloquea.

**L47-49: `enable_thinking` hardcodeado para qwen3-32b**
```python
if model == "qwen3-32b":
    extra_params["extra_body"] = {"enable_thinking": True}
```
Si Qwen agrega thinking a otros modelos, este código no escala. Debería ser configurable.

---

## 📁 `config.py` (70 líneas)

### ✅ Aciertos
- Validación de SECRET_KEY obligatoria ✅
- Cookies con HttpOnly, SameSite Strict ✅
- Debug controlado por env ✅

### 🟠 Grave
**L21: SECRET_KEY no tiene validación de fortaleza**
```python
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise EnvironmentError(...)
```
Solo valida que exista, no que sea fuerte. Con `solo_coloco_texto_aqui_` del `.env`, cualquier atacante puede forjar sesiones.

**L37: Sin pool de conexiones**
```python
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
```
Cada request abre una conexión nueva si no hay pool. Bajo carga, PostgreSQL se satura.

### 🟡 Medio
**L11-17: `get_required_env` definida pero NUNCA USADA**
```python
@staticmethod
def get_required_env(name):
```
Nunca se invoca. `PAYPAL_CLIENT_ID`, `PAYPAL_SECRET`, `FERNET_KEY` no tienen validación de existencia en producción.

**L49: `WHATSAPP_NUMBER` vacío por defecto**
```python
WHATSAPP_NUMBER = ''
```
Si alguien despliega sin configurarlo, la app corre pero el botón de WhatsApp no funciona (sin error visible).

---

## 📁 `app.py` (200 líneas)

### ✅ Aciertos
- Factoría `create_app` ✅
- Talisman con CSP ✅
- Error handlers para 400, 403, 404, 500 ✅
- CORS limitado a `/ai/*` ✅

### 🟠 Grave
**L184-185: `db.create_all()` en cada arranque**
```python
with app.app_context():
    db.create_all()
```
`create_all()` es **CREATE IF NOT EXISTS**. No migra esquemas. Si agregas una columna nueva en models.py, no se crea automáticamente en DB existente (por eso existe `migrate_db.py` como parche).

**Solución:** Usar Flask-Migrate (Alembic).

### 🟡 Medio
**L42: CORS permisivo para AI**
```python
CORS(app, resources={r"/ai/*": {"origins": "*"}})
```
El chatbot IA permite CORS desde cualquier origen. Si alguien embedding el chat en su sitio, puede consumir tu API key de Qwen.

**L141-142: CSRF exempt en paypal_webhook y ai.chat — correcto pero frágil**
Si alguien agrega otro endpoint que necesita CSRF exempt, debe acordarse de agregarlo aquí. Podría olvidarse.

---

## 📁 `models.py` (491 líneas)

### ✅ Aciertos
- Cifrado Fernet para PII (whatsapp, teléfono, dirección) ✅
- Sanitización HTML con bleach ✅
- Validación de datos con `@validates` ✅
- UserMixin bien implementado ✅
- `lazy='joined'` en relaciones (E11) ✅

### 🔴 Crítico
**L24-29: Fernet key auto-generada sin persistencia en desarrollo**
```python
_fernet_key = os.environ.get('FERNET_KEY')
if not _fernet_key:
    if os.environ.get('FLASK_ENV') == 'production':
        raise EnvironmentError(...)
    _fernet_key = Fernet.generate_key().decode()
```
**Cada reinicio genera una nueva key.** Todos los datos cifrados con la key anterior (WhatsApp de afiliados, teléfonos y direcciones de pedidos) se vuelven **ilegibles permanentemente**.

### 🟠 Grave
**L125-126: `lazy='joined'` en Afiliado.pedidos y Afiliado.comisiones**
```python
pedidos = db.relationship('Pedido', backref='afiliado', lazy='joined')
comisiones = db.relationship('Comision', backref='afiliado', lazy='joined')
```
`lazy='joined'` carga SIEMPRE pedidos y comisiones cada vez que se consulta un afiliado. Incluso si solo necesitas el nombre:
```python
afiliado = Afiliado.query.first()  # LEFT JOIN pedidos + LEFT JOIN comisiones
```
**Con 500 afiliados con promedios de 50 pedidos cada uno, una simple consulta trae 25,000 filas en memoria.**

**Solución:** Cambiar a `lazy='dynamic'` o `lazy='select'` y cargar explícitamente con `joinedload()` solo cuando se necesite.

**L217-223: `reducir_stock` no es atómico**
```python
def reducir_stock(self, cantidad):
    if self.stock >= cantidad:
        self.stock -= cantidad
        return True
    return False
```
Sin bloqueo pesimista. En concurrencia, dos llamadas pueden pasar la validación simultáneamente.

### 🟡 Medio
**L258-277: `obtener_todas_imagenes()` duplica URLs**
```python
if self.imagen_url:
    todas.append(self.imagen_url)
if self.imagenes_url:
    todas.extend(self.imagenes_url)
```
Si `imagen_url` también está en `imagenes_url`, aparece duplicada.

**L371-398: `_generar_comision()` consulta DB dentro de un loop**
```python
for item in self.productos_json:
    producto = Producto.query.get(item['id'])  # N consultas
```
Si el pedido tiene 10 productos, son 10 queries para calcular comisiones. Debería ser un solo `Producto.query.filter(Producto.id.in_(ids)).all()`.

---

## 📁 `init_db.py` (170 líneas)

### ✅ Aciertos
- No hardcodea credenciales (usa .env) ✅
- Logging profesional ✅
- Productos de ejemplo con datos realistas ✅

### 🔴 Crítico
**L31-32: `db.drop_all()` borra TODOS los datos**
```python
db.drop_all()
```
Si alguien ejecuta `init_db.py` en producción por accidente, pierde toda la base de datos. No hay confirmación.

**Solución:** Agregar `input("¿ESTÁS SEGURO? (escribe 'YES'): ")` y verificar antes de drop_all.

### 🟡 Medio
**L96-125: Productos de ejemplo hardcodeados**
Si la base de datos ya tiene productos, no se crean (L127: `if Producto.query.count() == 0`). Pero si el admin quiere resetear productos específicos, no hay manera.

---

## 📁 `migrate_db.py` (85 líneas)

### ✅ Aciertos
- Verifica existencia previa de columnas ✅
- Compatible PostgreSQL/MySQL ✅

### 🟡 Medio
**L40: Raw SQL con ALTER TABLE**
```python
db.session.execute(text("ALTER TABLE afiliados ADD COLUMN whatsapp VARCHAR(20)"))
```
Si la tabla `afiliados` no existe (DB vacía), esto falla. No hay verificación previa.

**L40: VARCHAR(20) insuficiente para WhatsApp internacional**
Números con código de país + número + extensiones pueden exceder 20 caracteres. El modelo `models.py` usa `String(500)`.

---

## 📊 RESUMEN POR ARCHIVO

| Archivo | Líneas | Críticos | Graves | Medios | Prioridad refactor |
|---|---|---|---|---|---|
| `routes/tienda.py` | 903 | 3 | 4 | 3 | 🔴 **URGENTE** |
| `routes/admin.py` | 701 | 1 | 2 | 4 | 🔴 **URGENTE** |
| `models.py` | 491 | 1 | 2 | 2 | 🟠 Alta |
| `config.py` | 70 | 0 | 2 | 2 | 🟠 Alta |
| `routes/auth.py` | 238 | 1 | 1 | 1 | 🟠 Alta |
| `routes/afiliado.py` | 319 | 0 | 2 | 2 | 🟡 Media |
| `utils/rate_limit.py` | 12 | 0 | 1 | 0 | 🟡 Media |
| `utils/ai_qwen.py` | 86 | 0 | 1 | 2 | 🟡 Media |
| `init_db.py` | 170 | 1 | 0 | 1 | 🟡 Media |
| `app.py` | 200 | 0 | 1 | 2 | 🟢 Baja |
| `utils/security_logger.py` | 52 | 0 | 0 | 2 | 🟢 Baja |
| `migrate_db.py` | 85 | 0 | 0 | 2 | 🟢 Baja |
| `utils/validators.py` | 45 | 0 | 0 | 2 | 🟢 Baja |
| `routes/ai.py` | 37 | 0 | 0 | 2 | 🟢 Baja |
