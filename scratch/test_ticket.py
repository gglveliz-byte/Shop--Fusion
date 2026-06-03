import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app, db
from routes.ai import qwen_service
import json

app = create_app()

with app.app_context():
    print("=======================================")
    print("PASO 1: ENVIANDO MENSAJE URGENTE A LA IA")
    print("=======================================")
    print("Usuario: 'Tengo un problema urgente con mi pedido, no puedo pagar'\n")
    
    # Simulate user not being admin
    herramientas_permitidas = ['createCustomerOrder', 'addProductToCart', 'updateCartItem', 'checkoutCart', 'listProducts', 'validatePaymentReceipt', 'createSupportTicket', 'getTicketStatus', 'addComment']
    herramientas_disponibles = [t for t in qwen_service.TOOLS if t['function']['name'] in herramientas_permitidas]
    system_msg = qwen_service.SYSTEM_PROMPT + "\n\nAVISO CRÍTICO DE SEGURIDAD: El usuario actual NO es Administrador. "
    
    res1 = qwen_service.get_response(
        "Tengo un problema urgente con mi pedido, no puedo pagar",
        history=[],
        tools=herramientas_disponibles,
        system_instruction=system_msg
    )
    
    print("--- RESPUESTA DE LA IA ---")
    if getattr(res1, "get", None) and res1.get("content"):
        print(f"IA: {res1.get('content')}")
    else:
        print(f"IA: {res1}")
        
    print("\n=======================================")
    print("PASO 2: EL USUARIO PROPORCIONA SUS DATOS")
    print("=======================================")
    print("Usuario: 'Mi nombre es Juan Pérez y mi correo es juan@example.com'\n")
    
    history = [
        {"role": "user", "content": "Tengo un problema urgente con mi pedido, no puedo pagar"},
        {"role": "assistant", "content": res1.get("content") if isinstance(res1, dict) else str(res1)}
    ]
    
    res2 = qwen_service.get_response(
        "Mi nombre es Juan Pérez y mi correo es juan@example.com",
        history=history,
        tools=herramientas_disponibles,
        system_instruction=system_msg
    )
    
    print("--- RESPUESTA/ACCIÓN DE LA IA ---")
    if isinstance(res2, dict) and res2.get("tool_calls"):
        print("La IA ha decidido llamar a una herramienta:\n")
        for tc in res2["tool_calls"]:
            print(f"🛠️ Herramienta: {tc['function']['name']}")
            print(f"📦 Argumentos: {tc['function']['arguments']}")
            
            # Simulate backend connection (Phase 5)
            if tc['function']['name'] == 'createSupportTicket':
                from utils.support import create_ticket, escalate_ticket
                args = json.loads(tc['function']['arguments'])
                
                print("\n--- SIMULANDO BACKEND (routes/ai.py) ---")
                print("Llamando a create_ticket()...")
                db_res = create_ticket(
                    subject=args.get('subject'),
                    description=args.get('description'),
                    priority=args.get('priority', 'media'),
                    contact_name=args.get('contact_name'),
                    contact_email=args.get('contact_email'),
                    canal='chat'
                )
                print(f"Resultado BD: {db_res}")
                
                if db_res.get('success') and args.get('priority') in ['alta', 'critica']:
                    print("\n¡Prioridad Alta/Crítica Detectada! Llamando a escalate_ticket()...")
                    esc_res = escalate_ticket(db_res['ticket_id'])
                    print(f"Resultado Escalado: {esc_res}")
    else:
        print(res2)
