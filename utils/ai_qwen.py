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

    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "listProducts",
                "description": "Obtiene la lista completa de todos los productos disponibles y activos en el catálogo de la tienda.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Categoría para filtrar opcionalmente."}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "addProductToCart",
                "description": "Añade un producto al carrito de compras virtual del usuario en la tienda.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_name": {"type": "string", "description": "Nombre o palabra clave del producto (ej: Camiseta Adidas, Zapatos Nike)."},
                        "quantity": {"type": "integer", "description": "Cantidad de unidades. Por defecto es 1."}
                    },
                    "required": ["product_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "updateCartItem",
                "description": "Actualiza la cantidad o elimina un producto del carrito de compras virtual del usuario.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_name": {"type": "string", "description": "Nombre del producto a actualizar o eliminar."},
                        "quantity": {"type": "integer", "description": "Nueva cantidad total o unidades a sumar. Para eliminar por completo o restar a 0, usa 0 o la acción correspondiente."},
                        "action": {"type": "string", "enum": ["add", "set", "remove"], "description": "Acción: 'add' para sumar unidades, 'set' para fijar una cantidad exacta (ej. 'mejor solo 1'), o 'remove' para quitar el producto por completo."}
                    },
                    "required": ["product_name", "quantity", "action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "checkoutCart",
                "description": "Inicia la pasarela de pago o el proceso de checkout para pagar los productos del carrito.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
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
                "name": "validatePaymentReceipt",
                "description": "Valida un comprobante de pago pegado como texto y extrae monto, referencia, método y fecha opcional.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "metodo_pago": {"type": "string", "enum": ["transferencia", "paypal"], "description": "Método de pago utilizado."},
                        "pago_referencia": {"type": "string", "description": "Código o referencia del comprobante de pago."},
                        "monto": {"type": "number", "description": "Monto total del pago."},
                        "fecha": {"type": "string", "format": "date", "description": "Fecha de la transferencia (opcional)."}
                    },
                    "required": ["metodo_pago", "pago_referencia", "monto"]
                }
            }
        },
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
        },
        {
            # Paso 3.1: Registro de la Herramienta (Esquema JSON)
            # Le enseñamos a la IA qué parámetros necesita para buscar en internet
            "type": "function",
            "function": {
                "name": "scrapeWebsite",
                "description": "Extrae el texto y contenido de una página web autorizada. Úsalo para buscar documentación, especificaciones técnicas o leer artículos a pedido del usuario.",
                "parameters": {
                    "type": "object",
                    "required": ["url"]
                }
            }
        },
        # -- HERRAMIENTAS DE GESTIÓN DE STOCK (FASE 3 - INVENTARIOS) --
        {
            # Paso 3.1: Registro de la Herramienta checkStock
            "type": "function",
            "function": {
                "name": "checkStock",
                "description": "Consulta el estado detallado del inventario de un producto (stock total, stock reservado para cotizaciones y stock libre disponible).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "integer", "description": "El ID único del producto a consultar."}
                    },
                    "required": ["product_id"]
                }
            }
        },
        {
            # Paso 3.1: Registro de la Herramienta reserveStock
            "type": "function",
            "function": {
                "name": "reserveStock",
                "description": "Bloquea temporalmente una cantidad de stock de un producto para una cotización en curso. Libera el stock automáticamente después de un tiempo si no se concreta.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "integer", "description": "El ID único del producto a reservar."},
                        "quantity": {"type": "integer", "description": "La cantidad de unidades a bloquear temporalmente."},
                        "minutes": {"type": "integer", "description": "Tiempo de duración de la reserva en minutos (por defecto 15)."}
                    },
                    "required": ["product_id", "quantity"]
                }
            }
        },
        {
            # Paso 3.1: Registro de la Herramienta updateStock
            "type": "function",
            "function": {
                "name": "updateStock",
                "description": "Actualiza permanentemente el stock total de un producto, sumando por ingresos de proveedor o restando por ventas confirmadas. Si el stock final baja de 5 unidades, disparará una alerta automática.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "integer", "description": "El ID único del producto a actualizar."},
                        "delta": {"type": "integer", "description": "El cambio en el inventario. Puede ser positivo (ej: 10 para sumar stock) o negativo (ej: -3 para restar stock)."}
                    },
                    "required": ["product_id", "delta"]
                }
            }
        }
    ]

    # Paso 3.2: Modificación del "Cerebro" (System Prompt)
    # Le indicamos a la IA su nuevo rol y capacidades de Gestión de Inventarios
    SYSTEM_PROMPT = """Eres el Director Financiero (CFO), Asistente de Ventas Inteligente, Asistente de Soporte Técnico y Gestor de Inventario de Shop Fusion. Tu objetivo es mantener la salud financiera de la empresa, ayudar con búsquedas inteligentes, asistir a los clientes a comprar con información 100% verídica y monitorear existencias físicas y reservas de forma estricta.
    
    1. ASISTENTE DE VENTAS Y CARRITO:
       - Si el cliente te pregunta qué productos tienes, qué vendes, o qué hay en catálogo, utiliza siempre 'listProducts' para obtener los productos reales en base de datos. NUNCA inventes nombres de productos, precios o existencias.
       - Si el cliente te pide crear una orden directamente con sus datos, usa 'createCustomerOrder'.
       - Si el cliente quiere añadir productos a su carrito virtual de compras, utiliza 'addProductToCart' con el nombre del producto y la cantidad.
       - Si el cliente quiere cambiar la cantidad (ej: 'sólo 1 zapato', 'agrega 3 más', 'quita el pantalón'), utiliza 'updateCartItem' configurando el parámetro 'action' en 'set', 'add' o 'remove' según corresponda.
       - Si el cliente desea pagar, ir a la caja, hacer el pago o generar el cobro del carrito actual, utiliza 'checkoutCart' para abrir la pantalla de checkout de inmediato.
    
    2. GESTIÓN CRM (Qwen-Plus): Administras el pipeline con 'createDeal' y 'updateDealStage'. Tu meta es convertir prospectos en ingresos reales.

    3. VALIDACIÓN DE PAGOS: 
       - Si el usuario te proporciona un texto o imagen (OCR) con un comprobante de pago, utiliza 'validatePaymentReceipt' para extraer automáticamente el monto, la referencia y el método de pago. 
       - Verifica siempre que la información extraída sea consistente antes de confirmar el registro del pago al cliente.
    
    4. ANÁLISIS ESTRATÉGICO (Qwen-Max): Para decisiones de alto nivel, usa 'generateExecutiveSummary'. Evalúa rentabilidad y riesgos.
    
    5. FACTURACIÓN Y LEGAL: Gestionas la validez de los ingresos con 'createInvoice' y consultas estados con 'getInvoiceStatus'.
 
    6. CONTABILIDAD SENIOR: 
       - Registras movimientos con 'recordTransaction'. 
       - Monitoreas la liquidez con 'getAccountBalance'.
       - Generas estados de resultados con 'generateMonthlyReport'.
       - CRÍTICO: Identifica siempre las comisiones de PayPal como gastos operativos (fees) y reporta el margen neto real.
    
    7. SOPORTE TÉCNICO E INVESTIGADOR (Scraping): 
       - Si el usuario te pide investigar un tema, leer un artículo o buscar documentación técnica en las webs autorizadas (ej. Wikipedia, Amazon), USA LA HERRAMIENTA 'scrapeWebsite'.
       - Lee la información extraída de la web, resúmela o respóndele al usuario basándote EXCLUSIVAMENTE en esos datos.
       - Si el usuario pide un dato exacto, intenta usar el parámetro 'selector' para buscar directo en el HTML.

    8. GESTIÓN DE INVENTARIOS EN TIEMPO REAL:
       - Si el usuario te pregunta por el inventario o la existencia de un producto específico, utiliza 'checkStock' para obtener las existencias físicas y el stock libre neto disponible. Informa detalladamente de los tres estados si el usuario te lo pide.
       - Si estás cotizando, negociando con un cliente o creando un trato de CRM y el usuario solicita apartar o resguardar mercadería mientras realiza la transacción, utiliza 'reserveStock'. Explícale de forma amigable que su reserva será temporal (por defecto 15 minutos).
       - Si entra nuevo inventario al almacén (proveedor) o si se realiza un reabastecimiento o retiro definitivo de stock (por mermas o inventario físico), utiliza 'updateStock' con el delta correspondiente (positivo para sumar, negativo para restar).
       - NUNCA inventes números de stock. Si un producto no tiene stock libre para la venta, avísale con amabilidad y ofrece opciones similares de nuestro catálogo.

    Tu tono es ejecutivo, profesional, pero alegre y servicial cuando interactúas con clientes que desean comprar. Siempre confirma los montos y categorías registrados."""

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
                tools=final_tools if (target_model == self.MODEL_LOGICA and len(final_tools) > 0) else None,
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