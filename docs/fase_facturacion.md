# Plan de Implementación: Módulo de Facturación Inteligente (IA)

Este documento detalla la hoja de ruta para integrar la facturación automatizada y asistida por IA en Shop Fusion.

## Fase 1: Infraestructura y Lógica de Negocio (El Cimiento)
- [ ] **Paso 1: Modelado de Datos**: Crear el modelo `Factura` vinculado a `Pedido` y actualizar `Configuracion` con el campo `iva_porcentaje`.
- [ ] **Paso 2: Motor de Impuestos**: Implementar lógica en Python para cálculos automáticos basados en configuración.
- [ ] **Paso 3: API de Gestión**: Endpoints `/api/factura/generate` (POST) y `/api/factura/<id>` (GET).

## Fase 2: Cerebro de Facturación (Integración IA)
- [ ] **Paso 4: Function Calling**: Diseñar esquemas JSON para `createInvoice` y `getInvoiceStatus`.
- [ ] **Paso 5: Orquestador Qwen**: Actualizar el `System Prompt` para manejo de intenciones de facturación.
- [ ] **Paso 6: Ejecución de Herramientas**: Conectar la respuesta de la IA con la creación real de registros en la BD.

## Fase 3: Validación y Seguridad (Blindaje)
- [ ] **Paso 7: Interfaz Visual**: Plantilla HTML profesional para visualización de facturas.
- [ ] **Paso 8: Human-in-the-loop**: Integración en el chat para pre-visualizar la factura antes de confirmarla.
- [ ] **Paso 9: Control de Roles**: Restricción de acceso exclusivo para `Admin` y `Ventas`.

---

## Diseño del Modelo `Factura`
- `id`: Identificador único.
- `numero_factura`: Formato correlativo (ej: FAC-0001).
- `pedido_id`: Relación con el pedido de origen.
- `subtotal`: Monto base.
- `iva_monto`: Impuesto calculado.
- `total`: Monto final.
- `estado`: emitido, pagado, anulado.
- `creado_en`: Fecha de emisión.

---
*Shop Fusion IA Project - 2026*
