# Propuesta de Refactorización y Estabilización: Shop Fusion
**Documento Técnico para Aprobación de Supervisor**

Esta propuesta detalla la hoja de ruta estratégica para erradicar las vulnerabilidades críticas descubiertas durante la auditoría del proyecto. Las tareas están organizadas de mayor a menor urgencia. Ninguna nueva funcionalidad (SaaS/Multitenant) debe desarrollarse hasta que la Fase 2 sea completada.

---

## 🔴 FASE 1: Contención de Seguridad Crítica (Severidad Critica)
*Por aquí arrancaremos. Si nos atacan hoy, estas son las puertas de entrada.*

### 1.1 Exposición y Fugas de Sesión
- **El Problema:** El endpoint `/check-session` expone estado y roles sin necesidad. Configuraciones globales (`debug=True`) y contraseñas harcodeadas (`admin123` en la BD) están vulnerables en producción.
- **La Solución:** Borrado del endpoint de rastreo. Refactorizar `config.py` para forzar la lectura del 100% de los datos sensitivos (contraseñas, puertos, DB urls) desde un entorno aislado `.env`.
- **Qué se afecta:** `routes/auth.py`, `config.py`, `app.py`, `init_db.py`.
- **Tiempo Estimado:** 1 Día.

### 1.2 Vulnerabilidad Cross-Site Request Forgery (CSRF)
- **El Problema:** Ningún formulario del sistema cuenta con validación de "origen". Un atacante podría forzar transacciones financieras enviando POST engañosos desde otras páginas.
- **La Solución:** Implementar protección estandarizada mediante `Flask-WTF`. Se configurará globalmente en `app.py` y se inyectará el token `{{ csrf_token() }}` en todas las plantillas donde haya un `<form>`.
- **Qué se afecta:** `app.py`, y hasta 10 archivos en `templates/**/*.html`.
- **Tiempo Estimado:** 1 Día.

---

## 🟠 FASE 2: Integridad Financiera y Pasarela de Pagos (Severidad Alta)
*El corazón del negocio corre riesgo financiero por la actual arquitectura de cobros.*

### 2.1 Desincronización de Precios (Fraude Potencial)
- **El Problema:** Actualmente se confía en que el carrito del (`index.html`) mande a PayPal y WhatsApp el "Precio Total" correcto. Un usuario audaz puede abrir las herramientas de desarrollador y alterar su recibo a un total de $1.00 antes de pagar.
- **La Solución:** El *Backend debe ser el Rey*. El frontend enviará únicamente `{producto_id: 2, cantidad: 1}`. Python buscará los precios inalterables en la Base de Datos y construirá la factura a cobrar.
- **Qué se afecta:** `routes/tienda.py`, `templates/tienda/index.html`.
- **Tiempo Estimado:** 2 Días.

### 2.2 Validación de Transacciones (Fantasmas de PayPal)
- **El Problema:** Si el usuario cierra la ventana justo después de pagar en la pantalla de PayPal, pero antes de que nuestra web reciba la confirmación frontal, cobramos el dinero pero el "Pedido" jamás se guarda en nuestra Base de Datos.
- **La Solución:** Migrar a un modelo de eventos *Webhooks Asíncronos*. PayPal confirmará directamente al servidor vía API posterior que el dinero fue capturado (`payment.capture.completed`), protegiendo la transacción sin intervención del navegador.
- **Qué se afecta:** `routes/tienda.py` (Nueva ruta `/api/webhooks/paypal`).
- **Tiempo Estimado:** 2 Días.

---

## 🟡 FASE 3: Lógica Operativa (Severidad Media)
*Riesgos logísticos y estructurales que afectan las métricas y la mantención.*

### 3.1 Prevención de Sobreventas (Riesgo Retorno de Dinero)
- **El Problema:** El inventario no tiene límite ni columna de "Cantidad" en DB. Dos clientes pueden comprar el último artículo de manera concurrente.
- **La Solución:** Se inyectará por migración forzosa una columna de `stock`. Al dar clic en Pagar, ese stock quedará "reservado". Si transcurren 15 minutos sin llegar el pago del webhook, el sistema devolverá la unidad al catálogo.
- **Qué se afecta:** `models.py`, `migrate_db.py`, `routes/tienda.py`.
- **Tiempo Estimado:** 2 Días.

### 3.2 Almacenamiento Volátil de Imágenes
- **El Problema:** La app guarda imágenes en disco físico (`/static/uploads/`). Plataformas cloud como Render/Railway borran el disco entero tras cada reinicio, perdiendo el catálogo de imágenes.
- **La Solución:** Empalmar el código para que suba los datos directamente a **AWS S3** o **Cloudinary** interactuando por API en lugar de `file.save(local)`.
- **Qué se afecta:** `routes/admin.py`, `config.py`.
- **Tiempo Estimado:** 2 Días.

---

## 🟢 FASE 4: Optimización Base de Datos (Severidad Baja)
*Cuellos de botella de memoria y CPU para el futuro crecimiento.*

### 4.1 Sobrecarga Innecesaria
- **El Problema:** Consultas tipo `N+1` en pedidos, y cálculos reiterativos de hashing (`Bcrypt`) excesivos sin importar que sean innecesarios.
- **La Solución:** Utilizar `joinedload` en llamadas complejas. Poner condicionales al hashing de contraseñas de sesión.
- **Qué se afecta:** `routes/admin.py`, `routes/auth.py`.
- **Tiempo Estimado:** 1 Día.

---

## ⏱️ RESUMEN EJECUTIVO PARA LA GERENCIA
*   **Tiempo Total Estimado:** `8 a 11 Días Laborables`.
*   **Zona de Inicio:** El trabajo DEBE iniciar por la FASE 1 (Contención Auth / Config), dado que no bloquea la base de datos pero detiene accesos fantasma de inmediato.
*   **Impacto de Post-Entrega:** El sistema pasará de un estado de "Prototipo Viable" a "Producto Grado Producción", blindando las fugas monetarias para que el equipo pueda continuar tranquilamente desarrollando el SaaS multitenant seguro.
