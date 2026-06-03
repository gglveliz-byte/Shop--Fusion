# Herramienta FAQ con IA (RAG Experimental)

## Descripción General

Se desarrolló una herramienta experimental de FAQ utilizando un enfoque tipo RAG (Retrieval-Augmented Generation) mediante embeddings y similitud semántica.

El objetivo de esta herramienta era permitir que la IA pudiera consultar manuales internos, políticas de la tienda y preguntas frecuentes antes de responder al usuario.

Actualmente este sistema no se encuentra activo en producción debido a que el uso de embeddings incrementa el consumo de recursos del servidor (RAM, almacenamiento y llamadas API). Sin embargo, el código se mantiene documentado y disponible para futuras versiones del SaaS en caso se utilice una infraestructura de mayor capacidad.
Se recuerda que para este sistema se tiene su propia tabla en la base de datos llamada:
"documentos_conocimiento" ubicado en models.py.

---

# 1. Código de la herramienta FAQ (`utils/knowledge_base.py`)

El código utilizado para el motor RAG experimental se encuentra en la misma ubicación donde se indica en la línea del título Nº1. Se encuentra como comentario todo el código.

---

# 2. Registro de herramienta en TOOLS (`utils/ai_qwen.py`)

Para registrar la herramienta dentro de la lista de herramientas (TOOLS) disponibles para Qwen, se utilizó el siguiente bloque:

```python
# HERRAMIENTA RAG PARA CONSULTAR MANUALES - FAQ (HERRAMIENTA 10)
{
    "type": "function",
    "function": {
        "name": "searchKnowledgeBase",
        "description": "Busca información en manuales internos, políticas de la tienda, garantías, envíos, devoluciones y preguntas frecuentes. Debes usar esta herramienta antes de responder consultas sobre políticas, soporte o reglas del negocio.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Pregunta o tema específico a buscar(ej: política de devoluciones, garantía de productos, tiempos de envío)."
                }
            },
            "required": ["query"]
        }
    }
}
```

---

# 3. Integración en `routes/ai.py`

## 3.1 Herramienta permitida para usuarios normales

En la sección donde se definen las herramientas permitidas para usuarios no administradores, se agregó el nombre de la herramienta dentro de la lista: (línea 144 - herramientas_permitidas)

```python
'searchKnowledgeBase'
```

---

## 3.2 Lógica principal de ejecución (`elif`)

Posteriormente, dentro del bloque principal de herramientas (`elif func_name == ...`), se agregó la lógica de ejecución de la herramienta:

```python
# --- Lógica de Base de Conocimientos (FAQ)  ---
elif func_name == "searchKnowledgeBase":
    from utils.knowledge_base import searchKnowledgeBase
    # IMPORTANTE: Le inyectamos el cliente de Qwen que ya tenemos instanciado arriba
    # Reutilizar el cliente ya inicializado en qwen_service
    db_res = searchKnowledgeBase(query=args.get('query'),ai_client=qwen_service.client)
    
    if db_res.get('success'):
        # Juntamos los fragmentos encontrados en un solo texto
        fragmentos = "\n\n".join([f"📖 {m['titulo']}:\n{m['contenido']}" for m in db_res['matches']])
        system_msgs.append(
            f"[SISTEMA INTERNO] Encontré estos manuales en la empresa para tu consulta:\n\n{fragmentos}\n\n"
            "INSTRUCCIÓN: Redacta una respuesta amable al usuario basándote ESTRICTAMENTE en estos textos. No inventes reglas que no estén ahí."
        )
    else:
        system_msgs.append(
            f"[SISTEMA INTERNO] Resultado de la búsqueda: {db_res.get('error')}. "
            "INSTRUCCIÓN: Dile al cliente que no tienes esa información a mano y que un asesor humano se pondrá en contacto pronto."
        )
```

---