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
    if not es_admin:
        # Si no es admin, solo permitimos ventas directas para evitar acceso a datos sensibles de CRM/Facturación
        herramientas_disponibles = [t for t in qwen_service.TOOLS if t['function']['name'] == 'createCustomerOrder']
        print("DEBUG: Usuario no-admin detectado. Deshabilitando herramientas de facturación.")

    # 2. Llamada inicial a la IA para detectar intención
    result = qwen_service.get_response(mensaje, model=modelo, history=historial, tools=herramientas_disponibles)
    
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
        elif func_name == "upsertDeal":
            from utils.crm import upsert_opportunity
            db_res = upsert_opportunity({
                'id': args.get('id'),
                'cliente_nombre': args.get('customer_name'),
                'valor_estimado': args.get('estimated_value'),
                'etapa': args.get('stage'),
                'notas': args.get('notes')
            })
            system_msg = f"Se gestionó el negocio en el CRM. Resultado: {json.dumps(db_res)}. Informa al usuario."

        elif func_name == "updateDealStage":
            from utils.crm import update_opportunity_stage
            db_res = update_opportunity_stage(args.get('deal_id'), args.get('new_stage'))
            system_msg = f"Cambio de etapa realizado. Resultado: {json.dumps(db_res)}. Informa al usuario."

        elif func_name == "getPipelineSummary":
            from utils.crm import get_pipeline_summary
            db_res = get_pipeline_summary()
            system_msg = f"Estadísticas del pipeline: {json.dumps(db_res)}. Da un resumen estratégico usando Qwen-Max."
            target_model = "qwen-max" # Forzamos el modelo potente para análisis

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

        # 4. Respuesta Final unificada para cualquier herramienta
        if db_res:
            final_result = qwen_service.get_response(mensaje, model=target_model, history=historial, system_instruction=system_msg)
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
