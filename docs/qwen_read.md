# Investigación e Integración: Modelos Qwen (Alibaba Cloud)

Este documento resume la investigación, selección técnica y estado de integración de los modelos de IA Qwen en el proyecto **Shop Fusion**.

## 1. Análisis de Modelos Disponibles

> [!NOTE]
> Tras realizar una auditoría técnica mediante la API, se han identificado **154 modelos disponibles** vinculados a la `DASHSCOPE_API_KEY`. El catálogo incluye versiones actualizadas, snapshots históricos (fechados), modelos de baja latencia y especializados. Para fines de este proyecto, se han agrupado en las siguientes familias principales:

| Categoría | Variantes Encontradas | Grupos de Modelos Principales | Capacidades Clave | Uso Sugerido |
| :--- | :--- | :--- | :--- | :--- |
| **General (Core)** | ~45 modelos | `qwen-plus`, `qwen-max`, `qwen-turbo` | Alta velocidad, multilingüe, balance costo/beneficio. | Chatbots, resúmenes, atención al cliente general. |
| **Deep Thinking** | ~12 modelos | `qwen3-32b`, `qwq-plus`, `deepseek-v3.2` | Razonamiento lógico avanzado, resolución de problemas. | Análisis de datos, lógica compleja, matemáticas. |
| **Coding** | ~8 modelos | `qwen3-coder-plus`, `qwen-coder-plus` | Especializado en 92+ lenguajes, autocompletado. | Generación de código, explicación y revisión técnica. |
| **Vision (VL)** | ~35 modelos | `qwen-image-2.0`, `qwen-vl-max` | Comprensión de imágenes, OCR, descripción visual. | Búsqueda por imagen, lectura de documentos (facturas). |
| **Omni-Modal** | ~15 modelos | `qwen3.5-omni-plus`, `qwen-omni-turbo` | Procesamiento simultáneo de texto, audio e imagen. | Asistentes virtuales avanzados de voz y visión. |
| **Audio / Voz** | ~25 modelos | `qwen3-tts`, `qwen3-asr`, `qwen3-vc` | Síntesis de voz (TTS) y transcripción (ASR). | Comandos de voz, lectura de textos en voz alta. |
| **Traducción** | ~8 modelos | `qwen-mt-plus`, `qwen3-livetranslate` | Traducción automática de alta fidelidad. | Localización de la tienda para otros idiomas. |
| **Embeddings** | 6 modelos | `text-embedding-v3`, `text-embedding-v4` | Conversión de texto a vectores numéricos. | Motores de búsqueda interna semántica (por significado). |

## 2. Detalles de Implementación Técnica

### Endpoint y Autenticación

- **Servidor**: Alibaba Cloud Model Studio (Región Internacional/Singapore).
- **Base URL**: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
- **Librería**: `openai` (v1.50.0+) para máxima compatibilidad y soporte de proxies.

### Gestión de "Deep Thinking" (qwen3-32b)

Para el modelo de razonamiento, se ha implementado el parámetro `enable_thinking: True`.

> [!IMPORTANT]
> El modo de pensamiento profundo requiere obligatoriamente el uso de **Streaming** (`stream=True`) para capturar el canal de razonamiento antes de la respuesta final.

## 3. Estado de la Lista de Tareas (Checklist)

- [x] **Investigación de modelos**: Revisión de documentación y capacidades.
- [x] **Configuración del cliente API**: Cliente unificado creado en `utils/ai_qwen.py`.
- [x] **Gestión segura**: `DASHSCOPE_API_KEY` integrada en sistema de variables de entorno blindadas.
- [x] **Implementación técnica**: Soporte para `reasoning_content` y `content` diferenciado.
- [x] **Prueba de concepto**: Interfaz CLI (Terminal) funcional en `ai_test_terminal.py`.
- [/] **Chat Básico**: Estructura preparada, pendiente integración en interfaz web.
- [/] **Streaming**: Validado y funcionando en el motor de servicio.

## 4. Instrucciones para Pruebas Rápidas

Para verificar la conexión y el comportamiento de los modelos sin afectar la base del servidor web, ejecutar:

```powershell
python ai_test_terminal.py
```

---

_Documentación generada como parte del proceso de Integración de IA para el proyecto._
