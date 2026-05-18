# Herramientas de IA en Shop Fusion

A continuación se detalla la lista de herramientas (Backlogs) integradas mediante function calling con los modelos Qwen. Cada módulo tiene un rol principal, archivos clave asociados y ejemplos de uso conversacional.

---

## 1. 🧾 Generación de órdenes de compra
**Descripción:** Permite a la IA crear, modificar y consultar órdenes de compra a partir de conversaciones con clientes o instrucciones del administrador.
**Rol principal:** Ventas / Admin
* **Archivos Clave:**
  * `routes/ai.py`: Orquesta la herramienta y llama a la función de creación (ej. `createCustomerOrder`).
  * `utils/ai_qwen.py`: Define el esquema de datos de la orden para la IA (cliente, productos, cantidades).
  * `models.py`: Contiene la estructura de datos (`Pedido`).
* **Ejemplo de Uso:**
  > *"Quiero hacer un pedido a nombre de Juan Pérez. Mi dirección es Calle Falsa 123. Deseo comprar 2 unidades del producto XYZ."*

---

## 2. 🧾 Facturación
**Descripción:** Genera facturas a partir de órdenes completadas o manualmente, asigna números de factura y calcula impuestos automáticamente.
**Rol principal:** Ventas / Admin
* **Archivos Clave:**
  * `utils/billing.py`: Contiene la lógica para el cálculo de impuestos (IVA configurable).
  * `routes/ai.py`: Integra las funciones de IA `createInvoice` y `getInvoiceStatus`.
  * `models.py`: Modelo de datos de `Factura` e impuestos en `Configuracion`.
* **Ejemplo de Uso:**
  > *"Genera la factura para el pedido número 5 que acaba de ser pagado."*

---

## 3. 📊 Herramienta de Ventas (gestión de pipeline y CRM ligero)
**Descripción:** Permite a la IA registrar oportunidades, actualizar estados (contactado, negociación, cerrado, perdido) y extraer métricas básicas. Incluye resúmenes ejecutivos automáticos usando Qwen-Max.
**Rol principal:** Ventas
* **Archivos Clave:**
  * `utils/crm.py`: Contiene las funciones core `create_deal`, `update_deal_stage`, `forecast_revenue` y `generate_executive_summary`.
  * `routes/ai.py`: Conecta la IA (Qwen-Plus para ventas y Qwen-Max para resúmenes).
  * `models.py`: Modelo de datos `Oportunidad`.
* **Ejemplo de Uso:**
  > *"Registra una oportunidad de negocio para 'Inversiones Tech' por 2500 dólares en etapa de prospección."*
  > *"Genera un reporte ejecutivo analizando el pipeline y las ventas actuales."*

---

## 4. 💳 Herramienta de cobros (PayPal API)
**Descripción:** Permite al agente generar enlaces de pago, verificar transacciones y solicitar reembolsos utilizando la API de PayPal. *(En desarrollo / Integración futura)*
**Rol principal:** Ventas / Admin
* **Archivos Clave (Ganchos / Hooks actuales):**
  * `utils/accounting.py`: Preparado para registrar la entrada de dinero en la cuenta "Banco/PayPal" cuando se confirme un pago.
  * `models.py`: La fuente `paypal` ya está soportada en el modelo de transacciones.
* **Ejemplo de Uso:**
  > *"Cobra 150 USD al cliente por el servicio X."*

---

## 5. 📚 Contabilidad
**Descripción:** Registra ingresos, gastos, categoriza transacciones y genera reportes básicos (balance, pérdidas/ganancias). Se sincroniza automáticamente con cobros y facturación.
**Rol principal:** Admin / Asistente personal
* **Archivos Clave:**
  * `utils/accounting.py`: Define el catálogo de cuentas y las funciones `register_transaction`, `get_account_balance`, `generate_monthly_report`.
  * `routes/ai.py`: Mapea `recordTransaction`, `getAccountBalance`, `generateMonthlyReport`. Aquí ocurre la sincronización automática con facturación.
  * `models.py`: Modelo de datos `Transaccion`.
* **Ejemplo de Uso:**
  > *"¿Cuánto hemos gastado en marketing este mes?"*
  > *"Registra un gasto operativo de 50 dólares."*

