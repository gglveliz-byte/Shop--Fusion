from sqlalchemy.engine import result
import json
from flask import Blueprint, request, jsonify, render_template, current_app, redirect, url_for, flash, session
from flask_login import current_user
from utils.ai_qwen import qwen_service
from utils.rate_limit import limiter
from utils.orders import create_order_from_json
import re

def extract_payment_data(text):
    """Extract payment fields from free-form text using advanced regex and NLP matching.
    Returns a dict with keys: metodo_pago, pago_referencia, monto, fecha (optional).
    """
    if not text:
        return None
        
    data = {}
    text_lower = text.lower()
    
    # 1. Determinar Método de Pago de manera flexible
    if "paypal" in text_lower:
        data["metodo_pago"] = "paypal"
    elif any(word in text_lower for word in ["transferencia", "banco", "deposito", "depósito", "bancaria", "transfer", "pichincha", "guayaquil", "produbanco", "pacifico", "pacífico", "bolivariano", "cooperativa"]):
        data["metodo_pago"] = "transferencia"
    else:
        # Fallback a regex
        match_metodo = re.search(r"(?i)metodo[:\s]+(transferencia|paypal)", text)
        if match_metodo:
            data["metodo_pago"] = match_metodo.group(1).lower()

    # 2. Extraer Referencia
    # Busca palabras clave en español de comprobantes seguidas por un código alfanumérico
    match_ref = re.search(r"(?i)(?:referencia|ref|comprobante|transaccion|transacción|tx|hash|codigo|código|nro|numero|número|operacion|operación)\s*(?:de)?\s*[:#\s-]*\s*([A-Za-z0-9\-]+)", text)
    if match_ref:
        data["pago_referencia"] = match_ref.group(1)
    
    # 3. Extraer Monto
    # Captura montos precedidos por $, total, monto, valor, etc.
    match_monto = re.search(r"(?i)(?:monto|total|valor|precio|cantidad|\$)\s*(?:de)?\s*[:$#\s]*\s*([0-9]+(?:[.,][0-9]{1,2})?)", text)
    if match_monto:
        monto_str = match_monto.group(1).replace(",", ".") # Reemplazar coma decimal por punto
        data["monto"] = monto_str

    # 4. Extraer Fecha (opcional)
    match_fecha = re.search(r"(?i)fecha[:\s-]*(\d{4}[-/\s]\d{2}[-/\s]\d{2}|\d{2}[-/\s]\d{2}[-/\s]\d{4})", text)
    if match_fecha:
        data["fecha"] = match_fecha.group(1)

    return data if data else None

bp = Blueprint('ai', __name__, url_prefix='/ai')

@bp.route('/interfaz')
def interface():
    """Renderiza la página dedicada del chatbot."""
    return render_template('ai/chat_page.html')

@bp.route('/chat', methods=['POST'])
@limiter.limit("10 per minute")
def chat():
    """Endpoint para procesar mensajes del chatbot con soporte para Ventas, CRM y Facturación."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No hay datos en la solicitud"}), 400

    # Intentar extraer datos de pago del mensaje libre
    mensaje_raw = data.get('message')
    payment_info = extract_payment_data(mensaje_raw) if mensaje_raw else None
    if payment_info and all(k in payment_info for k in ["metodo_pago", "pago_referencia", "monto"]):
        # Simular llamada a la herramienta validatePaymentReceipt
        from models import Pedido, db
        from datetime import datetime
        referencia = payment_info["pago_referencia"]
        duplicado = Pedido.query.filter_by(pago_referencia=referencia).first()
        if duplicado:
            return jsonify({"error": f"La referencia de pago '{referencia}' ya está registrada en el pedido #{duplicado.id}."}), 400
        # Buscar pedido pendiente por monto
        try:
            monto_valor = float(payment_info["monto"])
        except ValueError:
            return jsonify({"error": "Monto inválido en los datos de pago."}), 400
        pedido = (
            Pedido.query.filter(Pedido.estado == "pendiente")
            .filter(Pedido.total >= monto_valor - 0.01)
            .filter(Pedido.total <= monto_valor + 0.01)
            .first()
        )
        if not pedido:
            return jsonify({"message": "No se encontró pedido pendiente que coincida con el monto. Se guardó la información del pago para revisión."}), 200
        # Conciliar
        pedido.metodo_pago = payment_info["metodo_pago"]
        pedido.pago_referencia = referencia
        pedido.pagado_en = datetime.utcnow()
        pedido.estado = "pagado"
        db.session.commit()
        # Generar factura y registro contable (reuse existing logic)
        try:
            from utils.billing import calculate_invoice_data
            from models import Factura
            datos = calculate_invoice_data(pedido)
            nueva_f = Factura(
                numero_factura=Factura.generar_numero_correlativo(),
                pedido_id=pedido.id,
                subtotal=datos['subtotal'],
                iva_porcentaje=datos['iva_porcentaje'],
                iva_monto=datos['iva_monto'],
                total=datos['total']
            )
            db.session.add(nueva_f)
            db.session.commit()
            from utils.accounting import register_transaction
            register_transaction(
                tipo='ingreso',
                monto=float(nueva_f.total),
                categoria='venta',
                fuente='caja',
                descripcion=f"Ingreso automático por factura {nueva_f.numero_factura}",
                referencia_id=f"FAC-{nueva_f.id}"
            )
            return jsonify({
                "success": True,
                "pedido_id": pedido.id,
                "factura_id": nueva_f.id,
                "mensaje": f"Pedido #{pedido.id} marcado como pagado y factura {nueva_f.numero_factura} generada."
            }), 200
        except Exception as e:
            return jsonify({"error": f"Error al generar factura: {str(e)}"}), 500
    # Si no es datos de pago estructurados, continuar con flujo normal
    mensaje = data.get('message')
    modelo = data.get('model', 'qwen-plus')
    historial = data.get('history', [])
    
    if not mensaje:
        return jsonify({"error": "El mensaje es obligatorio"}), 400
    
    # 1. Determinar qué herramientas puede usar este usuario (Permisos)
    es_admin = hasattr(current_user, 'username')
    
    herramientas_disponibles = qwen_service.TOOLS
    system_msg = qwen_service.SYSTEM_PROMPT

    if not es_admin:
        # Si no es admin, permitimos herramientas de compra, carrito y catálogo
        herramientas_permitidas = ['createCustomerOrder', 'addProductToCart', 'updateCartItem', 'checkoutCart', 'listProducts', 'validatePaymentReceipt', 'createSupportTicket', 'getTicketStatus', 'addComment']
        herramientas_disponibles = [t for t in qwen_service.TOOLS if t['function']['name'] in herramientas_permitidas]
        print("DEBUG: Usuario no-admin detectado. Habilitando herramientas de compra y carrito.")
        
        # Inyección de contexto para evitar "alucinaciones" de la IA
        system_msg += (
            "\n\nAVISO CRÍTICO DE SEGURIDAD: El usuario actual NO es Administrador. "
            "Para esta conversación se te han bloqueado temporalmente las herramientas de CRM, Contabilidad y Facturación. "
            "Si el usuario te pide crear negocios, facturar o tareas financieras, no intentes procesarlo. "
            "Simplemente responde de forma muy educada que no cuentan con los permisos necesarios para realizar esa acción."
        )

    # Protección anti-alucinación de parámetros en el historial
    system_msg += (
        "\n\nREGLA ESTRICTA PARA HERRAMIENTAS: Cada vez que uses una herramienta, DEBES extraer los parámetros "
        "(montos, categorías, nombres, etc.) ÚNICAMENTE del último mensaje enviado por el usuario. "
        "NUNCA reutilices ni dupliques los datos de transacciones u operaciones pasadas que estén en tu historial."
    )

    # 2. Bucle de Razonamiento (ReAct) Multistep
    max_iteraciones = 3
    iteracion_actual = 0
    prompt_actual = mensaje
    historial_bucle = list(historial) if historial else []
    
    db_results_totales = []
    respuesta_final = ""
    reasoning_final = ""
    modelo_actual = modelo
    ejecucion_directa = False  # Bandera: True cuando se ejecutan herramientas confirmadas
    
    while iteracion_actual < max_iteraciones:
        iteracion_actual += 1

        # --- ATAJO: Si el mensaje es una confirmación de acción crítica, ejecutar directamente ---
        if prompt_actual.startswith("[SISTEMA_CONFIRMA]"):
            token = prompt_actual.replace("[SISTEMA_CONFIRMA]", "").strip()
            pending_calls = None
            try:
                from itsdangerous import URLSafeSerializer, BadSignature
                from flask import current_app
                if current_app.config.get('SECRET_KEY'):
                    s = URLSafeSerializer(current_app.config['SECRET_KEY'])
                    decoded = s.loads(token)
                    pending_calls = decoded.get("tool_calls")
                else:
                    decoded = json.loads(token)
                    pending_calls = decoded.get("tool_calls")
            except Exception:
                pending_calls = None

            if pending_calls:
                # Construir un resultado simulado con las tool_calls pendientes y saltarse la IA
                result = {
                    "content": "",
                    "reasoning": "",
                    "tool_calls": pending_calls
                }
                prompt_actual = ""  # Limpiar el prompt de confirmación
                ejecucion_directa = True  # Marcar: el lote está pre-autorizado, no re-bloquear
                if True:  # bloque de ejecución directa
                    pass  # La lógica de herramientas sigue debajo normalmente
            else:
                # Token inválido o sin tool_calls, dejar que la IA responda
                prompt_actual = "El usuario aprobó la acción crítica. Continúa con el flujo."
                result = qwen_service.get_response(
                    prompt_actual,
                    model=modelo_actual,
                    history=historial_bucle,
                    tools=herramientas_disponibles,
                    system_instruction=system_msg
                )
                if isinstance(result, str):
                    return jsonify({"error": result}), 500
        else:
            # Llamada normal a la IA
            result = qwen_service.get_response(
                prompt_actual,
                model=modelo_actual,
                history=historial_bucle,
                tools=herramientas_disponibles,
                system_instruction=system_msg
            )
            if isinstance(result, str):
                return jsonify({"error": result}), 500
        
        # Acumular respuesta de texto si existe
        if result.get("content"):
            respuesta_final += result.get("content") + "\n"
        if result.get("reasoning"):
            reasoning_final += result.get("reasoning") + "\n"

        # Si NO hay llamadas a herramientas, la IA ha completado la tarea
        if not result.get("tool_calls"):
            break

        # 3. Procesar llamadas a herramientas (Tool Calls)
        system_msgs = []
        target_model = modelo_actual

        # --- PRE-VALIDACIÓN (FASE 3) ---
        # Primero revisamos si hay alguna acción crítica bloqueante en todo el batch
        ACCIONES_CRITICAS = ["updateStock", "recordTransaction", "createInvoice"]
        
        for tool_call in result["tool_calls"][:3]:
            func_name = tool_call["function"]["name"]
            args_str = tool_call["function"]["arguments"]
            try:
                args = json.loads(args_str)
            except:
                if not args_str.strip().endswith("}"): args_str += "}"
                try: args = json.loads(args_str)
                except: continue

            es_confirmada = False
            if prompt_actual.startswith("[SISTEMA_CONFIRMA]"):
                token = prompt_actual.replace("[SISTEMA_CONFIRMA]", "").strip()
                from itsdangerous import URLSafeSerializer, BadSignature
                from flask import current_app
                if current_app.config.get('SECRET_KEY'):
                    s = URLSafeSerializer(current_app.config['SECRET_KEY'])
                    try:
                        conf_data = s.loads(token)
                        if conf_data.get("func_name") == func_name and conf_data.get("args") == args:
                            es_confirmada = True
                    except BadSignature:
                        pass
                else:
                    try:
                        conf_data = json.loads(token)
                        if conf_data.get("func_name") == func_name: es_confirmada = True
                    except: pass

            if func_name in ACCIONES_CRITICAS and not es_confirmada and not ejecucion_directa:
                # Se detiene la ejecución y firma el token con TODAS las tool_calls pendientes del turno
                from itsdangerous import URLSafeSerializer
                from flask import current_app
                token_str = ""
                all_pending = []
                for tc in result["tool_calls"][:3]:
                    all_pending.append({
                        "id": tc.get("id"),
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"]
                        }
                    })
                payload = {"func_name": func_name, "args": args, "tool_calls": all_pending}
                if current_app.config.get('SECRET_KEY'):
                    s = URLSafeSerializer(current_app.config['SECRET_KEY'])
                    token_str = s.dumps(payload)
                else:
                    token_str = json.dumps(payload)

                # Abortamos de inmediato y pedimos confirmación antes de ejecutar CUALQUIER herramienta
                return jsonify({
                    "status": "requires_confirmation",
                    "response": f"⚠️ **Acción de Seguridad Requerida**\nEl asistente intentó ejecutar una operación crítica:\n- Acción: `{func_name}`\n\nPor seguridad, por favor confirma si deseas proceder.",
                    "pending_action": {
                        "func_name": func_name,
                        "args": args,
                        "token": token_str
                    },
                    "model": modelo_actual
                })

        # --- EJECUCIÓN (Si no hay acciones críticas o ya están confirmadas) ---
        for tool_call in result["tool_calls"][:3]:
            func_name = tool_call["function"]["name"]
            args_str = tool_call["function"]["arguments"]
            
            try:
                args = json.loads(args_str)
            except json.JSONDecodeError:
                if not args_str.strip().endswith("}"): args_str += "}"
                try:
                    args = json.loads(args_str)
                except:
                    continue

            db_res = None

            # --- Lógica de Ventas ---
            if func_name == "createCustomerOrder":
                order_data = {
                    'cliente_nombre': args.get('customer_name'),
                    'cliente_telefono': args.get('customer_phone'),
                    'cliente_direccion': args.get('customer_address'),
                    'productos': [{'id': p['product_id'], 'cantidad': p['quantity']} for p in args.get('items', [])]
                }
                db_res = create_order_from_json(order_data)
                system_msgs.append(f"El sistema ejecutó la orden. Resultado: {json.dumps(db_res)}.")

            # --- Lógica de Scraping / Soporte ---
            elif func_name == "scrapeWebsite":
                # Paso 3.3: Conectar la IA con el Scraper
                from utils.scraper import scrape_webpage
                db_res = scrape_webpage(url=args.get('url'), selector=args.get('selector'))
                
                if db_res.get('success'):
                    # Le pasamos el texto extraído a la IA para que lo lea y responda
                    system_msgs.append(
                        f"DATOS EXTRAÍDOS DE LA WEB: {db_res['data'][:4000]}\n\n"
                        "Por favor, lee esta información y responde a la pregunta del usuario usándola como tu ÚNICA fuente de la verdad."
                    )
                else:
                    # Si falló (ej. no está en lista blanca o cayó), le decimos a la IA que informe del error
                    system_msgs.append(f"ERROR AL LEER LA WEB: {db_res.get('error')}. Informa amablemente al usuario del problema.")

            # --- Lógica de Soporte Técnico (Fase 5) ---
            elif func_name == "createSupportTicket":
                from utils.support import create_ticket, escalate_ticket
                db_res = create_ticket(
                    subject=args.get('subject'),
                    description=args.get('description'),
                    priority=args.get('priority', 'media'),
                    contact_name=args.get('contact_name'),
                    contact_email=args.get('contact_email'),
                    canal='chat'
                )
                
                # Si se creó con éxito y la prioridad es alta/crítica, lo escalamos automáticamente
                if db_res.get('success') and args.get('priority') in ['alta', 'critica']:
                    esc_res = escalate_ticket(db_res['ticket_id'])
                    db_res['escalation'] = esc_res

                system_msgs.append(f"Ticket creado. Resultado: {json.dumps(db_res)}. Informa el número del ticket al usuario.")

            elif func_name == "getTicketStatus":
                from utils.support import get_ticket_status
                db_res = get_ticket_status(ticket_id=args.get('ticket_id'))
                system_msgs.append(f"Estado del ticket devuelto: {json.dumps(db_res)}. Resúmelo amablemente para el usuario.")

            elif func_name == "addComment":
                from utils.support import add_comment
                db_res = add_comment(
                    ticket_id=args.get('ticket_id'), 
                    content=args.get('comment'), 
                    author='ia'
                )
                system_msgs.append(f"Comentario añadido al ticket. Resultado: {json.dumps(db_res)}.")

            elif func_name == "sendEmail":
                # Sólo administradores pueden usar esta herramienta de envío libre
                if not es_admin:
                    db_res = {"success": False, "error": "Permiso denegado: solo administradores pueden enviar correos manuales."}
                    system_msgs.append(f"[SEGURIDAD] Intento de envío de email sin autorización: {json.dumps(db_res)}.")
                else:
                    from utils.communications import send_email
                    # Construir context a partir de parámetros planos (evita JSON malformado de Qwen)
                    context = {}
                    if args.get('nombre_cliente'):
                        context['nombre_cliente'] = args['nombre_cliente']
                    if args.get('nombre_producto'):
                        context['nombre_producto'] = args['nombre_producto']
                    if args.get('body_content'):
                        context['body_content'] = args['body_content']
                    
                    email_res = send_email(
                        to_email=args.get('to'),
                        subject=args.get('subject'),
                        template_name=args.get('template_name', 'general.html'),
                        context=context
                    )
                    db_res = email_res
                    system_msgs.append(f"Resultado envío email: {json.dumps(db_res)}.")
            elif func_name == "listProducts":
                from models import Producto
                category = args.get('category')
                query = Producto.query.filter(Producto.activo == True)
                if category:
                    query = query.filter(Producto.categoria.ilike(f"%{category}%"))
                productos = query.all()
                
                p_list = []
                for p in productos:
                    p_list.append({
                        "id": p.id,
                        "nombre": p.nombre,
                        "descripcion": p.descripcion,
                        "precio": float(p.precio_final),
                        "precio_oferta": float(p.precio_oferta) if p.precio_oferta else None,
                        "stock": p.stock
                    })
                db_res = {
                    "success": True,
                    "action": "listProducts",
                    "productos": p_list
                }
                system_msgs.append(f"Resultado de consulta de productos: {json.dumps(db_res)}.")

            # --- Lógica de Validación y Conciliación de Pago ---
            elif func_name == "validatePaymentReceipt":
                # args expected: metodo_pago, pago_referencia, monto, fecha (opcional)
                referencia = args.get("pago_referencia")
                # Verificar duplicado en la tabla pedidos
                from models import Pedido, db
                from datetime import datetime
                duplicado = Pedido.query.filter_by(pago_referencia=referencia).first()
                if duplicado:
                    db_res = {
                        "success": False,
                        "action": "validatePaymentReceipt",
                        "error": f"La referencia de pago '{referencia}' ya está registrada en el pedido #{duplicado.id}.",
                    }
                else:
                    # Buscar pedido pendiente cuyo total coincida (tolerancia 0.01)
                    monto = args.get("monto")
                    try:
                        monto_valor = float(monto)
                    except (TypeError, ValueError):
                        monto_valor = None
                    pedido = None
                    if monto_valor is not None:
                        pedido = (
                            Pedido.query.filter(Pedido.estado == "pendiente")
                            .filter(Pedido.total >= monto_valor - 0.01)
                            .filter(Pedido.total <= monto_valor + 0.01)
                            .first()
                        )
                    if pedido:
                        # Conciliar pago
                        pedido.metodo_pago = args.get("metodo_pago")
                        pedido.pago_referencia = referencia
                        pedido.pagado_en = datetime.utcnow()
                        pedido.estado = "pagado"
                        db.session.commit()
                        # Generar factura automáticamente
                        try:
                            from utils.billing import calculate_invoice_data
                            from models import Factura
                            datos = calculate_invoice_data(pedido)
                            nueva_f = Factura(
                                numero_factura=Factura.generar_numero_correlativo(),
                                pedido_id=pedido.id,
                                subtotal=datos['subtotal'],
                                iva_porcentaje=datos['iva_porcentaje'],
                                iva_monto=datos['iva_monto'],
                                total=datos['total']
                            )
                            db.session.add(nueva_f)
                            db.session.commit()
                            # Registro contable automático
                            from utils.accounting import register_transaction
                            register_transaction(
                                tipo='ingreso',
                                monto=float(nueva_f.total),
                                categoria='venta',
                                fuente='caja',
                                descripcion=f"Ingreso automático por factura {nueva_f.numero_factura}",
                                referencia_id=f"FAC-{nueva_f.id}"
                            )
                            db_res = {
                                "success": True,
                                "action": "validatePaymentReceipt",
                                "pedido_id": pedido.id,
                                "mensaje": f"Pedido #{pedido.id} marcado como pagado, factura {nueva_f.numero_factura} generada.",
                                "factura_id": nueva_f.id
                            }
                        except Exception as e:
                            db_res = {
                                "success": False,
                                "action": "validatePaymentReceipt",
                                "error": str(e)
                            }

                    else:
                        # No se encontró pedido coincidente, se guarda solo la info
                        db_res = {
                            "success": True,
                            "action": "validatePaymentReceipt",
                            "metodo_pago": args.get("metodo_pago"),
                            "pago_referencia": referencia,
                            "monto": monto,
                            "fecha": args.get("fecha"),
                        }
                system_msgs.append(f"Validación de comprobante: {json.dumps(db_res)}.")

            elif func_name == "addProductToCart":
                from models import Producto
                p_id = args.get('product_id')
                qty = args.get('quantity', 1) or 1
                
                producto = Producto.query.filter_by(id=p_id, activo=True).first() if p_id else None
                
                if not producto:
                    db_res = {
                        "success": False,
                        "action": "addProductToCart",
                        "error": f"Producto con ID '{p_id}' no encontrado o no disponible. Usa searchProduct primero."
                    }
                elif not producto.esta_disponible(qty):
                    stock_libre = producto.stock - producto.stock_reservado
                    db_res = {
                        "success": False,
                        "action": "addProductToCart",
                        "error": f"Stock insuficiente para '{producto.nombre}'. Solicitado: {qty}, Disponible real: {stock_libre}."
                    }
                else:
                    imagenes = producto.obtener_todas_imagenes()
                    imagen = imagenes[0] if imagenes else (producto.imagen or "")
                    db_res = {
                        "success": True,
                        "action": "addProductToCart",
                        "id": producto.id,
                        "nombre": producto.nombre,
                        "precio": float(producto.precio_venta()),
                        "imagen": imagen,
                        "cantidad": qty,
                        "mensaje": f"Agregado {qty}x '{producto.nombre}' al carrito."
                    }
                system_msgs.append(f"Resultado de agregar al carrito: {json.dumps(db_res)}.")

            elif func_name == "updateCartItem":
                from models import Producto
                p_id = args.get('product_id')
                qty = args.get('quantity', 1) or 0
                action_type = args.get('action', 'add')
                
                producto = Producto.query.filter_by(id=p_id, activo=True).first() if p_id else None
                
                if not producto:
                    db_res = {
                        "success": False,
                        "action": "updateCartItem",
                        "error": f"Producto con ID '{p_id}' no encontrado o no disponible. Usa searchProduct primero."
                    }
                else:
                    # Calcular la cantidad total acumulada para validar contra el stock
                    cant_a_validar = qty
                    if action_type == 'add':
                        from flask import session
                        carrito = session.get('carrito', [])
                        cant_actual = 0
                        for item in carrito:
                            if item.get('id') == producto.id:
                                cant_actual = item.get('cantidad', 0)
                                break
                        cant_a_validar = cant_actual + qty
                    
                    # Validar disponibilidad si la acción es sumar o establecer cantidad
                    if action_type in ['add', 'set'] and not producto.esta_disponible(cant_a_validar):
                        stock_libre = producto.stock - producto.stock_reservado
                        db_res = {
                            "success": False,
                            "action": "updateCartItem",
                            "error": f"Stock insuficiente para '{producto.nombre}'. Solicitado total: {cant_a_validar}, Disponible real: {stock_libre}."
                        }
                    else:
                        imagenes = producto.obtener_todas_imagenes()
                        imagen = imagenes[0] if imagenes else (producto.imagen or "")
                        db_res = {
                            "success": True,
                            "action": "updateCartItem",
                            "action_type": action_type,
                            "id": producto.id,
                            "nombre": producto.nombre,
                            "precio": float(producto.precio_venta()),
                            "imagen": imagen,
                            "cantidad": qty,
                            "mensaje": f"Carrito actualizado: {action_type} para '{producto.nombre}' con cantidad {qty}."
                        }
                system_msgs.append(f"Resultado de actualizar carrito: {json.dumps(db_res)}.")

            elif func_name == "checkoutCart":
                db_res = {
                    "success": True,
                    "action": "checkoutCart",
                    "mensaje": "Iniciando checkout."
                }
                system_msgs.append("El sistema abrió la pantalla de pago.")

            # --- Lógica de CRM  - HERRAMIENTA 3 ---
            elif func_name == "createDeal":
                from utils.crm import create_deal
                db_res = create_deal({
                    'id': args.get('id'),
                    'cliente_nombre': args.get('customer_name'),
                    'valor_estimado': args.get('estimated_value'),
                    'etapa': args.get('stage'),
                    'notas': args.get('notes')
                })
                system_msgs.append(f"Se gestionó el negocio en el CRM. Resultado: {json.dumps(db_res)}.")

            elif func_name == "updateDealStage":
                from utils.crm import update_deal_stage
                db_res = update_deal_stage(args.get('deal_id'), args.get('new_stage'))
                system_msgs.append(f"Cambio de etapa realizado. Resultado: {json.dumps(db_res)}.")

            elif func_name == "forecastRevenue":
                from utils.crm import forecast_revenue
                db_res = forecast_revenue()
                system_msgs.append(f"Estadísticas del pipeline: {json.dumps(db_res)}.")
                target_model = "qwen-plus"

            elif func_name == "generateExecutiveSummary":
                from utils.crm import generate_executive_summary
                db_res = generate_executive_summary()
                system_msgs.append(f"DATOS ESTRATÉGICOS: {json.dumps(db_res)}.")
                target_model = "qwen-max"

            # --- Lógica de Facturación ---
            elif func_name == "createInvoice":
                from models import db, Pedido, Factura
                from utils.billing import calculate_invoice_data
                pedido_id = args.get('pedido_id')
                pedido = Pedido.query.get(pedido_id) if pedido_id else None
                if not pedido:
                    db_res = {"success": False, "mensaje": f"Pedido #{pedido_id} no encontrado."}
                elif pedido.estado not in ('pendiente', 'pagado', 'procesando'):
                    db_res = {"success": False, "mensaje": f"No se puede facturar un pedido en estado '{pedido.estado}'."}
                else:
                    try:
                        datos = calculate_invoice_data(pedido)
                        nueva_f = Factura(
                            numero_factura=Factura.generar_numero_correlativo(),
                            pedido_id=pedido.id, subtotal=datos['subtotal'],
                            iva_porcentaje=datos['iva_porcentaje'], iva_monto=datos['iva_monto'], total=datos['total']
                        )
                        db.session.add(nueva_f)
                        db.session.commit()
                        db_res = {
                            "success": True,
                            "mensaje": f"Factura {nueva_f.numero_factura} generada para pedido #{pedido.id} (estado: {pedido.estado}).",
                            "factura_id": nueva_f.id,
                            "numero_factura": nueva_f.numero_factura,
                            "total": float(nueva_f.total)
                        }
                        # Solo registrar movimiento contable si el pedido ya está pagado
                        if pedido.estado == 'pagado':
                            from utils.accounting import register_transaction
                            register_transaction(
                                tipo='ingreso', monto=float(nueva_f.total),
                                categoria='venta', fuente='caja',
                                descripcion=f"Ingreso por factura {nueva_f.numero_factura}",
                                referencia_id=f"FAC-{nueva_f.id}"
                            )
                    except Exception as e:
                        db_res = {"success": False, "mensaje": str(e)}
                system_msgs.append(f"Acción Factura: {json.dumps(db_res)}.")
            elif func_name == "getInvoiceStatus":
                from models import Factura
                f = Factura.query.get(args.get('factura_id'))
                if not f: db_res = {"success": False, "mensaje": "Factura no encontrada."}
                else: db_res = {"success": True, "numero": f.numero_factura, "estado": f.estado, "total": float(f.total)}
                system_msgs.append(f"Estado Factura: {json.dumps(db_res)}.")

            # --- Lógica de Contabilidad - HERRAMIENTA 5 ---
            elif func_name == "recordTransaction":
                from utils.accounting import register_transaction
                db_res = register_transaction(
                    tipo=args.get('type'),
                    monto=args.get('amount'),
                    categoria=args.get('category'),
                    fuente=args.get('source', 'caja'),
                    descripcion=args.get('description')
                )
                system_msgs.append(f"Registro contable realizado: {json.dumps(db_res)}.")

            elif func_name == "getAccountBalance":
                from utils.accounting import get_account_balance
                db_res = get_account_balance()
                system_msgs.append(f"BALANCE ACTUAL: {json.dumps(db_res)}.")

            elif func_name == "generateMonthlyReport":
                from utils.accounting import generate_monthly_report
                db_res = generate_monthly_report()
                system_msgs.append(f"REPORTE CATEGORIZADO: {json.dumps(db_res)}.")
                target_model = "qwen-max"

            # --- Lógica de Inventario -  HERRAMIENTA 8 ---
            elif func_name == "searchProduct":
                from utils.inventory import search_product
                db_res = search_product(query=args.get('query'))
                system_msgs.append(f"Búsqueda de producto completada: {json.dumps(db_res)}.")
            
            elif func_name == "checkStock":
                from utils.inventory import check_stock
                db_res = check_stock(product_id=args.get('product_id'))
                system_msgs.append(f"Consulta de inventario completada: {json.dumps(db_res)}.")

            elif func_name == "reserveStock":
                from utils.inventory import reserve_stock
                minutos=args.get('minutes')
                if minutos is not None:
                    db_res = reserve_stock(product_id=args.get('product_id'), quantity=args.get('quantity'), minutes=minutos)
                else:
                    db_res = reserve_stock(product_id=args.get('product_id'), quantity=args.get('quantity'))
                system_msgs.append(f"Reserva de inventario completada: {json.dumps(db_res)}.")

            elif func_name == "updateStock":
                from utils.inventory import update_stock
                db_res = update_stock(product_id=args.get('product_id'), delta=args.get('delta'))
                system_msgs.append(f"Actualización física de inventario completada: {json.dumps(db_res)}.")

            # --- Lógica de Analítica y BI - HERRAMIENTA 12 ---
            elif func_name == "getSalesReport":
                from utils.analytics import get_sales_report
                periodo = args.get('period', 'this_month') or 'this_month'
                db_res = get_sales_report(period=periodo)
                system_msgs.append(f"Reporte de ventas completado: {json.dumps(db_res)}.")

            elif func_name == "comparePeriods":
                from utils.analytics import compare_periods
                p1 = args.get('period1')
                p2 = args.get('period2')
                db_res = compare_periods(period1=p1, period2=p2)
                system_msgs.append(f"Comparación de periodos completada: {json.dumps(db_res)}.")

            elif func_name == "getTopProducts":
                from utils.analytics import get_top_products
                lim = args.get('limit', 5) or 5
                db_res = get_top_products(limit=lim)
                system_msgs.append(f"Ranking de productos estrella completado: {json.dumps(db_res)}.")

            # --- Lógica de Agenda y Recordatorios - HERRAMIENTA 13 ---
            elif func_name == "createReminder":
                from utils.agenda import createReminder
                db_res = createReminder(text=args.get('text'), datetime_str=args.get('datetime'))
                system_msgs.append(f"Resultado de creación de recordatorio: {json.dumps(db_res)}")

            elif func_name == "listTodayReminders":
                from utils.agenda import listTodayReminders
                db_res = listTodayReminders()
                system_msgs.append(f"Lista de recordatorios pendientes obtenida: {json.dumps(db_res)}")

            elif func_name == "markDone":
                from utils.agenda import markDone
                db_res = markDone(reminderId=args.get('reminderId'))
                system_msgs.append(f"Resultado de la actualización de recordatorio: {json.dumps(db_res)}")

            if db_res:
                db_results_totales.append(db_res)

        # 4. Feedback a la IA (Observaciones nativas)
        
        # Guardamos el mensaje actual del usuario (o system prompt) si existe
        if prompt_actual:
            historial_bucle.append({"role": "user", "content": prompt_actual})
        
        # Añadimos la respuesta nativa del asistente pidiendo las herramientas
        historial_bucle.append({
            "role": "assistant",
            "content": result.get("content") or "",
            "tool_calls": result.get("tool_calls")
        })
        
        # Añadimos los resultados de cada herramienta con el rol 'tool'
        for i, tool_call in enumerate(result["tool_calls"][:3]):
            historial_bucle.append({
                "role": "tool",
                "tool_call_id": tool_call.get("id"),
                "content": system_msgs[i] if i < len(system_msgs) else '{"success": false}'
            })
        
        ejecucion_directa = False  # Resetear la bandera para la siguiente iteración del bucle
        # El próximo prompt será vacío; el modelo reaccionará a los mensajes 'tool'
        prompt_actual = ""  
        modelo_actual = target_model

    # 5. Respuesta final al usuario
    return jsonify({
        "response": respuesta_final.strip() if respuesta_final.strip() else result.get("content", "Acción completada con éxito."),
        "reasoning": reasoning_final.strip() if reasoning_final.strip() else result.get("reasoning"),
        "status": "tool_executed" if db_results_totales else "success",
        "db_results": db_results_totales,
        "db_result": db_results_totales[0] if db_results_totales else None,
        "model": modelo_actual
    })