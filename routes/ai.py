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
    modelo = data.get('model', 'qwen3.6-plus')
    
    if not mensaje:
        return jsonify({"error": "El mensaje es obligatorio"}), 400
    
    # Llamar al servicio de Qwen
    respuesta, razonamiento = qwen_service.get_response(mensaje, model=modelo)
    
    return jsonify({
        "response": respuesta,
        "reasoning": razonamiento,
        "model": modelo
    })
