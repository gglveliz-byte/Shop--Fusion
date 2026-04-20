Síntesis de Plan de Corrección: Shop Fusion (Estabilidad pre-SaaS)
Esta es la síntesis estratégica basada en los lineamientos entregados. El objetivo supremo es blindar el núcleo de la aplicación contra accesos no autorizados, desfalcos económicos por asincronía en pagos, o inconsistencia de la Base de Datos; todo para preparar el terreno para la futura "Marca Blanca" (SaaS).

🗂️ Archivos Críticos a Intervenir
A tu lista original, he sumado dos archivos ineludibles para la seguridad e integridad del proyecto:

config.py (Manejo de variables de entorno y JWT/Tokens)
routes/auth.py (Lógica de acceso)
routes/tienda.py (Checkout, manejo de inventario)
routes/admin.py (Panel de verificación)
models.py (Control de stock)
templates/tienda/index.html (Carrito en local storage)
init_db.py (Credenciales quemadas)
[AÑADIDO] app.py: Para forzar la inicialización global de CSRF (Flask-WTF).
[AÑADIDO] migrate_db.py: Crítico para inyectar la columna stock sin borrar la BD actual de producción.
📸 Estrategia sobre las "Fotos que validan el error"
Actualmente los errores son de backend puro (lógica). Presentaré la "fotografía del código" (code snippets de tu repositorio actual) que sirve como evidencia irrefutable del hueco de seguridad, justo al lado de la lista de verificación, cuando empecemos las correcciones. Cuando corrijamos errores del frontend (UI/UX) posteriormente, utilizaré mi navegador integrado para capturas de pantalla de la interfaz.

✅ Checklist de Implementación (Fases de Trabajo)
CAUTION

Regla de oro: No escribir nueva lógica de negocio (features) hasta que la casilla anterior esté verificada rigurosamente.

Fase 0: Preparación de Entorno (A la espera de tus instrucciones)
[ ] Configuración de separación Dev / Staging / Producción.
[ ] Creación del archivo .env cerrado (Sin claves quemadas en config.py).
Fase 1: Identidad y Seguridad de Acceso (Auth)
[ ] Erradicar contraseñas por defecto en init_db.py.
[ ] Parche en routes/auth.py para bloquear Bypass de autenticación.
[ ] Validar rate-limiting (protección contra fuerza bruta de contraseñas).
[ ] Inyectar tokens CSRF en todos los formularios de templates.
Fase 2: Integridad Financiera y Cobros (Pagos)
[ ] routes/tienda.py: Implementar Webhook asíncrono para PayPal (Validar transacciones estrictamente en el backend, nunca confíar en index.html).
[ ] Verificar el cálculo de montos totales directamente contra la base de datos, ignorando cualquier alteración de precio que mande el frontend.
Fase 3: Consistencia Operativa (Inventario y Estado)
[ ] models.py: Crear columna de stock.
[ ] migrate_db.py: Actualizar BD sin pérdida de datos.
[ ] routes/tienda.py: Descontar stock al reservar pedido y devolverlo si Paypal reporta un pago declinado o incompleto.