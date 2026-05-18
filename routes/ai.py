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
        # Si no es admin, solo permitimos ventas directas para evitar acceso a datos sensibles de CRM/Facturación
        herramientas_disponibles = [t for t in qwen_service.TOOLS if t['function']['name'] == 'createCustomerOrder']
        print("DEBUG: Usuario no-admin detectado. Deshabilitando herramientas de facturación.")
        
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
        tool_call = result["tool_calls"][0]
        func_name = tool_call["function"]["name"]
        args_str = tool_call["function"]["arguments"]
        
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            if not args_str.strip().endswith("}"): args_str += "}"
            try:
                args = json.loads(args_str)
            except:
                return jsonify({"error": "Error de formato en la IA. Reintente."}), 400

        db_res = None
        system_msg = ""
        target_model = modelo # Por defecto usar el modelo actual

        # --- Lógica de Ventas ---
        if func_name == "createCustomerOrder":
            # Traducir campos de la IA a nuestro servicio de la Fase 1
            order_data = {
                'cliente_nombre': args.get('customer_name'),
                'cliente_telefono': args.get('customer_phone'),
                'cliente_direccion': args.get('customer_address'),
                'productos': [{'id': p['product_id'], 'cantidad': p['quantity']} for p in args.get('items', [])]
            }
            db_res = create_order_from_json(order_data)
            
            # Segunda llamada para respuesta final con instrucciones detalladas de calidad
            system_msg = (
                f"El sistema ejecutó la orden. Resultado: {json.dumps(db_res)}. "
                "Informa al usuario con lenguaje natural. Incluye resumen de productos y total."
            )

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
            system_msg = f"Se gestionó el negocio en el CRM. Resultado: {json.dumps(db_res)}. Informa al usuario."

        elif func_name == "updateDealStage":
            from utils.crm import update_deal_stage
            db_res = update_deal_stage(args.get('deal_id'), args.get('new_stage'))
            system_msg = f"Cambio de etapa realizado. Resultado: {json.dumps(db_res)}. Informa al usuario."

        elif func_name == "forecastRevenue":
            from utils.crm import forecast_revenue
            db_res = forecast_revenue()
            system_msg = f"Estadísticas del pipeline: {json.dumps(db_res)}. Da un resumen rápido de las proyecciones."
            target_model = "qwen-plus"

        elif func_name == "generateExecutiveSummary":
            from utils.crm import generate_executive_summary
            db_res = generate_executive_summary()
            system_msg = (
                f"DATOS ESTRATÉGICOS: {json.dumps(db_res)}. Analiza estos datos como consultor senior. "
                "Genera un resumen ejecutivo sobre salud financiera y proyecciones. Sé profesional."
            )
            target_model = "qwen-max" # REQUERIMIENTO: Qwen-Max para resúmenes

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
                except Exception as e: db_res = {"success": False, "mensaje": str(e)}
            system_msg = f"Acción Factura: {json.dumps(db_res)}. Informa al usuario."

        elif func_name == "getInvoiceStatus":
            from models import Factura
            f = Factura.query.get(args.get('factura_id'))
            if not f: db_res = {"success": False, "mensaje": "Factura no encontrada."}
            else: db_res = {"success": True, "numero": f.numero_factura, "estado": f.estado, "total": float(f.total)}
            system_msg = f"Estado Factura: {json.dumps(db_res)}. Informa al usuario."

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
            system_msg = f"Registro contable realizado: {json.dumps(db_res)}. Confirma la operación."

        elif func_name == "getAccountBalance":
            from utils.accounting import get_account_balance
            db_res = get_account_balance()
            system_msg = f"BALANCE ACTUAL: {json.dumps(db_res)}. Informa los totales al usuario."

        elif func_name == "generateMonthlyReport":
            from utils.accounting import generate_monthly_report
            db_res = generate_monthly_report()
            system_msg = f"REPORTE CATEGORIZADO: {json.dumps(db_res)}. Analiza los gastos e ingresos y da un resumen ejecutivo."
            target_model = "qwen-max" # Reportes complejos usan el modelo senior

        # 4. Respuesta Final unificada para cualquier herramienta
        if db_res:
            # Sincronización Automática: Si se creó una factura con éxito, registrar ingreso
            if func_name == "createInvoice" and db_res.get('success'):
                from utils.accounting import register_transaction
                # Obtener monto de la factura
                from models import Factura
                f = Factura.query.get(db_res.get('factura_id'))
                if f:
                    register_transaction(
                        tipo='ingreso',
                        monto=float(f.total),
                        categoria='venta',
                        fuente='caja',
                        descripcion=f"Ingreso automático por factura {f.numero_factura}",
                        referencia_id=f"FAC-{f.id}"
                    )

            # Forzamos tools=[] para que la IA NO intente llamar a otra herramienta y nos responda obligatoriamente con texto.
            final_result = qwen_service.get_response(mensaje, model=target_model, history=historial, system_instruction=system_msg, tools=[])
            
            if isinstance(final_result, str):
                return jsonify({"error": final_result}), 500
                
            return jsonify({
                "response": final_result.get("content"),
                "reasoning": final_result.get("reasoning"),
                "status": "tool_executed",
                "db_result": db_res
            })

    # 5. Respuesta normal si no hubo herramientas
    return jsonify({
        "response": result.get("content"),
        "reasoning": result.get("reasoning"),
        "model": modelo
    })
