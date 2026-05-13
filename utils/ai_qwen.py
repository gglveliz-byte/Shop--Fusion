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
                "name": "createInvoice",
                "description": "Genera una factura legal a partir de un pedido pagado.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pedido_id": {
                            "type": "integer",
                            "description": "ID del pedido que se desea facturar (debe estar en estado 'pagado')."
                        }
                    },
                    "required": ["pedido_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "getInvoiceStatus",
                "description": "Consulta el estado y los detalles financieros de una factura por su ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "factura_id": {
                            "type": "integer",
                            "description": "ID único de la factura a consultar."
                        }
                    },
                    "required": ["factura_id"]
                }
            }
        }
    ]

    # System Prompt Maestro para el comportamiento de la IA
    SYSTEM_PROMPT = """Eres el Asistente de Gestión Inteligente de Shop Fusion. Tu rol abarca dos áreas críticas:
    
    1. ASISTENTE DE VENTAS: Ayudas a los clientes a registrar pedidos. 
       - REGLA: Necesitas Nombre, Teléfono, Dirección y IDs de productos. Usa 'createCustomerOrder'.
    
    2. GESTIÓN DE FACTURACIÓN: Ayudas a los administradores y clientes con sus comprobantes legales.
       - REGLA: Si un usuario solicita la factura de un pedido, usa 'createInvoice'. Informa que solo se pueden facturar pedidos PAGADOS.
       - REGLA: Si un usuario pregunta por el estado o detalles de una factura, usa 'getInvoiceStatus'.
    
    Tus reglas generales son:
    - Identidad: Profesional, ejecutivo y eficiente.
    - Seguridad: No inventes datos financieros. Si no tienes un ID, pídelo.
    - Confirmación: Siempre informa al usuario cuando hayas preparado una acción (orden o factura) exitosamente."""

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

    def get_response(self, prompt, model=None, system_instruction=None, history=None, tools=None):
        """
        Envía una consulta a la IA y retorna la respuesta estructurada.
        history: Lista de mensajes previos [{"role": "user", "content": "..."}, ...]
        tools: Lista personalizada de herramientas (si es None, usa las por defecto)
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

            # Determinar qué herramientas usar (las pasadas o las de la clase)
            final_tools = tools if tools is not None else self.TOOLS

            # Parámetros adicionales para el modelo de razonamiento (si aplica)
            extra_params = {}
            if target_model == "qwen-max": 
                extra_params["extra_body"] = {"enable_thinking": True}

            # Realizamos la llamada a la API con streaming activado
            response_stream = self.client.chat.completions.create(
                model=target_model,
                messages=messages,
                tools=final_tools if target_model == self.MODEL_LOGICA else None,
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

