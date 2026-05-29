# Herramientas de IA en Shop Fusion (Backlog Completo)

A continuación se detalla la lista oficial de los **10 Módulos de Herramientas** integrados mediante *function calling* con los modelos Qwen. Cada módulo tiene su rol principal asignado, los archivos clave donde se ejecuta la lógica y su correspondencia con el Backlog.

---

## 1. 🧾 Generación de órdenes de compra
**Descripción:** Permite a la IA crear, modificar y consultar órdenes de compra a partir de conversaciones con clientes o instrucciones del administrador.
**Rol principal:** Ventas / Admin
* **Archivos Clave:**
  * `routes/ai.py`: Orquesta y llama a la función `createCustomerOrder`.
  * `utils/ai_qwen.py`: Define el esquema de datos de la orden (cliente, productos, cantidades).
  * `models.py`: Estructura de datos (`Pedido` y `DetallePedido`).

---

## 2. 🧾 Facturación
**Descripción:** Genera facturas a partir de órdenes completadas o manualmente, asigna números de factura y calcula impuestos automáticamente.
**Rol principal:** Ventas / Admin
* **Archivos Clave:**
  * `utils/billing.py`: Contiene la lógica para el cálculo de impuestos.
  * `routes/ai.py`: Mapea las funciones de IA `createInvoice` y `getInvoiceStatus`.
  * `models.py`: Modelo de datos de `Factura` e impuestos.

---

## 3. 📊 Herramienta de Ventas (gestión de pipeline y CRM ligero)
**Descripción:** Permite a la IA registrar oportunidades, actualizar estados (contactado, negociación, cerrado, perdido) y extraer métricas básicas. Incluye resúmenes ejecutivos automáticos usando Qwen-Max.
**Rol principal:** Ventas
* **Archivos Clave:**
  * `utils/crm.py`: Contiene las funciones core `create_deal`, `update_deal_stage`, `forecast_revenue` y `generate_executive_summary`.
  * `routes/ai.py`: Conecta la IA con el CRM de la base de datos.
  * `models.py`: Modelo de datos `Oportunidad`.

---

## 4. 💳 Herramienta de cobros (Carrito y Pagos)
**Descripción:** Permite al agente manejar el carrito de compras, iniciar el proceso de checkout y generar comprobaciones de pago. *(Integrado a la lógica de e-commerce).*
**Rol principal:** Ventas / Admin
* **Archivos Clave:**
  * `utils/ai_qwen.py`: Herramientas de manejo como `addProductToCart`, `updateCartItem` y `checkoutCart`.
  * `routes/ai.py`: Intercepta comandos de checkout.
  * `utils/accounting.py`: Función `register_transaction` llamada cuando se confirma un cobro.

---

## 5. 📚 Contabilidad
**Descripción:** Registra ingresos, gastos, categoriza transacciones y genera reportes básicos (balance, pérdidas/ganancias). Se sincroniza automáticamente con cobros y facturación.
**Rol principal:** Admin / Asistente personal
* **Archivos Clave:**
  * `utils/accounting.py`: Catálogo de cuentas y funciones `register_transaction`, `get_account_balance`, `generate_monthly_report`.
  * `routes/ai.py`: Mapea y conecta estas herramientas para la IA.
  * `models.py`: Modelo de datos `Transaccion`.

---

## 6. 🔍 Validación de boucher (comprobante) de pagos
**Descripción:** Permite al agente (o al admin) validar textos o datos de transferencias y comprobantes, extrayendo monto, fecha y referencia.
**Rol principal:** Admin / Soporte
* **Archivos Clave:**
  * `utils/ai_qwen.py`: Esquema de la herramienta `validatePaymentReceipt`.
  * `routes/ai.py`: Parsea y aprueba el boucher validando la referencia del comprobante.

---

## 7. 🕸️ Web scraping
**Descripción:** Herramienta genérica para que la IA pueda extraer información de sitios web autorizados bajo demanda (competidores, listas de precios, documentación técnica).
**Rol principal:** Soporte técnico / Admin / Ventas
* **Archivos Clave:**
  * `utils/scraper.py`: Encapsula el servicio de extracción de HTML a texto limpio.
  * `utils/ai_qwen.py`: Define el esquema para la función `scrapeWebsite`.
  * `routes/ai.py`: Intercepta la llamada y le pasa el texto a la IA para su análisis.

---

## 8. 📦 Manejo de inventario en tiempo real
**Descripción:** Consulta y actualiza el stock de productos físicos. La IA puede informar disponibilidad, reservar artículos de forma temporal durante una venta, y alterar el stock general disparando alertas.
**Rol principal:** Ventas / Admin
* **Archivos Clave:**
  * `utils/inventory.py`: Funciones complejas como `search_product`, `check_stock`, `reserve_stock`, `update_stock`.
  * `routes/ai.py`: Mapea y asegura la ejecución en la base de datos.
  * `models.py`: Atributos `stock` y `stock_reservado`.

---

## 9. 🤖 Agente control total (Orquestador)
**Descripción:** Es el "cerebro" central que decide qué herramienta usar según la intención del usuario. Mantiene el contexto y ejecuta flujos de razonamiento continuos (ReAct).
**Rol principal:** Todos
* **Archivos Clave:**
  * `utils/ai_qwen.py`: Contiene el `SYSTEM_PROMPT` con las Reglas de Oro y toda la asignación dinámica de roles.
  * `routes/ai.py`: Bucle *While* principal que permite la encadenación multi-paso de herramientas antes de responder al usuario.

---

## 10. 📈 Reportes y analítica (Admin BI)
**Descripción:** Motor de Inteligencia de Negocios (BI) que genera comparativas financieras de crecimiento, márgenes netos reales y el ranking del rendimiento de los productos a lo largo del tiempo.
**Rol principal:** Admin / Analista BI Senior
* **Archivos Clave:**
  * `utils/analytics.py`: Motor matemático y de extracción de datos (`get_sales_report`, `compare_periods`, `get_top_products`).
  * `routes/ai.py`: Blinda y ejecuta las funciones como herramientas de acceso restringido para los administradores.

---

## ⚙️ Notas de Arquitectura e Infraestructura (Free Tier)
Dado que el proyecto utiliza servicios en la nube en su capa gratuita (**Free Tier**), la Inteligencia Artificial está adaptada para garantizar estabilidad:

1. **Un Paso a la Vez (Evita Bucles Infinitos):** 
   * Por seguridad, la IA procesa un máximo 3 herramientas de forma consecutiva.

2. **Falsos Negativos por Timeouts:** 
   * Si la BD entra en estado de suspensión temporal y la IA registra algo justo en ese segundo, puede que se guarde en la BD pero no llegue el mensaje visual de éxito al chat. En producción (con servidores de pago o SQLAlchemy `pool_pre_ping=True`), este comportamiento desaparece. Con ello si puede haber errores en algunos registros que requieren más tiempo en completarse.