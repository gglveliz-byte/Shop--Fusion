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
    respuesta, razonamiento = qwen_service.get_response(pregunta, model=model_name)
    
    # Si hay razonamiento (modelo 32b), lo mostramos primero
    if razonamiento:
        print("--- PROCESO DE PENSAMIENTO (Reasoning) ---")
        print(razonamiento)
        print("-" * 40)
    
    # Mostramos la respuesta final
    print("\n--- RESPUESTA FINAL ---")
    print(respuesta)
    print("\n" + "="*40 + "\n")

if __name__ == "__main__":
    test_ai()

