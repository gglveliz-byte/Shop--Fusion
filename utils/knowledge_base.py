import math
from models import DocumentoConocimiento, db

def cosine_similarity(vec1, vec2):
    """Función matemática pura para calcular similitud vectorial."""
    if not vec1 or not vec2: return 0.0
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))
    if magnitude1 == 0 or magnitude2 == 0: return 0.0
    return dot_product / (magnitude1 * magnitude2)

def generar_embedding(texto, ai_client):
    """Usa el cliente inyectado desde afuera para generar el vector."""
    try:
        response = ai_client.embeddings.create(
            model="text-embedding-v2",
            input=texto
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"[RAG ERROR] Fallo al generar embedding: {e}")
        return None

def searchKnowledgeBase(query, ai_client):
    """Motor RAG puramente matemático. Recibe el cliente IA como parámetro."""
    query_embedding = generar_embedding(query, ai_client)

    if not query_embedding:
        return {"success": False,"error": "Error al procesar el vector de búsqueda."}

    documentos = DocumentoConocimiento.query.all()

    if not documentos:
        return {"success": False,"error": "La base de conocimiento está vacía."}

    resultados = []
    updated = False

    for doc in documentos:
        doc_embedding = doc.vector_embedding
        # [Lazy Generation]
        if not doc_embedding:
            doc_embedding = generar_embedding(doc.contenido_texto, ai_client)

            if doc_embedding:
                doc.vector_embedding = doc_embedding
                updated = True

        if doc_embedding:
            similitud = cosine_similarity(query_embedding, doc_embedding)
            resultados.append({
                "titulo": doc.titulo,
                "contenido": doc.contenido_texto[:500],
                #Redondea a 4 decimales para mejor legibilidad
                "score": round(similitud, 4)
            })

    # Commit único al finalizar el bucle
    if updated:
        db.session.commit()

    # Ordenar por similitud descendente
    resultados.sort(key=lambda x: x["score"],reverse=True)

    # Filtrar mejores coincidencias
    top_resultados = [res for res in resultados if res["score"] > 0.40][:2]

    if not top_resultados:
        return {"success": False,"error": "No encontré información en los manuales."}

    return {"success": True,"matches": top_resultados}