import os
from openai import OpenAI
from dotenv import load_dotenv

# Cargar la API KEY desde el .env
load_dotenv()

def list_available_models():
    """
    Consulta al servidor de Alibaba Cloud la lista de todos los modelos
    disponibles para la API KEY actual.
    """
    api_key = os.environ.get('DASHSCOPE_API_KEY')
    
    if not api_key:
        print("Error: DASHSCOPE_API_KEY no encontrada en el archivo .env")
        return

    print("--- CONSULTANDO MODELOS DISPONIBLES EN ALIBABA CLOUD ---")
    
    try:
        # Inicializar el cliente compatible con OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        )

        # Solicitar la lista de modelos
        models = client.models.list()

        print(f"\nSe encontraron {len(models.data)} modelos disponibles:\n")
        
        # Ordenar y mostrar los nombres de los modelos
        model_names = sorted([model.id for model in models.data])
        for i, name in enumerate(model_names, 1):
            print(f"{i}. {name}")
            
        print("\n" + "="*50)

    except Exception as e:
        print(f"\nError al obtener la lista: {str(e)}")

if __name__ == "__main__":
    list_available_models()