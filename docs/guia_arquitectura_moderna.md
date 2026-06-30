# Guía de Arquitectura Modernizada - ShopFusion

Esta guía documenta los cambios arquitectónicos implementados durante las Fases de seguridad y optimización. Sirve como referencia para el administrador y desarrolladores sobre cómo operar el sistema en Producción y Desarrollo.

---

## 1. Gestión de Base de Datos (Flask-Migrate vs Scripts Manuales)

En la nueva arquitectura, hemos separado claramente la "Inicialización" de la "Evolución" de la base de datos para evitar pérdida accidental de datos.

### A. `init_db.py` (Punto de Partida)
Este script se utiliza **exclusivamente para la configuración inicial** o cuando se desea reinyectar datos perdidos.
- **Funcionamiento actual:** Gracias a la Fase 11, este script ahora es "inteligente y selectivo". Si borras un producto de prueba desde el Panel de Administrador, puedes volver a correr `python init_db.py` en tu terminal. El script buscará únicamente los elementos que faltan y los insertará sin alterar los que ya existen ni destruir la base de datos.
- **¿Cuándo usarlo?** Al clonar el proyecto por primera vez o para recuperar productos de demostración eliminados por accidente.

### B. Flask-Migrate (Evolución de la Base de Datos)
Reemplaza scripts manuales peligrosos como `migrate_db.py`. Es la herramienta oficial para modificar tablas sin perder los registros de los clientes.

**Flujo de Trabajo Básico:**
1. **El "Punto Cero" (Se hace solo una vez en un proyecto que ya tiene tablas):**
   ```bash
   flask db init
   flask db stamp head
   ```
   *(El comando `stamp head` es crucial porque le dice a Flask-Migrate: "La base de datos ya existe y está sincronizada con el código actual, no intentes crear todo de nuevo").*

2. **Cuando modificas `models.py` (ej. agregas un campo nuevo):**
   ```bash
   flask db migrate -m "Mensaje descriptivo del cambio"
   ```
   *(Alembic detecta los cambios automáticamente y genera un archivo SQL).*

3. **Para aplicar los cambios a la base de datos real:**
   ```bash
   flask db upgrade
   ```

### C. `migrate_db.py`
Es un script heredado (legacy) de parcheo manual. Fue blindado en la Fase 11 y 12 para ser seguro, pero en el futuro, todo nuevo cambio de esquema debe realizarse usando Flask-Migrate.

---

## 2. Protección de API y CORS (`ALLOWED_ORIGINS`)

**El Problema:** La API de IA conectada a Qwen (Alibaba) tiene un costo asociado. Sin restricciones, un atacante podría insertar tu chat en su propia página web y gastar tu saldo.
**La Solución:** Implementamos una política estricta de CORS en `app.py`. Si la petición no proviene de una lista blanca de dominios autorizados, el servidor la bloquea inmediatamente.

**Configuración en archivo `.env`:**
- **Para Desarrollo (Local):**
  ```env
  ALLOWED_ORIGINS=http://localhost:5000,http://127.0.0.1:5000
  ```
- **Para Producción (Render, AWS, etc.):**
  ```env
  ALLOWED_ORIGINS=https://mi-tienda-shopfusion.com,https://mi-tienda.onrender.com
  ```

---

## 3. Lógica de Inteligencia Artificial (`THINKING_MODELS`)

En `ai_qwen.py`, la aplicación tiene definidos por defecto los modelos base a usar (ej. `MODEL_LOGICA = "qwen-plus"`). 

La nueva variable de entorno `THINKING_MODELS` **no cambia qué modelo usas**, sino que actúa como una **"Lista VIP" de autorizaciones**.
Debido a que habilitar el parámetro "Thinking" (razonamiento profundo) puede aumentar costos o tiempo de respuesta, ahora está totalmente desacoplado del código fuente.

**Cómo funciona:**
Si tu aplicación está configurada para usar `qwen-plus`, antes de llamar a la API evalúa:
- Si `.env` tiene `THINKING_MODELS=qwen-max`: `qwen-plus` NO está en la lista. Se ejecuta una consulta estándar.
- Si `.env` tiene `THINKING_MODELS=qwen-max,qwen-plus`: `qwen-plus` SÍ está en la lista VIP. La app inyectará automáticamente `{"enable_thinking": True}` en la petición.

Esto permite encender o apagar capacidades avanzadas de razonamiento en producción al instante, sin necesidad de tocar el código ni redesplegar la aplicación.

---

## 4. Prevención de Ataques y Redis (`REDIS_URL`)

**El Problema:** Anteriormente, el limitador de tráfico (Rate Limiting) usaba la memoria RAM (`memory://`). Si un atacante sufría un bloqueo por múltiples intentos fallidos (Fuerza Bruta), solo necesitaba esperar a que el servidor de Render se reiniciara (o provocar un reinicio) para que la RAM se limpiara y pudiera volver a atacar.
**La Solución:** En la Fase 2, migramos el limitador de `auth.py` y rutas globales a **Redis** mediante la estrategia de `moving-window`.

**Errores comunes (WinError 10061):**
Si ejecutas la app localmente en Windows y ves `ConnectionRefusedError: [WinError 10061] localhost:6379`, significa que Flask está buscando a Redis pero no lo tienes instalado localmente.

**Solución en Desarrollo:**
Usa un proveedor gratuito de Redis en la nube (como Upstash) y configura la URL en tu archivo `.env`. Así tu entorno de desarrollo funcionará exactamente igual que Producción.
```env
REDIS_URL=rediss://default:tu_contraseña_secreta@tu-servidor.upstash.io:6379
```
