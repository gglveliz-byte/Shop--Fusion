# Selección de Modelos IA para el Ecosistema Shop Fusion

Este documento detalla la selección estratégica de modelos Qwen para cumplir con los 9 requerimientos funcionales solicitados.

## 1. Modelo Principal: El Orquestador y Gestor de Lógica
**Modelo sugerido:** `qwen-plus` (o `qwen3.6-plus`)

Este modelo actuará como el "Cerebro" del sistema para 8 de las 9 herramientas:
1.  **Generación de órdenes de compra**: Manejo de datos estructurados y JSON Schema.
2.  **Facturación**: Cálculos lógicos y generación de registros de pago.
3.  **Gestión de Ventas (CRM ligero)**: Seguimiento de leads y pipeline.
4.  **Herramienta de cobros (PayPal)**: Interacción segura con la API de pagos.
5.  **Contabilidad**: Registro de ingresos/gastos y reportes financieros.
7.  **Web scraping**: Extracción e interpretación de datos externos.
8.  **Manejo de inventario**: Consulta y actualización de stock en tiempo real.
9.  **Agente control total (Orquestador)**: Planificación, razonamiento y ejecución de tareas multi-paso.

## 2. Modelo Especializado: La Visión
**Modelo sugerido:** `qwen-vl-max` (o `qwen-image-2.0`)

Utilizado específicamente para la herramienta restante:
6.  **Validación de boucher (OCR)**: Procesamiento visual de comprobantes de pago para extraer datos y validarlos contra el sistema.

## 3. Opción Alternativa: Modelo Unificado (Omni)
**Modelo sugerido:** `qwen3.5-omni-plus`

*   **Ventaja**: Permite manejar las 9 herramientas bajo un mismo modelo.
*   **Desventaja**: Al ser multimodal, puede ser ligeramente más lento en tareas puramente de texto que el modelo `plus` optimizado.

---

## Plan de Acción de Implementación

1.  **Fase 1: El Orquestador**: Implementar la lógica de "Function Calling" en `utils/ai_qwen.py`.
2.  **Fase 2: Herramientas de Datos**: Conectar la IA con las tablas de Productos e Inventario.
3.  **Fase 3: Integración Financiera**: Conexión con PayPal y sistema de facturación.
4.  **Fase 4: Inteligencia Visual**: Implementación del validador de boucher con el modelo VL.

---

## Variable de Entorno: `THINKING_MODELS` (Razonamiento Profundo)

En `utils/ai_qwen.py`, la aplicación tiene definidos los modelos base a usar (ej. `MODEL_LOGICA = "qwen-plus"`).

La variable `THINKING_MODELS` **no cambia qué modelo usas**, sino que actúa como una **"Lista VIP" de autorizaciones**. Habilitar el parámetro "Thinking" (razonamiento profundo) aumenta los costos y el tiempo de respuesta, por lo que está desacoplado del código y es configurable desde el `.env`.

**Cómo funciona:**

| Configuración en `.env` | Modelo en uso | ¿Se activa Thinking? |
|---|---|---|
| `THINKING_MODELS=qwen-max` | `qwen-plus` | ❌ No (`qwen-plus` no está en la lista) |
| `THINKING_MODELS=qwen-max,qwen-plus` | `qwen-plus` | ✅ Sí (está en la lista VIP) |

Esto permite encender o apagar capacidades avanzadas de razonamiento en producción al instante, **sin necesidad de tocar el código ni redesplegar la aplicación**.