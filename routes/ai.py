import json
from flask import Blueprint, request, jsonify, render_template
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
    """Endpoint para procesar mensajes del chatbot con soporte para ejecución de herramientas."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No hay datos en la solicitud"}), 400
    
    mensaje = data.get('message')
    modelo = data.get('model', 'qwen-plus')
    historial = data.get('history', [])
    
    if not mensaje:
        return jsonify({"error": "El mensaje es obligatorio"}), 400
    
    # 1. Determinar qué herramientas puede usar este usuario
    from flask_login import current_user
    es_admin = hasattr(current_user, 'username') # Verificación de rol administrativo
    
    # Si no es admin, filtramos las herramientas de facturación
    herramientas_disponibles = qwen_service.TOOLS
    if not es_admin:
        herramientas_disponibles = [t for t in qwen_service.TOOLS if t['function']['name'] == 'createCustomerOrder']
        print("DEBUG: Usuario no-admin detectado. Deshabilitando herramientas de facturación.")

    # 2. Primera llamada a la IA para detectar intención
    print(f"DEBUG: Enviando mensaje a IA: {mensaje}")
    result = qwen_service.get_response(mensaje, model=modelo, history=historial, tools=herramientas_disponibles)
    
    # Si ocurrió un error (devuelve un string en lugar de dict en caso de excepción capturada)
    if isinstance(result, str):
        print(f"DEBUG ERROR IA: {result}")
        return jsonify({"error": result}), 500

    # 2. Verificar si la IA quiere ejecutar una herramienta
    if result.get("tool_calls"):
        tool_call = result["tool_calls"][0]
        func_name = tool_call["function"]["name"]
        args_str = tool_call["function"]["arguments"]
        print(f"DEBUG: IA quiere ejecutar {func_name} con args: {args_str}")
        
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            print("DEBUG ERROR: JSON mal formado por la IA. Intentando limpiar...")
            # Intento de reparación simple: cerrar llaves si faltan
            if not args_str.strip().endswith("}"):
                args_str += "}"
            try:
                args = json.loads(args_str)
            except:
                return jsonify({"error": "La IA envió datos incompletos. Por favor, intenta de nuevo."}), 400

        if func_name == "createCustomerOrder":
            # Traducir campos de la IA a nuestro servicio de la Fase 1
            order_data = {
                'cliente_nombre': args.get('customer_name'),
                'cliente_telefono': args.get('customer_phone'),
                'cliente_direccion': args.get('customer_address'),
                'productos': [{'id': p['product_id'], 'cantidad': p['quantity']} for p in args.get('items', [])]
            }
            
            # EJECUCIÓN REAL EN BASE DE DATOS
            print(f"DEBUG: Ejecutando create_order_from_json con: {order_data}")
            db_res = create_order_from_json(order_data)
            print(f"DEBUG: Resultado DB: {db_res}")
            
            # 3. Segunda llamada a la IA para que dé la respuesta final al usuario
            system_msg = (
                f"El sistema ha ejecutado la acción. Resultado: {json.dumps(db_res)}. "
                "Informa al usuario con lenguaje natural. MUY IMPORTANTE: Incluye un resumen detallado "
                "que enumere los productos comprados, sus cantidades y el total a pagar. "
                "Si hubo un error (como stock insuficiente), explícalo claramente."
            )
            print("DEBUG: Solicitando respuesta final con resumen detallado...")
            final_result = qwen_service.get_response(mensaje, model=modelo, history=historial, system_instruction=system_msg)
            
            final_content = final_result.get("content")
            if not final_content:
                final_content = f"He procesado tu solicitud. Resultado: {db_res.get('message', 'Operación completada')}"
            
            return jsonify({
                "response": final_content,
                "reasoning": final_result.get("reasoning"),
                "status": "tool_executed",
                "db_result": db_res
            })

        elif func_name == "createInvoice":
            # [NUEVO] Manejador de creación de facturas desde la IA
            from models import db, Pedido, Factura
            from utils.billing import calculate_invoice_data
            
            pedido_id = args.get('pedido_id')
            pedido = Pedido.query.get(pedido_id)
            
            if not pedido:
                res = {"success": False, "message": f"Pedido #{pedido_id} no encontrado."}
            elif pedido.estado != 'pagado':
                res = {"success": False, "message": f"El pedido #{pedido_id} aún no está pagado. No se puede facturar."}
            elif pedido.factura:
                res = {"success": False, "message": f"El pedido #{pedido_id} ya tiene la factura {pedido.factura.numero_factura}."}
            else:
                try:
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
                    res = {"success": True, "message": f"Factura {nueva_f.numero_factura} generada exitosamente.", "factura_id": nueva_f.id}
                except Exception as e:
                    db.session.rollback()
                    res = {"success": False, "message": str(e)}

            # Devolver a la IA para confirmación final al usuario
            final_res = qwen_service.get_response(f"Acción Factura: {json.dumps(res)}", model=modelo, history=historial)
            return jsonify(final_res)

        elif func_name == "getInvoiceStatus":
            # [NUEVO] Manejador de consulta de facturas desde la IA
            from models import Factura
            factura_id = args.get('factura_id')
            f = Factura.query.get(factura_id)
            
            if not f:
                res = {"success": False, "message": "Factura no encontrada."}
            else:
                res = {
                    "success": True, 
                    "numero": f.numero_factura, 
                    "estado": f.estado, 
                    "total": float(f.total),
                    "fecha": f.creado_en.strftime('%d/%m/%Y')
                }

            final_res = qwen_service.get_response(f"Resultado Consulta Factura: {json.dumps(res)}", model=modelo, history=historial)
            return jsonify(final_res)

    # Si no hubo herramientas, devolver la respuesta normal
    print(f"DEBUG: Respuesta normal de IA: {result.get('content')[:50] if result.get('content') else 'VACIO'}...")
    return jsonify({
        "response": result.get("content"),
        "reasoning": result.get("reasoning"),
        "model": modelo
    })
