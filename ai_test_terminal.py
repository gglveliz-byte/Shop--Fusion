import sys
from utils.ai_qwen import qwen_service

def test_ai():
    """
    Script de prueba para verificar la conexión con Qwen desde la terminal.
    """
    print("\n--- PRUEBA DE CONEXIÓN QWEN (Alibaba Cloud) ---")
    
    # Lista de modelos disponibles según el requerimiento
    modelos = {
        "1": "qwen3.6-plus",
        "2": "qwen3-32b",
        "3": "qwen3-coder-480b-a35b-instruct"
    }

    print("\nSelecciona el modelo:")
    print("1. Qwen 3.6 Plus (General)")
    print("2. Qwen 3-32b (Razonamiento Profundo)")
    print("3. Qwen 3-Coder (Programación)")
    
    opcion = input("\nElige una opción (1-3): ")
    model_name = modelos.get(opcion, "qwen3.6-plus")
    
    pregunta = input(f"\n[{model_name}] Escribe tu pregunta: ")
    
    print("\nConsultando a la IA... (espera un momento)\n")
    
    # Llamamos al servicio
    result = qwen_service.get_response(pregunta, model=model_name)
    
    # Mostrar Pensamiento si existe
    if result.get("reasoning"):
        print("\n" + "="*20 + " PENSAMIENTO " + "="*20)
        print(result.get("reasoning"))
        print("="*53 + "\n")

    # Mostrar Llamada a Función si existe
    if result.get("tool_calls"):
        print("\n" + "🔧" * 5 + " DETECTADA ACCIÓN DE HERRAMIENTA " + "🔧" * 5)
        for tc in result.get("tool_calls"):
            print(f"Función: {tc['function']['name']}")
            print(f"Argumentos: {tc['function']['arguments']}")
        print("🔧" * 38 + "\n")

    # Mostrar Respuesta Final
    if result.get("content"):
        print(f"Qwen: {result.get('content')}")
    elif result.get("tool_calls"):
        print("Qwen: He preparado la información técnica de la orden de compra solicitada.")

if __name__ == "__main__":

