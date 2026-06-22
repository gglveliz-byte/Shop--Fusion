# Fase 2: Conectividad IA - Mapeo de Datos (JSON Schema)

Este documento registra el diseño del esquema de datos para la función `createPurchaseOrder`, permitiendo que el modelo **Qwen-Plus** convierta lenguaje natural en acciones estructuradas de compra.

## 1. Esquema de Función: `createPurchaseOrder`

Este esquema se utiliza en la configuración de `tools` del modelo Qwen para la detección de intención de compra.

```json
{
  "name": "createPurchaseOrder",
  "description": "Genera una orden de compra formal extrayendo datos de la solicitud del usuario.",
  "parameters": {
    "type": "object",
    "properties": {
      "supplier": {
        "type": "string",
        "description": "Nombre de la empresa o proveedor al que se le realiza la compra."
      },
      "items": {
        "type": "array",
        "description": "Lista de productos incluidos en la orden.",
        "items": {
          "type": "object",
          "properties": {
            "product_name": {
              "type": "string",
              "description": "Nombre o descripción del producto."
            },
            "quantity": {
              "type": "integer",
              "description": "Cantidad de unidades a solicitar."
            },
            "unit_price": {
              "type": "number",
              "description": "Precio unitario negociado o estimado (opcional)."
            }
          },
          "required": ["product_name", "quantity"]
        }
      },
      "priority": {
        "type": "string",
        "enum": ["baja", "media", "alta", "urgente"],
        "description": "Nivel de prioridad de la orden de compra."
      },
      "notes": {
        "type": "string",
        "description": "Comentarios adicionales o instrucciones especiales."
      }
    },
    "required": ["supplier", "items"]
  }
}
```

## 2. Flujo de Ejecución

1. **Input**: Usuario escribe "Compra 5 laptops Dell al proveedor TechSistemas".
2. **Procesamiento**: El motor `ai_qwen.py` recibe el prompt y detecta que coincide con el esquema `createPurchaseOrder`.
3. **Output Estructurado**: La IA devuelve un JSON con los campos mapeados.
4. **Acción**: El sistema de Shop Fusion procesa el JSON para registrar la orden en la base de datos (Fase 3).

---
*Documentación técnica - Shop Fusion IA Project*
