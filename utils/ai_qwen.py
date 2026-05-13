import os
from openai import OpenAI
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

class QwenAIService:
    """
    Servicio para interactuar con los modelos de Alibaba Cloud Qwen.
    Configurado para usar exclusivamente los modelos aprobados para Shop Fusion.
    """
    # Modelos oficiales aprobados (docs/seleccion_modelos_ia.md)
    MODEL_LOGICA = "qwen-plus"      # Para Orquestación, Ventas y Lógica
    MODEL_VISION = "qwen-vl-max"    # Para OCR y Validación de Bouchers

    # Definición de herramientas (Tools) para Function Calling
    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "createCustomerOrder",
                "description": "Crea un pedido de venta para un cliente final en la base de datos.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_name": {
                            "type": "string",
                            "description": "Nombre completo del cliente."
                        },
                        "customer_phone": {
                            "type": "string",
                            "description": "Número de WhatsApp o teléfono del cliente."
                        },
                        "customer_address": {
                            "type": "string",
                            "description": "Dirección de entrega del pedido."
                        },
                        "items": {
                            "type": "array",
                            "description": "Lista de productos que el cliente desea comprar.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "product_id": {
                                        "type": "integer",
                                        "description": "ID numérico del producto en el catálogo."
                                    },
                                    "quantity": {
                                        "type": "integer",
                                        "description": "Cantidad de unidades del producto."
                                    }
                                },
                                "required": ["product_id", "quantity"]
                            }
                        }
                    },
                    "required": ["customer_name", "customer_phone", "customer_address", "items"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "upsertDeal",
                "description": "Crea o actualiza una oportunidad en el CRM. Úsalo para prospectos o clientes interesados que aún no compran.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "description": "ID de la oportunidad si es para actualizar."},
                        "customer_name": {"type": "string", "description": "Nombre del prospecto."},
                        "estimated_value": {"type": "number", "description": "Valor monetario estimado del negocio."},
                        "stage": {
                            "type": "string", 
                            "enum": ["prospecto", "contactado", "negociacion", "cerrado_ganado", "cerrado_perdido"]
                        },
                        "notes": {"type": "string", "description": "Detalles del interés del cliente o seguimiento."}
                    },
                    "required": ["customer_name", "estimated_value"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "updateDealStage",
                "description": "Cambia la etapa de un negocio existente (ej: de negociación a cerrado).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "deal_id": {"type": "integer"},
                        "new_stage": {
                            "type": "string", 
                            "enum": ["prospecto", "contactado", "negociacion", "cerrado_ganado", "cerrado_perdido"]
                        }
                    },
                    "required": ["deal_id", "new_stage"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "getPipelineSummary",
                "description": "Obtiene estadísticas del pipeline de ventas (totales, pronósticos, conteos por etapa).",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
    ]

    # System Prompt Maestro para el comportamiento de la IA
    SYSTEM_PROMPT = """Eres el Asistente de Ventas y CRM Inteligente de Shop Fusion.
    
    Tus reglas de comportamiento son:
    1. Identidad: Eres amable, profesional y enfocado en cerrar ventas de forma estratégica.
    2. Ventas Directas: Usa 'createCustomerOrder' cuando un cliente indique qué productos quiere comprar ya mismo. Necesitas: Nombre, Teléfono, Dirección e ítems.
    3. Gestión de CRM: Usa 'upsertDeal' para registrar prospectos (leads) o negocios que aún están en negociación. Pide siempre el nombre y valor estimado.
    4. Seguimiento: Usa 'updateDealStage' cuando un cliente avance en su decisión (ej: de negociación a cerrado).
    5. Análisis: Si te preguntan sobre el estado de las ventas o el pipeline, usa 'getPipelineSummary'.
    6. Validación: Si faltan datos para un pedido o un negocio, pídelos cordialmente antes de procesar."""

    def __init__(self):
        # Configuración del cliente con el endpoint de Singapore (International)
        api_key = os.environ.get('DASHSCOPE_API_KEY')
        
        # Inicializamos el cliente solo si la API KEY existe
        self.client = None
        if api_key:
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
            )

    def get_response(self, prompt, model=None, system_instruction=None, history=None):
        """
        Envía una consulta a la IA y retorna la respuesta estructurada.
        history: Lista de mensajes previos [{"role": "user", "content": "..."}, ...]
        """
        if not self.client:
            return "Error: DASHSCOPE_API_KEY no configurada."

        # Usar el prompt maestro por defecto
        sys_msg = system_instruction if system_instruction else self.SYSTEM_PROMPT

        try:
            # Preparamos los mensajes: Sistema + Historial + Mensaje Actual
            messages = [{"role": "system", "content": sys_msg}]
            
            if history:
                messages.extend(history)
            
            messages.append({"role": "user", "content": prompt})

            # Usar modelo de lógica por defecto si no se especifica
            target_model = model if model else self.MODEL_LOGICA

            # Parámetros adicionales para el modelo de razonamiento (si aplica)
            extra_params = {}
            if target_model == "qwen-max": # Por si se escala a MAX en el futuro
                extra_params["extra_body"] = {"enable_thinking": True}

            # Realizamos la llamada a la API con streaming activado y herramientas registradas
            response_stream = self.client.chat.completions.create(
                model=target_model,
                messages=messages,
                tools=self.TOOLS if target_model == self.MODEL_LOGICA else None,
                stream=True,
                **extra_params
            )

            full_content = ""
            full_reasoning = ""
            tool_calls = []

            for chunk in response_stream:
                if not chunk.choices:
                    continue
                
                delta = chunk.choices[0].delta
                
                # 1. Capturar razonamiento (Deep Thinking)
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    full_reasoning += delta.reasoning_content
                
                # 2. Capturar contenido de texto normal
                if delta.content:
                    full_content += delta.content

                # 3. Capturar llamadas a funciones (Function Calling)
                if delta.tool_calls:
                    for tc_chunk in delta.tool_calls:
                        if len(tool_calls) <= tc_chunk.index:
                            tool_calls.append({
                                "id": tc_chunk.id,
                                "type": "function",
                                "function": {"name": tc_chunk.function.name, "arguments": ""}
                            })
                        
                        if tc_chunk.function.arguments:
                            tool_calls[tc_chunk.index]["function"]["arguments"] += tc_chunk.function.arguments
            
            return {
                "content": full_content if full_content else None,
                "reasoning": full_reasoning if full_reasoning else None,
                "tool_calls": tool_calls if tool_calls else None
            }

        except Exception as e:
            return f"Error al conectar con Qwen: {str(e)}", None

# Instancia global para ser usada en toda la app
qwen_service = QwenAIService()

