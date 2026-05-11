import os
from openai import OpenAI
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

class QwenAIService:
    """
    Servicio para interactuar con los modelos de Alibaba Cloud Qwen.
    Configurado para usar exclusivamente los modelos aprobados para Shop Fusion.
    """
    # Modelos oficiales aprobados (docs/seleccion_modelos_ia.md)
    MODEL_LOGICA = "qwen-plus"      # Para Orquestación, Ventas y Lógica
    MODEL_VISION = "qwen-vl-max"    # Para OCR y Validación de Bouchers

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

    def get_response(self, prompt, model=None, system_instruction="Eres un asistente útil y profesional."):
        """
        Envía una consulta a la IA y retorna la respuesta.
        Soporta los modelos aprobados: 
        - qwen-plus (Lógica y Orquestación)
        - qwen-vl-max (Visión y OCR)
        """
        if not self.client:
            return "Error: DASHSCOPE_API_KEY no configurada.", None

        # Usar modelo de lógica por defecto si no se especifica
        target_model = model if model else self.MODEL_LOGICA

        try:
            # Preparamos los mensajes en formato chat
            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ]

            # Parámetros adicionales para el modelo de razonamiento (si aplica)
            extra_params = {}
            if target_model == "qwen-max": # Por si se escala a MAX en el futuro
                extra_params["extra_body"] = {"enable_thinking": True}

            # Realizamos la llamada a la API con streaming activado
            response_stream = self.client.chat.completions.create(
                model=target_model,
                messages=messages,
                stream=True,
                **extra_params
            )

            full_content = ""
            full_reasoning = ""

            for chunk in response_stream:
                if not chunk.choices:
                    continue
                
                delta = chunk.choices[0].delta
                
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    full_reasoning += delta.reasoning_content
                
                if delta.content:
                    full_content += delta.content
            
            return full_content, (full_reasoning if full_reasoning else None)

        except Exception as e:
            return f"Error al conectar con Qwen: {str(e)}", None

# Instancia global para ser usada en toda la app
qwen_service = QwenAIService()

