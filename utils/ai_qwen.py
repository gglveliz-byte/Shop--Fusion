import os
from openai import OpenAI
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

class QwenAIService:
    """
    Servicio para interactuar con los modelos de Alibaba Cloud Qwen.
    Configurado para manejar Ventas, CRM y Facturación con inteligencia estratégica.
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
                        "customer_name": {"type": "string", "description": "Nombre completo del cliente."},
                        "customer_phone": {"type": "string", "description": "WhatsApp o teléfono."},
                        "customer_address": {"type": "string", "description": "Dirección de entrega."},
                        "items": {
                            "type": "array",
                            "description": "Lista de productos que el cliente desea comprar.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "product_id": {"type": "integer","description": "ID numérico del producto en el catálogo."},
                                    "quantity": {"type": "integer","description": "Cantidad de unidades del producto."}
                                },
                                "required": ["product_id", "quantity"]
                            }
                        }
                    },
                    "required": ["customer_name", "customer_phone", "customer_address", "items"]
                }
            }
        },
        # --- HERRAMIENTAS DE CRM ---
        {
            "type": "function",
            "function": {
                "name": "createDeal",
                "description": "Registra una nueva oportunidad o prospecto en el CRM.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_name": {"type": "string", "description": "Nombre del prospecto."},
                        "estimated_value": {"type": "number", "description": "Valor monetario del negocio."},
                        "notes": {"type": "string", "description": "Detalles del interés."}
                    },
                    "required": ["customer_name", "estimated_value"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "updateDealStage",
                "description": "Actualiza la etapa de un negocio (prospecto, contactado, negociacion, cerrado_ganado, cerrado_perdido).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "deal_id": {"type": "integer"},
                        "new_stage": {"type": "string", "enum": ["prospecto", "contactado", "negociacion", "cerrado_ganado", "cerrado_perdido"]}
                    },
                    "required": ["deal_id", "new_stage"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "forecastRevenue",
                "description": "Extrae métricas básicas y proyecciones de ingresos del pipeline actual.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generateExecutiveSummary",
                "description": "Genera resúmenes ejecutivos automáticos analizando ventas y CRM con Qwen-Max.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        # --- HERRAMIENTAS DE FACTURACIÓN ---
        {
            "type": "function",
            "function": {
                "name": "createInvoice",
                "description": "Genera una factura legal a partir de un pedido pagado.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pedido_id": {"type": "integer"}
                    },
                    "required": ["pedido_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "getInvoiceStatus",
                "description": "Consulta el estado de una factura por su ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "factura_id": {"type": "integer"}
                    },
                    "required": ["factura_id"]
                }
            }
        },

        # -- HERRAMIENTAS DE CONTABILIDAD --
        {
            "type": "function",
            "function": {
                "name": "recordTransaction",
                "description": "Registra un ingreso o gasto manual en la contabilidad.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["ingreso", "gasto"]},
                        "amount": {"type": "number"},
                        "category": {"type": "string", "description": "Ej: marketing, salarios, servicios, venta, otros"},
                        "source": {"type": "string", "description": "Ej: caja, banco, paypal"},
                        "description": {"type": "string"}
                    },
                    "required": ["type", "amount", "category"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "getAccountBalance",
                "description": "Consulta el balance general (Ingresos vs Gastos).",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generateMonthlyReport",
                "description": "Genera un reporte detallado de gastos e ingresos por categoría.",
                "parameters": {"type": "object", "properties": {}}
            }
        }
    ]

    SYSTEM_PROMPT = """Eres el Asistente de Gestión Integral de Shop Fusion.
    
    1. ASISTENTE DE VENTAS: Ayudas a registrar pedidos con 'createCustomerOrder'. Necesitas Nombre, Teléfono, Dirección e ítems.
    
    2. GESTIÓN CRM (Qwen-Plus): Registra prospectos con 'createDeal', actualiza etapas con 'updateDealStage' e informa métricas con 'forecastRevenue'.
    
    3. RESÚMENES EJECUTIVOS (Qwen-Max): Para análisis estratégicos de alto nivel, usa 'generateExecutiveSummary'.
    
    4. FACTURACIÓN: Gestiona comprobantes con 'createInvoice' y 'getInvoiceStatus'.

    5. CONTABILIDAD: Registra finanzas con 'recordTransaction', consulta saldos con 'getAccountBalance' y reportes con 'generateMonthlyReport'.
    
    Sé profesional, ejecutivo y siempre confirma las acciones realizadas."""

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
        """Envía consulta a la IA con protección total (Try-Catch)."""
        if not self.client: return "Error: API KEY no configurada."

        try:
            # 1. Configuración de mensajes
            sys_msg = system_instruction if system_instruction else self.SYSTEM_PROMPT
            messages = [{"role": "system", "content": sys_msg}]
            if history: messages.extend(history)
            messages.append({"role": "user", "content": prompt})

            # 2. Selección de modelo y herramientas
            target_model = model if model else self.MODEL_LOGICA
            final_tools = tools if tools is not None else self.TOOLS

            extra_params = {}
            if target_model == "qwen-max": 
                extra_params["extra_body"] = {"enable_thinking": True}

            # 3. Llamada a la API
            response_stream = self.client.chat.completions.create(
                model=target_model,
                messages=messages,
                tools=final_tools if target_model == self.MODEL_LOGICA else None,
                stream=True,
                **extra_params
            )

            full_content, full_reasoning, tool_calls = "", "", []
            for chunk in response_stream:
                if not chunk.choices: continue
                delta = chunk.choices[0].delta
                
                # Capturar razonamiento
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    full_reasoning += delta.reasoning_content
                
                # Capturar contenido
                if delta.content: full_content += delta.content
                
                # Capturar herramientas
                if delta.tool_calls:
                    for tc_chunk in delta.tool_calls:
                        if len(tool_calls) <= tc_chunk.index:
                            tool_calls.append({
                                "id": tc_chunk.id, "type": "function",
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
            return f"Error Qwen: {str(e)}"

# Instancia global del servicio
qwen_service = QwenAIService()