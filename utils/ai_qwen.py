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
                        "product_id": {"type": "integer", "description": "ID numérico exacto del producto a añadir."},
                        "quantity": {"type": "integer", "description": "Cantidad de unidades. Por defecto es 1."}
                    },
                    "required": ["product_id"]
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
                        "product_id": {"type": "integer", "description": "ID numérico del producto a actualizar o eliminar."},
                        "quantity": {"type": "integer", "description": "Nueva cantidad total o unidades a sumar. Para eliminar por completo o restar a 0, usa 0 o la acción correspondiente."},
                        "action": {"type": "string", "enum": ["add", "set", "remove"], "description": "Acción: 'add' para sumar unidades, 'set' para fijar una cantidad exacta (ej. 'mejor solo 1'), o 'remove' para quitar el producto por completo."}
                    },
                    "required": ["product_id", "quantity", "action"]
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

        # -- HERRAMIENTA 5 - GESTIÓN DE CONTABILIDAD --
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

        # HERRAMIENTA 7 - WEB SCRAPING
        {
            # Le enseñamos a la IA qué parámetros necesita para buscar en internet
            "type": "function",
            "function": {
                "name": "scrapeWebsite",
                "description": "Extrae el texto y contenido de una página web autorizada. Úsalo para buscar documentación, especificaciones técnicas o leer artículos a pedido del usuario.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL de la página web a raspar."
                        }
                    },
                    "required": ["url"]
                }
            }
        },

        # -- HERRAMIENTA 8 - GESTIÓN DE INVENTARIO --
        {
            "type": "function",
            "function": {
                "name": "searchProduct",
                "description": "Busca productos por nombre o palabra clave y devuelve coincidencias reales con sus IDs exactos. Debe usarse antes de consultar o actualizar inventario.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Nombre o palabra clave del producto a buscar."
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
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
            "type": "function",
            "function": {
                "name": "reserveStock",
                "description": "Bloquea temporalmente stock por el tiempo exacto configurado por el servidor. La IA NO debe inventar ni asumir minutos. Solo debe usar el tiempo devuelto por la herramienta en la respuesta.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "integer", "description": "El ID único del producto a reservar."},
                        "quantity": {"type": "integer", "description": "La cantidad de unidades a bloquear temporalmente."},
                        "minutes": {"type": "integer", "description": "Tiempo opcional solicitado. El servidor puede ignorarlo y usar el valor configurado internamente."}
                    },
                    "required": ["product_id", "quantity"]
                }
            }
        },
        {
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

        # -- HERRAMIENTA 11 - GESTIÓN DE REPORTES Y ANALÍTICA --
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
        },
        # -- HERRAMIENTAS DE SOPORTE (FASE 4) --
        {
            "type": "function",
            "function": {
                "name": "createSupportTicket",
                "description": "Crea un nuevo ticket de soporte técnico. Úsalo cuando un usuario reporte un problema, queja o solicite ayuda que no puedas resolver directamente. Siempre debes pedir nombre y email antes de crearlo.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string", "description": "Asunto breve del problema."},
                        "description": {"type": "string", "description": "Descripción detallada del problema."},
                        "priority": {
                            "type": "string",
                            "enum": ["baja", "media", "alta", "critica"],
                            "description": "Prioridad del problema. Usa 'alta' o 'critica' para problemas urgentes, pagos o errores graves."
                        },
                        "contact_name": {"type": "string", "description": "Nombre del cliente."},
                        "contact_email": {"type": "string", "description": "Correo electrónico del cliente."}
                    },
                    "required": ["subject", "description", "priority", "contact_name", "contact_email"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "getTicketStatus",
                "description": "Consulta el estado actual de un ticket de soporte previamente creado usando su ID numérico (no el código TKT, solo el número).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticket_id": {"type": "integer", "description": "ID numérico del ticket (ej: si es TKT-0042, el ID es 42)."}
                    },
                    "required": ["ticket_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "addComment",
                "description": "Añade información adicional o un nuevo comentario a un ticket de soporte existente.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticket_id": {"type": "integer", "description": "ID numérico del ticket."},
                        "comment": {"type": "string", "description": "El comentario o actualización a añadir."}
                    },
                    "required": ["ticket_id", "comment"]
                }
            }
        },

        # -- HERRAMIENTA 13: ASISTENTE PERSONAL Y AGENDA --
        {
            "type": "function",
            "function": {
                "name": "createReminder",
                "description": "Crea un recordatorio o agenda una tarea para el administrador. Úsalo cuando te pidan recordar algo.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Descripción de la tarea (ej: 'Llamar al proveedor')."},
                        "datetime": {"type": "string", "description": "Fecha y hora en formato YYYY-MM-DDTHH:MM:SS."}
                    },
                    "required": ["text", "datetime"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "listTodayReminders",
                "description": "Obtiene los recordatorios y tareas pendientes o atrasadas. Úsalo cuando el usuario pregunte por su agenda de hoy.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "markDone",
                "description": "Marca una tarea o recordatorio como completado usando su ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reminderId": {"type": "integer", "description": "ID numérico de la tarea."}
                    },
                    "required": ["reminderId"]
                }
            }
        },
        # -- HERRAMIENTA 14: COMUNICACIONES Y CORREOS --
        {
            "type": "function",
            "function": {
                "name": "sendEmail",
                "description": "Envía un correo electrónico a un cliente usando plantillas predefinidas. IMPORTANTE: Los parámetros deben ser cadenas de texto cortas y simples. NO incluyas bloques largos de texto ni HTML.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Correo electrónico del destinatario."},
                        "subject": {"type": "string", "description": "Asunto del correo (máximo 80 caracteres)."},
                        "template_name": {
                            "type": "string", 
                            "enum": ["general.html", "seguimiento.html", "encuesta.html"],
                            "description": "Plantilla a utilizar: 'seguimiento.html' para post-venta, 'encuesta.html' para satisfacción, 'general.html' para correos libres."
                        },
                        "nombre_cliente": {"type": "string", "description": "Nombre del cliente destinatario."},
                        "nombre_producto": {"type": "string", "description": "Nombre del producto comprado (opcional, dejar vacío si no aplica)."},
                        "body_content": {"type": "string", "description": "Texto breve del cuerpo del correo (solo para plantilla general.html). Máximo 500 caracteres. Puede usar Markdown simple como **negrita**."}
                    },
                    "required": ["to", "subject", "template_name", "nombre_cliente"]
                }
            }
        }
    ]

    # Prompt activo del Orquestador Central optimizado para autonomía de IA.
    #Este PROMPT es utilizado por la IA en el archivo routes/ai.py.
    SYSTEM_PROMPT = """Eres el Orquestador Central de esta tienda virtual. Actúas dinámicamente como Asistente de Ventas, Especialista de Soporte, Gestor de Inventario y Analista de Business Intelligence (BI) Senior, adaptándote a la intención del usuario.

=== ⚙️ REGLAS DE ORO Y COMPORTAMIENTO (CRÍTICO) ===
1. CERO ALUCINACIONES: NUNCA inventes nombres de productos, precios, existencias, datos financieros, ni métricas. Si necesitas información que no tienes, DEBES usar tus herramientas para consultar la base de datos real.
2. AUTONOMÍA DE HERRAMIENTAS: Tienes un catálogo de herramientas con descripciones claras. Decide inteligentemente cuál usar según la petición. Puedes ejecutar herramientas de forma secuencial (ej. buscar un producto en catálogo -> luego reservar su stock -> luego crear la orden).
3. REPORTES BI Y ANALÍTICA: Cuando generes análisis o reportes financieros, formatea la información SIEMPRE en tablas Markdown profesionales, usa emojis (📈, 💰) y proporciona 2 o 3 recomendaciones estratégicas basadas en los datos reales devueltos por el servidor.
4. SOPORTE E INVESTIGACIÓN: Si debes investigar documentación externa, limítate a resumir los datos reales extraídos de las webs autorizadas.
5. BASE DE CONOCIMIENTOS (FAQ): Para consultas sobre soporte, políticas, garantías, devoluciones o envíos, primero revisa la base de conocimiento interna antes de responder. Basa tu respuesta únicamente en la información encontrada y, si no existe información suficiente, indica que un asesor humano continuará la atención.
6. ASISTENTE PERSONAL (AGENDA): Si un usuario que no es administrador solicita guardar o gestionar recordatorios personales, responde amablemente que no puedes realizar esa acción.

=== 📦 REGLAS CRÍTICAS DE INVENTARIO ===
1. Nunca inventes IDs, stock, tiempos, límites ni configuraciones del sistema. Usa únicamente datos reales devueltos por herramientas.
2. Diferencia siempre entre consultar información y ejecutar acciones que modifiquen datos.
3. Nunca repitas reservas o actualizaciones ya ejecutadas en la conversación sin confirmación explícita del usuario.
4. Si existen múltiples coincidencias de productos, solicita aclaración antes de continuar.
5. Verifica siempre la respuesta de las herramientas antes de informar éxito. Si success=false o existe error, informa el problema y detén la operación.
6. Nunca ejecutes herramientas de modificación únicamente para obtener información adicional o consultar configuraciones internas.

=== 🎫 REGLAS DE SOPORTE Y ESCALADO ===
REGLA ABSOLUTA — ORDEN ESTRICTO DE PASOS (NO SE PUEDE SALTEAR):
PASO 1 — DETECTAR: Si el usuario menciona palabras como "urgente", "error", "no puedo pagar", "queja", "me cobraron", "problema", O si has intentado resolver el problema más de 2 veces sin éxito, debes activar el protocolo de soporte.
PASO 2 — RECOPILAR DATOS (OBLIGATORIO ANTES DE CREAR EL TICKET): DEBES pedir el nombre completo y el correo electrónico del usuario. Usa un mensaje como: "Para abrir un ticket de soporte oficial, necesito tu nombre completo y correo electrónico. ¿Me los puedes indicar?". ESPERA la respuesta del usuario. NO crees el ticket todavía.
PASO 3 — CREAR EL TICKET: SOLAMENTE después de que el usuario te haya proporcionado su nombre y correo, ejecuta la herramienta createSupportTicket. NUNCA llames a createSupportTicket sin haber obtenido primero ambos datos (contact_name y contact_email) del usuario en el chat.
PASO 4 — CONFIRMAR: Una vez creado, informa siempre al usuario el número oficial (Ej: TKT-0042) para que pueda hacer seguimiento.
REGLA DE PRIORIDAD: Asigna 'alta' o 'critica' a problemas de pago, cobros duplicados o caídas del sistema. Asigna 'media' a consultas generales.

=== 📧 REGLAS DE COMUNICACIONES (ENVÍO DE CORREOS) ===
REGLA DE CONFIRMACIÓN (HUMAN-IN-THE-LOOP): NUNCA ejecutes la herramienta sendEmail por tu propia cuenta. Si el administrador te pide enviar un correo:
1. Redacta primero un borrador del correo en el chat.
2. Pregúntale al usuario explícitamente: "¿Estás de acuerdo con enviar este correo ahora?".
3. SOLAMENTE ejecuta la herramienta sendEmail si el usuario responde afirmativamente (ej: "sí", "envíalo", "ok").
=== ⚠️ SEGURIDAD Y CONTROL DE AUTORIZACIÓN ===
1. LÍMITES DE PERMISOS Y PRIVACIDAD: Si el usuario te pide una acción administrativa (ej. reportes financieros, métricas) y no posees la herramienta en tu catálogo, explícale de forma natural que no tienes acceso a esa información. IMPORTANTE: NUNCA menciones nombres de herramientas (ej. `listProducts`, `getSalesReport`), ni digas que "están bloqueadas", ni hables de "niveles de usuario" o "permisos". Simplemente discúlpate, dile que como asistente de ventas solo puedes ayudarle con sus compras, y ofrécele ayuda con el catálogo.
2. CONFIRMACIÓN DE ACCIONES CRÍTICAS: Si el servidor o una herramienta te devuelve un mensaje requiriendo confirmación de seguridad, detente inmediatamente. Pide la confirmación al usuario y no des por completado el flujo hasta que el sistema lo autorice.

Tu tono global es altamente profesional y transparente. Eres servicial y persuasivo con los clientes, pero estrictamente analítico, preciso y ejecutivo al tratar asuntos de finanzas o administración."""

    def __init__(self):
        # Configuración del cliente con el endpoint de Singapore (International)
        api_key = os.environ.get('DASHSCOPE_API_KEY')
        
        # FASE 4: Validación de seguridad de la API Key para evitar excepciones no controladas.
        if not api_key or len(api_key) < 10 or not api_key.startswith('sk-'):
            raise ValueError("DASHSCOPE_API_KEY no configurada o inválida en las variables de entorno.")
            
        # FASE 7: Política de reintentos y Timeout explícito (Previene bloqueo indefinido del servidor)
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            timeout=30.0,
            max_retries=2
        )

    def get_response(self, prompt, model=None, system_instruction=None, history=None, tools=None, faq_context=""):
        """Envía consulta a la IA con protección total (Try-Catch) y
        Base de Conocimiento inyectada desde el contexto de la ruta (evita error app_context en hilos)."""
        if not self.client: return "Error: API KEY no configurada."

        try:
            # 1. Configuración de mensajes base
            base_prompt = system_instruction if system_instruction else self.SYSTEM_PROMPT
            
            # Inyectamos el FAQ al final del prompt para que Qwen lo lea.
            # El faq_context ya viene pre-construido desde routes/ai.py (dentro del contexto Flask correcto).
            sys_msg = f"""{base_prompt}
            === BASE DE CONOCIMIENTO INTERNA (FAQ) ===
            Las siguientes son las politicas estrictas de la empresa.
            Úsalas siempre para responder dudas de clientes sobre estos temas:
            {faq_context}
            """

            # 3. Construcción de mensajes con historial
            messages = [{"role": "system", "content": sys_msg}]
            if history: messages.extend(history)
            if prompt: messages.append({"role": "user", "content": prompt})

            # 4. Selección de modelo y herramientas
            target_model = model if model else self.MODEL_LOGICA
            final_tools = tools if tools is not None else self.TOOLS

            extra_params = {}
            # FASE 8: Listado dinámico para modelos que soportan razonamiento (Thinking Models)
            thinking_models = os.environ.get('THINKING_MODELS', 'qwen-max').split(',')
            if target_model in [m.strip() for m in thinking_models]:
                extra_params["extra_body"] = {"enable_thinking": True}

            # 5. Llamada a la API
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

    def get_stream_response(self, prompt, model=None, system_instruction=None, history=None, tools=None, faq_context=""):
        """Versión generadora de get_response que soporta SSE (streaming).
        Hace 'yield' de cada fragmento (chunk) a medida que llega desde Qwen,
        y al final emite un diccionario con el resultado ensamblado completo."""
        if not self.client:
            yield {"type": "error", "content": "Error: API KEY no configurada."}
            return

        try:
            base_prompt = system_instruction if system_instruction else self.SYSTEM_PROMPT
            sys_msg = f"""{base_prompt}
            === BASE DE CONOCIMIENTO INTERNA (FAQ) ===
            Las siguientes son las politicas estrictas de la empresa.
            Úsalas siempre para responder dudas de clientes sobre estos temas:
            {faq_context}
            """

            messages = [{"role": "system", "content": sys_msg}]
            if history: messages.extend(history)
            if prompt: messages.append({"role": "user", "content": prompt})

            target_model = model if model else self.MODEL_LOGICA
            final_tools = tools if tools is not None else self.TOOLS

            extra_params = {}
            thinking_models = os.environ.get('THINKING_MODELS', 'qwen-max').split(',')
            if target_model in [m.strip() for m in thinking_models]:
                extra_params["extra_body"] = {"enable_thinking": True}

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
                
                # Capturar y emitir razonamiento (Streaming)
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    full_reasoning += delta.reasoning_content
                    yield {"type": "reasoning", "content": delta.reasoning_content}
                
                # Capturar y emitir contenido (Streaming)
                if delta.content: 
                    full_content += delta.content
                    yield {"type": "content", "content": delta.content}
                
                # Capturar herramientas (Sin emitir fragmentos por seguridad)
                if delta.tool_calls:
                    for tc_chunk in delta.tool_calls:
                        if len(tool_calls) <= tc_chunk.index:
                            tool_calls.append({
                                "id": tc_chunk.id, "type": "function",
                                "function": {"name": tc_chunk.function.name, "arguments": ""}
                            })
                        if tc_chunk.function.arguments:
                            tool_calls[tc_chunk.index]["function"]["arguments"] += tc_chunk.function.arguments
            
            # Emitir resultado final ensamblado para compatibilidad con el bucle ReAct
            yield {
                "type": "final",
                "result": {
                    "content": full_content if full_content else None,
                    "reasoning": full_reasoning if full_reasoning else None,
                    "tool_calls": tool_calls if tool_calls else None
                }
            }
        except Exception as e:
            yield {"type": "error", "content": f"Error Qwen: {str(e)}"}

# Instancia global del servicio
qwen_service = QwenAIService()