import json
from flask import Blueprint, request, jsonify, render_template
from flask_login import current_user
from utils.ai_qwen import qwen_service
from utils.rate_limit import limiter
from utils.orders import create_order_from_json

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
        herramientas_permitidas = ['createCustomerOrder', 'addProductToCart', 'updateCartItem', 'checkoutCart', 'listProducts']
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

    # 2. Llamada inicial a la IA para detectar intención
    result = qwen_service.get_response(mensaje, model=modelo, history=historial, tools=herramientas_disponibles, system_instruction=system_msg)
    
    if isinstance(result, str):
        return jsonify({"error": result}), 500

    # 3. Procesar llamadas a herramientas (Tool Calls)
    if result.get("tool_calls"):
        db_results = []
        system_msgs = []
        target_model = modelo # Por defecto usar el modelo actual

        for tool_call in result["tool_calls"]:
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

            elif func_name == "addProductToCart":
                from models import Producto
                p_name = args.get('product_name')
                qty = args.get('quantity', 1) or 1
                
                # Normalizar sinónimos comunes en español
                synonyms = {
                    "zapatilla": "zapato",
                    "zapatillas": "zapato",
                    "tenis": "zapato",
                    "calzado": "zapato",
                    "playera": "camiseta",
                    "remera": "camiseta",
                    "polo": "camiseta",
                    "pantalon": "pantalón",
                    "licra": "pantalón",
                    "pantaloneta": "pantalón",
                    "buzo": "pantalón"
                }
                
                clean_name = p_name.lower().strip() if p_name else ""
                for syn, replacement in synonyms.items():
                    clean_name = clean_name.replace(syn, replacement)
                
                # Búsqueda de coincidencia directa
                producto = Producto.query.filter(Producto.nombre.ilike(f"%{clean_name}%"), Producto.activo == True).first()
                
                # Búsqueda tolerante a fallos si no se encuentra
                if not producto and clean_name:
                    palabras = [p.strip() for p in clean_name.split() if len(p.strip()) > 2]
                    for pal in palabras:
                        normalized_word = pal
                        for syn, replacement in synonyms.items():
                            normalized_word = normalized_word.replace(syn, replacement)
                        producto = Producto.query.filter(Producto.nombre.ilike(f"%{normalized_word}%"), Producto.activo == True).first()
                        if producto:
                            break
                            
                if not producto:
                    db_res = {
                        "success": False,
                        "action": "addProductToCart",
                        "error": f"Producto '{p_name}' no encontrado o agotado."
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
                p_name = args.get('product_name')
                qty = args.get('quantity', 1) or 0
                action_type = args.get('action', 'add')
                
                # Normalizar sinónimos comunes en español
                synonyms = {
                    "zapatilla": "zapato",
                    "zapatillas": "zapato",
                    "tenis": "zapato",
                    "calzado": "zapato",
                    "playera": "camiseta",
                    "remera": "camiseta",
                    "polo": "camiseta",
                    "pantalon": "pantalón",
                    "licra": "pantalón",
                    "pantaloneta": "pantalón",
                    "buzo": "pantalón"
                }
                
                clean_name = p_name.lower().strip() if p_name else ""
                for syn, replacement in synonyms.items():
                    clean_name = clean_name.replace(syn, replacement)
                
                # Búsqueda de coincidencia directa
                producto = Producto.query.filter(Producto.nombre.ilike(f"%{clean_name}%"), Producto.activo == True).first()
                
                # Búsqueda tolerante a fallos si no se encuentra
                if not producto and clean_name:
                    palabras = [p.strip() for p in clean_name.split() if len(p.strip()) > 2]
                    for pal in palabras:
                        normalized_word = pal
                        for syn, replacement in synonyms.items():
                            normalized_word = normalized_word.replace(syn, replacement)
                        producto = Producto.query.filter(Producto.nombre.ilike(f"%{normalized_word}%"), Producto.activo == True).first()
                        if producto:
                            break
                            
                if not producto:
                    db_res = {
                        "success": False,
                        "action": "updateCartItem",
                        "error": f"Producto '{p_name}' no encontrado o agotado."
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

            # --- Lógica de CRM ---
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
                pedido = Pedido.query.get(pedido_id)
                if not pedido: db_res = {"success": False, "mensaje": "Pedido no encontrado."}
                elif pedido.estado != 'pagado': db_res = {"success": False, "mensaje": "Pedido no pagado."}
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
                        db_res = {"success": True, "mensaje": f"Factura {nueva_f.numero_factura} generada.", "factura_id": nueva_f.id}
                        
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
                    except Exception as e: db_res = {"success": False, "mensaje": str(e)}
                system_msgs.append(f"Acción Factura: {json.dumps(db_res)}.")

            elif func_name == "getInvoiceStatus":
                from models import Factura
                f = Factura.query.get(args.get('factura_id'))
                if not f: db_res = {"success": False, "mensaje": "Factura no encontrada."}
                else: db_res = {"success": True, "numero": f.numero_factura, "estado": f.estado, "total": float(f.total)}
                system_msgs.append(f"Estado Factura: {json.dumps(db_res)}.")

            # --- Lógica de Contabilidad ---
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

            if db_res:
                db_results.append(db_res)

        unified_system_msg = " \n".join(system_msgs)
        unified_system_msg += " \nResponde al usuario confirmando de forma amigable todas las acciones ejecutadas con éxito."

        final_result = qwen_service.get_response(mensaje, model=target_model, history=historial, system_instruction=unified_system_msg, tools=[])
        
        if isinstance(final_result, str):
            return jsonify({"error": final_result}), 500
            
        return jsonify({
            "response": final_result.get("content"),
            "reasoning": final_result.get("reasoning"),
            "status": "tool_executed",
            "db_results": db_results,
            "db_result": db_results[0] if db_results else None
        })

    # 5. Respuesta normal si no hubo herramientas
    return jsonify({
        "response": result.get("content"),
        "reasoning": result.get("reasoning"),
        "model": modelo
    })
