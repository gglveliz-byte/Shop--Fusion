from flask import Blueprint, request, jsonify, render_template
from utils.ai_qwen import qwen_service
from utils.rate_limit import limiter

bp = Blueprint('ai', __name__, url_prefix='/ai')

@bp.route('/interfaz')
def interface():
    """
    Renderiza la página dedicada del chatbot.
    """
    return render_template('ai/chat_page.html')

@bp.route('/chat', methods=['POST'])
@limiter.limit("5 per minute")
def chat():
    """
    Endpoint para procesar mensajes del chatbot.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No hay datos en la solicitud"}), 400
    
    mensaje = data.get('message')
    modelo = data.get('model', 'qwen-plus')
    historial = data.get('history', []) # Capturar el historial enviado por el frontend
    
    if not mensaje:
        return jsonify({"error": "El mensaje es obligatorio"}), 400
    
    # Llamar al servicio de Qwen con el historial
    result = qwen_service.get_response(mensaje, model=modelo, history=historial)
    
    # Si ocurrió un error (devuelve un string en lugar de dict en caso de excepción capturada)
    if isinstance(result, str):
        return jsonify({"error": result}), 500

    return jsonify({
        "response": result.get("content"),
        "reasoning": result.get("reasoning"),
        "tool_calls": result.get("tool_calls"),
        "model": modelo
    })
