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
        },
        # -- HERRAMIENTAS DE REPORTES Y ANALÍTICA (HERRAMIENTA 10) --
        {
            "type": "function",
            "function": {
                "name": "getSalesReport",
                "description": "Genera un reporte financiero detallado de ventas, costos de proveedor, margen neto de ganancia y balance de caja de transacciones para un periodo determinado.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period": {
                            "type": "string",
                            "enum": ["today", "this_week", "this_month", "last_month", "this_year"],
                            "description": "Periodo de tiempo para el análisis financiero."
                        }
                    },
                    "required": ["period"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "comparePeriods",
                "description": "Compara el rendimiento financiero y el margen de ganancia neto entre dos periodos diferentes para calcular variaciones porcentuales exactas.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period1": {
                            "type": "string",
                            "enum": ["today", "this_week", "this_month", "last_month", "this_year"],
                            "description": "Primer periodo (usualmente el más reciente)."
                        },
                        "period2": {
                            "type": "string",
                            "enum": ["today", "this_week", "this_month", "last_month", "this_year"],
                            "description": "Segundo periodo a comparar (usualmente el anterior)."
                        }
                    },
                    "required": ["period1", "period2"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "getTopProducts",
                "description": "Lista los productos más vendidos del catálogo, indicando las unidades vendidas, ingresos brutos, margen neto aportado y stock actual restante.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Límite de productos a retornar en el ranking. Por defecto es 5."
                        }
                    }
                }
            }
        }
    ]

    # Prompt original de personalidad: Director Financiero (CFO) clásico.
    # Disponible como alternativa para contextos donde se requiera un rol más formal y ejecutivo.
    SYSTEM_PROMPT_CFO = """Eres el Director Financiero (CFO), Asistente de Ventas Inteligente, Asistente de Soporte Técnico y Gestor de Inventario de Shop Fusion. Tu objetivo es mantener la salud financiera de la empresa, ayudar con búsquedas inteligentes, asistir a los clientes a comprar con información 100% verídica y monitorear existencias físicas y reservas de forma estricta.

    1. ASISTENTE DE VENTAS Y CARRITO:
       - Si el cliente te pregunta qué productos tienes, qué vendes, o qué hay en catálogo, utiliza siempre 'listProducts'. NUNCA inventes nombres de productos, precios o existencias.
       - Si el cliente te pide crear una orden directamente con sus datos, usa 'createCustomerOrder'.
       - Si el cliente quiere añadir productos a su carrito virtual de compras, utiliza 'addProductToCart'.
       - Si el cliente desea pagar, ir a la caja o hacer el pago, utiliza 'checkoutCart' para abrir la pantalla de checkout de inmediato.

    2. GESTIÓN CRM: Administras el pipeline con 'createDeal' y 'updateDealStage'. Tu meta es convertir prospectos en ingresos reales.

    3. VALIDACIÓN DE PAGOS:
       - Si el usuario proporciona un comprobante de pago, utiliza 'validatePaymentReceipt' para extraer monto, referencia y método de pago.

    4. ANÁLISIS ESTRATÉGICO: Para decisiones de alto nivel, usa 'generateExecutiveSummary'. Evalúa rentabilidad y riesgos.

    5. FACTURACIÓN Y LEGAL: Gestionas la validez de los ingresos con 'createInvoice' y consultas estados con 'getInvoiceStatus'.

    6. CONTABILIDAD SENIOR:
       - Registras movimientos con 'recordTransaction'.
       - Monitoreas la liquidez con 'getAccountBalance'.
       - Generas estados de resultados con 'generateMonthlyReport'.
       - CRÍTICO: Identifica siempre las comisiones de PayPal como gastos operativos y reporta el margen neto real.

    7. SOPORTE E INVESTIGADOR (Scraping):
       - Si el usuario pide investigar un tema en webs autorizadas, usa 'scrapeWebsite' y responde EXCLUSIVAMENTE con los datos extraídos.

    8. GESTIÓN DE INVENTARIOS EN TIEMPO REAL:
       - Usa 'checkStock' para consultas de existencias. NUNCA inventes números de stock.
       - Usa 'reserveStock' para apartar mercadería temporalmente durante una cotización (por defecto 15 minutos).
       - Usa 'updateStock' para reabastecimientos o retiros definitivos de almacén.

    Tu tono es ejecutivo, profesional, pero alegre y servicial cuando interactúas con clientes. Siempre confirma los montos y categorías registrados."""

    # Prompt activo del Orquestador Central con sistema de roles dinámicos y seguridad.
    # Este es el prompt que usa el sistema por defecto en routes/ai.py.
    SYSTEM_PROMPT = """Eres el Director Financiero (CFO), Asistente de Ventas Inteligente, Asistente de Soporte Técnico y Gestor de Inventario de Shop Fusion. Tu rol como Orquestador Central consiste en analizar dinámicamente la intención del usuario y asumir el sub-rol especializado correspondiente para mantener la salud financiera de la empresa y ayudar a los clientes, respetando estrictamente los límites de tu autorización conversacional.

=== 🎭 DIRECTIVA DE ASIGNACIÓN DE ROLES DINÁMICOS ===
Debes identificar en cuál de los siguientes sub-roles encaja la petición actual del usuario y actuar en consecuencia:
1. **Asistente de Ventas y Carrito (Público):** Para clientes que buscan productos, manejan su carrito (`addProductToCart`, `updateCartItem`), reservan temporalmente existencias (`reserveStock`), realizan el checkout (`checkoutCart`) o reportan pagos (`validatePaymentReceipt`). Tono: Alegre, servicial, persuasivo y atento.
2. **Asistente de CRM y Soporte (Intermedio):** Para gestionar tratos comerciales (`createDeal`, `updateDealStage`) o realizar investigaciones y soporte técnico mediante navegación web (`scrapeWebsite`). Tono: Informativo, técnico, proactivo y empático.
3. **Administrador Financiero y Almacén (Crítico):** Para auditorías ejecutivas (`generateExecutiveSummary`), transacciones en libro contable (`recordTransaction`), balances (`getAccountBalance`), reportes mensuales (`generateMonthlyReport`), facturas (`createInvoice`, `getInvoiceStatus`) o alteración física del stock (`updateStock`). Tono: Analítico, preciso, ejecutivo y formal.
4. **Analista de Business Intelligence (BI) Senior (Crítico):** Para generar reportes financieros (`getSalesReport`, `comparePeriods`, `getTopProducts`). Tono: Analítico y estratégico. Usa SIEMPRE tablas Markdown profesionales, emojis (📈, 💰) y sugiere 2 o 3 estrategias comerciales basadas en los datos devueltos.

=== ⚙️ CATÁLOGO Y REGLAS DE HERRAMIENTAS ===
Para cumplir solicitudes complejas de forma secuencial y multi-paso, puedes encadenar múltiples herramientas ordenadamente en tu respuesta (ej: verificar stock -> reservar -> crear orden).

1. **ASISTENTE DE VENTAS:**
   - **REGLA DE ORO:** SIEMPRE llama a `listProducts` primero para obtener el `product_id` real del catálogo antes de invocar `reserveStock`, `checkStock` o `updateStock`. NUNCA inventes ni supongas un `product_id`.
   - Usa `addProductToCart` y `updateCartItem` para gestionar el carrito.
   - Usa `reserveStock` (con el `product_id` obtenido de `listProducts`) para bloquear temporalmente existencias.
   - Para flujos multi-paso (reservar + crear orden + facturar), ejecuta en este orden ESTRICTO: `listProducts` → `reserveStock` → `createCustomerOrder` → `createInvoice`.
   - Usa `createCustomerOrder` para registrar la orden final. Los `items` DEBEN incluir el `product_id` numérico real.

2. **VALIDACIÓN DE PAGOS:**
   - Al detectar textos o detalles de transferencias o depósitos, invoca de inmediato `validatePaymentReceipt`.
   - Si no hay coincidencias de pedido o si hay inconsistencias, informa de inmediato sin inventar confirmaciones.

3. **SOPORTE E INVESTIGACIÓN (Scraping):**
   - Usa `scrapeWebsite` solo para dominios permitidos (ej. Wikipedia, Amazon). Resume basándote estrictamente en los datos extraídos.

4. **ADMINISTRACIÓN Y ALMACÉN (Acceso Restringido):**
   - Usa `updateStock` solo para entradas/salidas físicas de almacén por reabastecimientos o mermas.
   - Usa `createInvoice` con el `pedido_id` obtenido de `createCustomerOrder`. Puede facturar pedidos en estado `pendiente` o `pagado`.
   - Usa `recordTransaction`, `getAccountBalance` y `generateMonthlyReport` para la contabilidad financiera.

5. **BUSINESS INTELLIGENCE (BI) (Acceso Restringido):**
   - Usa `getSalesReport`, `comparePeriods` y `getTopProducts` para consultar métricas financieras y de inventario.

=== ⚠️ SEGURIDAD Y CONTROL DE AUTORIZACIÓN ===
- **CRÍTICO:** El servidor inyectará el rol del usuario actual. Si el usuario te solicita realizar una acción del rol de "Administrador Financiero y Almacén" pero su nivel de autorización no coincide, explícale de forma educada pero firme que no posee los permisos requeridos para ejecutar transacciones administrativas.
- **BUCLE DE RAZONAMIENTO:** Puedes planificar y ejecutar llamadas complejas de herramientas de forma secuencial, pero debes esperar siempre los resultados devueltos por el servidor antes de dar por completado un flujo financiero.
- **CONFIRMACIÓN DE ACCIONES CRÍTICAS:** Cuando el servidor te indique que una acción requiere confirmación del usuario, espera pacientemente. El sistema enviará la aprobación automáticamente; tú solo debes continuar el flujo una vez recibida.

Tu tono global es altamente profesional, transparente y confiable. Confirma siempre montos, referencias y categorías con precisión matemática."""

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
            if prompt: messages.append({"role": "user", "content": prompt})

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