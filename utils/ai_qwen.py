import os
from openai import OpenAI
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

class QwenAIService:
    """
    Servicio para interactuar con los modelos de Alibaba Cloud Qwen
    usando el endpoint compatible con OpenAI.
    """

    def __init__(self):
        # Configuración del cliente con el endpoint de Singapore (International)
        # La API KEY debe estar en el archivo .env o en las variables de Render
        api_key = os.environ.get('DASHSCOPE_API_KEY')
        
        # Inicializamos el cliente solo si la API KEY existe para evitar errores en el arranque
        self.client = None
        if api_key:
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
            )

    def get_response(self, prompt, model="qwen3-32b", system_instruction="Eres un asistente útil y profesional."):
        """
        Envía una consulta a la IA y retorna la respuesta.
        Soporta los modelos: 
        - qwen3.6-plus (General)
        - qwen3-32b (Razonamiento Profundo)
        - qwen3-coder-480b-a35b-instruct (Código)
        """
        if not self.client:
            return "Error: DASHSCOPE_API_KEY no configurada.", None

        try:
            # Preparamos los mensajes en formato chat
            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ]

            # Parámetros adicionales para el modelo de razonamiento (32b)
            extra_params = {}
            if model == "qwen3-32b":
                # Activamos el pensamiento profundo si el modelo es el 32b
                extra_params["extra_body"] = {"enable_thinking": True}

            # Realizamos la llamada a la API con streaming activado
            response_stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True, # Obligatorio para enable_thinking
                **extra_params
            )

            full_content = ""
            full_reasoning = ""

            # Procesamos los fragmentos (chunks) que llegan en tiempo real
            for chunk in response_stream:
                # Verificamos que el chunk tenga contenido válido para evitar IndexError
                if not chunk.choices:
                    continue
                
                delta = chunk.choices[0].delta
                
                # Capturamos el razonamiento si está presente (solo en modelos thinking)
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    full_reasoning += delta.reasoning_content
                
                # Capturamos el contenido final
                if delta.content:
                    full_content += delta.content
            
            return full_content, (full_reasoning if full_reasoning else None)

        except Exception as e:
            # Captura de errores para depuración (logs)
            return f"Error al conectar con Qwen: {str(e)}", None

# Instancia global para ser usada en toda la app
qwen_service = QwenAIService()

