# Registro de Errores y Mejoras - Shop Fusion

## Cómo leer este documento

Este documento está diseñado para ser claro y accesible, incluso para personas sin experiencia técnica avanzada. Aquí te explicamos cómo usarlo:

### Estructura del documento:
- **Registro de Errores**: Problemas que impiden el funcionamiento correcto de la aplicación
- **Problemas Técnicos**: Dificultades que afectan el mantenimiento y escalabilidad
- **Mejoras Propuestas**: Sugerencias para hacer el código mejor

### Cómo interpretar cada error:
- **Descripción**: Qué está mal y dónde
- **Módulo afectado**: Archivo(s) donde ocurre el problema
- **Impacto**: Por qué es importante arreglarlo
- **Solución**: Cómo corregirlo (con ejemplos cuando es posible)

### Glosario de términos técnicos:
- **API**: Interfaz de Programación de Aplicaciones (conjunto de reglas para que programas se comuniquen)
- **BD**: Base de Datos (lugar donde se almacenan los datos)
- **Debugging**: Proceso de encontrar y corregir errores en el código
- **Logging**: Sistema para registrar eventos y mensajes del programa
- **Rollback**: Revertir cambios en la base de datos si algo sale mal
- **SQLAlchemy**: Librería para trabajar con bases de datos en Python
- **Flask**: Framework web para crear aplicaciones en Python
- **DRY**: Don't Repeat Yourself (principio de no repetir código)
- **CSRF**: Cross-Site Request Forgery (ataque de seguridad web)

---

## Objetivo
Centralizar el registro de:
- Errores detectados (problemas que rompen la aplicación)
- Problemas técnicos (dificultades de mantenimiento)
- Mejoras propuestas (sugerencias para optimizar)

Este documento sirve como guía para debugging, mantenimiento y evolución del sistema Shop Fusion.

---

## Prioridad de corrección

### 🔴 Alta (arreglar inmediatamente):
- Error 5: Import faltante en `app.py` (impide que la app inicie)
- Error 6: `codigo` puede ser nulo (causa crashes en formularios)
- Error 8: Configuración insegura (riesgos de seguridad)

### 🟡 Media (arreglar pronto):
- Error 1: Uso de print() (afecta debugging)
- Error 2: Excepciones genéricas (dificulta encontrar errores)
- Error 4: Contraseñas inseguras (riesgo de seguridad)

### 🟢 Baja (mejoras futuras):
- Error 3: Código duplicado (eficiencia)
- Error 7: Validación insuficiente (seguridad)
- Error 9: Dependencias (estabilidad)

---

## Registro de Errores

### Fecha: 13 de abril de 2026

#### Error 1: Uso excesivo de print() en producción
**Descripción**: En lugar de usar un sistema profesional de logging, el código usa `print()` para mostrar mensajes. Esto se encuentra en:
- `migrate_db.py` (líneas 21-29, 39-72, 77-79): Muestra progreso de migraciones
- `init_db.py` (líneas 20-33, 46-49, 85-117): Muestra creación de datos iniciales
- `test_app.py` (líneas 11-13, 16-99): Muestra resultados de pruebas

**Ejemplo del problema**:
```python
print("Creando tablas en la base de datos...")  # Esto va a la consola
```

**Módulo afectado**: `migrate_db.py`, `init_db.py`, `test_app.py`
**Impacto**: En producción, estos mensajes no se guardan en archivos de log, dificultando el debugging cuando algo sale mal. Además, generan ruido innecesario.
**Solución**: 
1. Importar el módulo `logging` al inicio de cada archivo
2. Reemplazar `print()` con `logging.info()`, `logging.error()`, etc.
3. Configurar un archivo de configuración de logging

**Ejemplo de solución**:
```python
import logging
logging.basicConfig(level=logging.INFO)

# En lugar de:
print("Creando tablas...")

# Usar:
logging.info("Creando tablas en la base de datos...")
```

#### Error 2: Manejo de excepciones genérico
**Descripción**: El código usa `except:` o `except Exception:` que capturan TODOS los errores, incluyendo los que no deberían manejarse ahí. Ubicaciones:
- `routes/admin.py` líneas 134, 224, 464, 516: En creación/edición de productos y afiliados
- `routes/tienda.py` líneas 422, 556, 670: En procesamiento de pagos y pedidos
- `migrate_db.py` línea 75: En migraciones de base de datos

**Ejemplo del problema**:
```python
try:
    # código que puede fallar
    precio = Decimal(request.form.get('precio'))
except:  # ¡Malo! Captura todo
    flash('Error desconocido', 'error')
```

**Módulo afectado**: `routes/admin.py`, `routes/tienda.py`, `migrate_db.py`
**Impacto**: Si ocurre un error inesperado (como `KeyboardInterrupt`), se maneja como un error normal, ocultando problemas reales y dificultando el debugging.
**Solución**: 
1. Capturar excepciones específicas según el contexto
2. Usar logging para registrar el error completo
3. Dejar que errores críticos (como `SystemExit`) se propaguen

**Ejemplo de solución**:
```python
try:
    precio = Decimal(request.form.get('precio'))
except ValueError:
    logging.error(f"Precio inválido: {request.form.get('precio')}")
    flash('El precio debe ser un número válido', 'error')
except Exception as e:
    logging.exception("Error inesperado en procesamiento de precio")
    flash('Error interno del servidor', 'error')
```

#### Error 3: Código duplicado para formateo de WhatsApp
**Descripción**: La lógica para dar formato a números de teléfono de WhatsApp se repite múltiples veces en `routes/tienda.py`. Cada vez hace lo mismo: agregar código de país y formatear el número.

**Ejemplo del problema** (se repite en varias líneas):
```python
if whatsapp_numero.startswith('0'):
    whatsapp_numero = '593' + whatsapp_numero[1:]
elif not whatsapp_numero.startswith('+') and not whatsapp_numero.startswith('593'):
    whatsapp_numero = '593' + whatsapp_numero
```

**Módulo afectado**: `routes/tienda.py` (líneas 71-73, 105-107, 316-318, 701-703, 761-763, 796-798)
**Impacto**: Si se cambia la lógica de formateo, hay que modificar múltiples lugares, aumentando el riesgo de errores y olvidos.
**Solución**: 
1. Crear una función helper en un archivo `utils.py`
2. Usar esa función en todos los lugares donde se formatea WhatsApp

**Ejemplo de solución**:
```python
# En utils.py
def format_whatsapp_number(numero):
    if not numero:
        return numero
    if numero.startswith('0'):
        return '593' + numero[1:]
    elif not numero.startswith('+') and not numero.startswith('593'):
        return '593' + numero
    return numero

# En routes/tienda.py
from utils import format_whatsapp_number
whatsapp_numero = format_whatsapp_number(whatsapp_numero)
```

#### Error 4: Contraseñas por defecto inseguras
**Descripción**: El sistema crea automáticamente un usuario administrador con contraseña 'admin123', que es fácil de adivinar. Esto está en `init_db.py` y se menciona en `test_app.py`.

**Ejemplo del problema**:
```python
admin = Admin(username='admin')
admin.set_password('admin123')  # ¡Contraseña hardcodeada!
```

**Módulo afectado**: `init_db.py`, `test_app.py`
**Impacto**: Cualquier persona que instale el sistema puede acceder como administrador sin esfuerzo, creando un grave riesgo de seguridad.
**Solución**: 
1. No crear usuarios con contraseñas por defecto
2. Generar contraseñas aleatorias seguras durante la instalación
3. Forzar cambio de contraseña en el primer login
4. Usar variables de entorno para configurar credenciales iniciales

**Ejemplo de solución**:
```python
import secrets

# Generar contraseña segura aleatoria
admin_password = secrets.token_urlsafe(12)
admin.set_password(admin_password)

print(f"Usuario admin creado. Contraseña temporal: {admin_password}")
print("¡IMPORTANTE! Cambia esta contraseña inmediatamente después del primer login.")
```

#### Error 5: Import faltante en `app.py`
**Descripción**: El archivo `app.py` usa la función `os.makedirs()` en la línea 27, pero no importa el módulo `os` al inicio del archivo.

**Ejemplo del problema**:
```python
# Línea 27 en app.py
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  # Error: os no definido
```

**Módulo afectado**: `app.py` (línea 27)
**Impacto**: La aplicación no puede iniciarse, mostrando un error `NameError: name 'os' is not defined`.
**Solución**: Agregar `import os` al inicio del archivo `app.py`.

**Ejemplo de solución**:
```python
# Al inicio de app.py, agregar:
import os

# Luego el resto del código funciona
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
```

#### Error 6: `codigo` puede ser nulo en el formulario de afiliado
**Descripción**: En la creación de afiliados, el código se obtiene del formulario y se llama `.upper()` directamente, pero si el campo está vacío, `request.form.get('codigo')` devuelve `None`, causando un error.

**Ejemplo del problema**:
```python
codigo = request.form.get('codigo').upper()  # Error si 'codigo' es None
```

**Módulo afectado**: `routes/admin.py` (línea 439)
**Impacto**: Cuando un usuario envía el formulario sin el campo 'codigo', la aplicación se rompe con `AttributeError: 'NoneType' object has no attribute 'upper'`.
**Solución**: Verificar que el campo existe y no está vacío antes de procesarlo.

**Ejemplo de solución**:
```python
codigo_raw = request.form.get('codigo')
if not codigo_raw:
    flash('El código es obligatorio', 'error')
    return render_template('admin/crear_afiliado.html')

codigo = codigo_raw.strip().upper()
```

#### Error 7: Falta validación de entrada en formularios
**Descripción**: Los formularios web no verifican que los datos enviados sean del tipo correcto o tengan el formato esperado. Por ejemplo, campos numéricos podrían recibir texto.

**Ejemplo del problema**:
```python
precio = request.form.get('precio_final')  # Podría ser "abc" en lugar de un número
producto.precio_final = Decimal(precio)  # Error si no es numérico
```

**Módulo afectado**: Todas las rutas con formularios (`routes/admin.py`, `routes/tienda.py`, etc.)
**Impacto**: Los usuarios pueden enviar datos malformados que causan errores, o peor aún, datos maliciosos que podrían comprometer la seguridad.
**Solución**: 
1. Usar librerías como WTForms para validación de formularios
2. Verificar tipos de datos antes de procesar
3. Sanitizar entrada para prevenir ataques XSS

**Ejemplo de solución con WTForms**:
```python
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, validators

class ProductoForm(FlaskForm):
    nombre = StringField('Nombre', [validators.DataRequired(), validators.Length(max=200)])
    precio_final = DecimalField('Precio Final', [validators.DataRequired(), validators.NumberRange(min=0)])

# En la ruta:
form = ProductoForm()
if form.validate_on_submit():
    # Los datos ya están validados
    producto = Producto(nombre=form.nombre.data, precio_final=form.precio_final.data)
```

#### Error 8: Configuración insegura por defecto
**Descripción**: La configuración tiene valores por defecto que no son seguros para producción:
- `SECRET_KEY` tiene un valor de desarrollo si no hay variable de entorno
- `SESSION_COOKIE_SECURE = False` permite cookies inseguras
- No se valida que `DATABASE_URL` exista

**Ejemplo del problema**:
```python
SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'  # ¡No usar en producción!
SESSION_COOKIE_SECURE = False  # ¡Inseguro!
```

**Módulo afectado**: `config.py`
**Impacto**: Sesiones pueden ser interceptadas, datos sensibles expuestos, y la aplicación puede fallar si faltan configuraciones críticas.
**Solución**: 
1. Requerir variables de entorno críticas
2. Cambiar configuraciones de seguridad para producción
3. Usar diferentes configuraciones para desarrollo y producción

**Ejemplo de solución**:
```python
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY es requerida. Configura la variable de entorno.")
    
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL es requerida.")
```

#### Error 9: Dependencias potencialmente inestables
**Descripción**: Flask 3.0.0 es una versión muy nueva que puede tener bugs o incompatibilidades con otras librerías del proyecto.

**Módulo afectado**: `requirements.txt`
**Impacto**: La aplicación podría fallar de manera inesperada o tener comportamientos extraños en producción.
**Solución**: 
1. Usar versiones estables probadas de las dependencias
2. Hacer pruebas exhaustivas con la versión nueva
3. Considerar usar Flask 2.x si hay problemas de compatibilidad

**Ejemplo de solución**:
```txt
# requirements.txt
Flask==2.3.3  # Versión estable en lugar de 3.0.0
Flask-SQLAlchemy==3.0.5
# ... otras dependencias
```

---

## Problemas Técnicos

### Arquitectura monolítica
**Descripción**: Las rutas están en archivos muy grandes (tienda.py > 800 líneas), dificultando el mantenimiento.
**Impacto**: Código difícil de mantener, refactorizar y testear.

### Falta de tests unitarios
**Descripción**: Solo existe un script de prueba básico (`test_app.py`) sin tests unitarios reales.
**Impacto**: Riesgo alto de regresiones en cambios futuros.

### Configuración de base de datos mixta
**Descripción**: Soporte para SQLite y PostgreSQL sin configuración clara de migraciones.
**Módulo afectado**: `config.py`, `init_db.py`, `migrate_db.py`
**Impacto**: Confusión en entornos de desarrollo vs producción.

### Manejo de sesiones básico
**Descripción**: Uso de sesiones Flask sin configuración avanzada de seguridad.
**Módulo afectado**: `config.py`, `app.py`
**Impacto**: Posibles vulnerabilidades de sesión.

### Falta de logging estructurado
**Descripción**: No hay sistema de logging configurado para producción.
**Impacto**: Dificultad para monitorear y debuggear en producción.

---

## Mejoras Propuestas

### Optimización de Código

#### 1. Implementar logging adecuado
- Reemplazar todos los `print()` con `logging` module
- Configurar diferentes niveles de log (DEBUG, INFO, WARNING, ERROR)
- Crear archivo de configuración de logging

#### 2. Mejorar manejo de excepciones
- Especificar tipos de excepciones en bloques `except`
- Crear excepciones custom para la aplicación
- Implementar logging de errores con contexto

#### 3. Eliminar código duplicado
- Crear función helper para formateo de números de WhatsApp
- Extraer lógica común de validación de formularios
- Crear utilities para operaciones repetidas

#### 4. Agregar validación de entrada
- Implementar WTForms o similar para validación de formularios
- Validar tipos de datos y rangos
- Sanitizar entrada para prevenir XSS

### Mejora de Arquitectura

#### 1. Refactorización en módulos más pequeños
- Dividir `routes/tienda.py` en módulos separados (productos, carrito, checkout, paypal)
- Crear capa de servicios (services/) para lógica de negocio
- Implementar patrón Repository para acceso a datos

#### 2. Arquitectura en capas
```
├── controllers/ (routes actuales)
├── services/ (lógica de negocio)
├── repositories/ (acceso a datos)
├── models/ (modelos de datos)
└── utils/ (funciones helper)
```

#### 3. Configuración por entorno
- Variables de entorno para diferentes ambientes
- Configuración separada para desarrollo, staging, producción
- Secrets management seguro

### Refactorización

#### 1. Separar responsabilidades
- Mover lógica de negocio fuera de las rutas
- Crear clases para operaciones complejas
- Implementar patrón Factory para creación de objetos

#### 2. Mejora de modelos
- Agregar validaciones en modelos SQLAlchemy
- Implementar métodos de clase para consultas comunes
- Crear índices apropiados en base de datos

#### 3. Optimización de consultas
- Evitar N+1 queries con joins apropiados
- Implementar paginación en listados largos
- Cache para datos frecuentemente accedidos

### Decisiones Técnicas

#### 1. Framework de testing
- Adoptar pytest como framework de testing
- Crear tests unitarios para modelos y servicios
- Implementar tests de integración para rutas

#### 2. Sistema de autenticación
- Evaluar migración a Flask-JWT-Extended para APIs
- Implementar refresh tokens
- Agregar rate limiting para login

#### 3. Base de datos
- Migrar completamente a PostgreSQL para producción
- Implementar Alembic para migraciones versionadas
- Agregar conexión pool

### Cambios en Estructura

#### 1. Reorganización de archivos
```
Shop--Fusion/
├── app/
│   ├── __init__.py
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── utils/
│   └── templates/
├── tests/
├── migrations/
├── config/
└── scripts/
```

#### 2. Configuración de CI/CD
- GitHub Actions para testing automático
- Docker para containerización
- Deployment automatizado

#### 3. Documentación
- API documentation con Swagger/OpenAPI
- README actualizado con guías de desarrollo
- Documentación de arquitectura

### Nuevas Tecnologías Adoptadas

#### 1. Docker y containerización
- Dockerfile para aplicación
- Docker Compose para desarrollo local
- Multi-stage builds para optimización

#### 2. Sistema de cache
- Redis para sesiones y cache
- Cache de templates y consultas frecuentes

#### 3. Monitoreo y observabilidad
- Sentry para error tracking
- Prometheus + Grafana para métricas
- Structured logging con ELK stack

#### 4. Seguridad mejorada
- Helmet para headers de seguridad
- Rate limiting con Flask-Limiter
- CORS configurado apropiadamente

#### 5. API RESTful
- Flask-RESTful para APIs
- Serialización con Marshmallow
- Documentación automática con Flasgger

#### 6. Task queue
- Celery para tareas asíncronas (emails, reportes)
- Redis como broker de mensajes

---

## Próximos Pasos de Implementación

1. **Fase 1 (Semana 1-2)**: Implementar logging y manejo de excepciones
2. **Fase 2 (Semana 3-4)**: Refactorizar rutas en módulos más pequeños
3. **Fase 3 (Semana 5-6)**: Agregar validación de entrada y seguridad
4. **Fase 4 (Semana 7-8)**: Implementar tests unitarios
5. **Fase 5 (Semana 9-10)**: Containerización y CI/CD
6. **Fase 6 (Semana 11-12)**: Migración a PostgreSQL y optimizaciones

---