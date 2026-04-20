# 🟡 Severidad Media (FASE 3)
**Nivel de Prioridad:** Media / Operativa.
**Objetivo:** Proteger el proceso logístico y garantizar que el crecimiento masivo no corrompa el sistema de inventario o elimine imágenes debido a fallos de Cloud Providers.

---

## 1. Sistema Ciego de Sobreventas
**El Problema:** El modelo `Producto` actual no tiene un límite ni contabilizador físico de estantes. Si cuentas con 2 Laptops de stock y tres personas presionan "Comprar" a la vez, la plataforma venderá 3 unidades de manera fantasma. Esto acarrea pésima reputación, demandas y tasas de reversibilidad de pago excesivas (que conllevan baneos de los proveedores de cobro).

### Código de Solución Recomendado:
**Migración Física en Base de Datos (en `migrate_db.py`):**
```python
def agregar_stock():
    with app.app_context():
        # Ejecutar esto primero contra DB remota sin perder informacion
        db.session.execute(text('ALTER TABLE producto ADD COLUMN stock INTEGER DEFAULT 0'))
        db.session.commit()
```
**Bloqueador Logístico en Backend (en `tienda.py`):**
```python
# Adición crítica antes de permitir Checkout
if producto.stock < item['cantidad']:
    flash(f'Lo sentimos, solo nos quedan {producto.stock} unidades de {producto.nombre}', 'error')
    return redirect(url_for('ver_carrito'))

# Si pasa, reservar inventario para evitar compras concurrentes concurrentes (Race Conditions)
producto.stock -= item['cantidad']
db.session.commit()
```

### 🔁 Alternativas:
Si se planea vender digitalmente (Ej: Cuentas de suscripción a cursos) la columna `stock` no importa, o se pueden trabajar esquemas de "Backorder" (Pre-ventas) permitiendo la venta así caiga por debajo del 0 (negativo), si y sólo si tienes un acuerdo con el importador local.

### ⚠️ Riesgos de Modificar esto:
Si el cliente llega a realizar el bloqueo bajando tu `producto.stock` en 1 unidad pero en el último de los casos cancela el pago de PayPal y no compra, **ese stock jamás se devuelve** y queda congelado para siempre. Se debe instruir al programador que utilice una cola de mensajería (Celery / BackgroundScheduler) para decirle al servidor: *"Si en 20 minutos esta sesión no confirma el dinero, regrésale la sumatoria 1 al stock principal automáticamente"*.

---

## 2. Amputación de Archivos debido a Arquitectura Serverless
**El Problema:** Guardas los archivos que los managers suben mediante el panel admin en la carpeta física de tu ecosistema `static/uploads/`. Cuando la plataforma intente escalar a Servidores en la Nube de Contenedores Dinámicos (ej: Heroku, AWS Fargate, Render), dichos pods o contenedores son "Efímeros" (*Stateless*). Al reiniciar el servidor en tu próxima versión, **tu carpeta `/uploads` se auto-disolverá y se borrarán visualmente todas las Laptops/Perfumes subidos**.

### Código de Solución Recomendado:
Al subir desde `admin.py`, no utilices `file.save()`. En su lugar, utiliza el SDK de Proveedores seguros para contenido estático (Cloudinary / AWS Bucket S3).

Ejemplo genérico con Cloudinary en vez de archivos locales:
```python
import cloudinary.uploader

@bp.route('/producto/nuevo', methods=['POST'])
@admin_required
def nuevo_producto():
    archivo = request.files['imagen']
    if archivo:
        # Enviar directo a los servidores espejo globales
        resultado = cloudinary.uploader.upload(archivo)
        # Guardo en MI base de datos solo la URL pública e inmortal generada
        nuevo_prod.imagen_url = resultado.get("secure_url") 
```

### 🔁 Alternativas:
Comprar/Alquilar unidades dedicadas de Almacenamiento Acoplado en Red (Network Attached Storages / AWS EFS) que sean inmortales y persistan a pesar de que el código reinicie. Resulta viable, pero costoso e ineficiente frente a un verdadero CDN global.

### ⚠️ Riesgos de Modificar esto:
Implica un trabajo extenso para migrar todas las sentencias donde exista código apuntando localmente como `<img src="{{ url_for('static', filename='uploads/' + prod.imagen) }}">`, reemplazándolo forzosamente por redireccionamientos HTTP llanos. Habrá que refactorizar todo el `index.html`.
