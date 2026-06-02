import json
from app import create_app
from models import db 

app = create_app()

FAQS_INICIALES = [
    {
        "titulo": "Política de Devoluciones",
        "categoria": "politicas",
        "contenido": "Las devoluciones solo se aceptan dentro de los primeros 30 días tras la recepción del producto. El artículo debe estar en su embalaje original y sin signos de uso. Para iniciar una devolución, el cliente debe contactar a soporte técnico con su número de orden. Los reembolsos se procesan a través de PayPal o el método de pago original en un plazo de 3 a 5 días hábiles. No aceptamos devoluciones de ropa interior o software descargable."
    },
    {
        "titulo": "Tiempos y Costos de Envío",
        "categoria": "logistica",
        "contenido": "Ofrecemos tres tipos de envío: 1) Envío Estándar: Tarda de 5 a 7 días hábiles y es gratuito en pedidos mayores a $50. 2) Envío Exprés: Tarda de 2 a 3 días hábiles y cuesta $15 adicionales. 3) Envío Internacional: Tarda de 10 a 15 días hábiles y el costo se calcula al finalizar la compra dependiendo del país. Los envíos se realizan de Lunes a Viernes, excluyendo feriados nacionales."
    },
    {
        "titulo": "Garantía de Productos Tecnológicos",
        "categoria": "garantias",
        "contenido": "Todos nuestros equipos tecnológicos (Laptops, Teléfonos, Servidores) cuentan con una garantía de fabricante de 1 año. Esta garantía cubre únicamente defectos de fábrica, como fallos en la placa madre, batería o pantalla sin impacto. La garantía queda anulada automáticamente si el dispositivo presenta daños por líquidos, caídas, o si ha sido abierto por personal no autorizado. Para reclamar la garantía, es obligatorio presentar la factura original de compra."
    },
    {
        "titulo": "Guía de Tallas para Ropa",
        "categoria": "general",
        "contenido": "Para elegir la talla correcta de ropa, como nuestro 'Pantalón Deportivo Puma' o camisetas, recomendamos lo siguiente: Talla S (Cintura 71-76cm), Talla M (Cintura 81-86cm), Talla L (Cintura 91-96cm). El calzado deportivo viene en tallas estándar US. Si estás entre dos tallas de ropa, te recomendamos elegir la talla mayor para un ajuste más holgado, o la talla menor si prefieres un ajuste más ceñido."
    }
]

def inyectar_documentos():
    with app.app_context():
        from models import DocumentoConocimiento
        print("Iniciando inyección de Base de Conocimiento (FAQ)...")
        
        # Verificar si ya existen para no duplicar
        existentes = DocumentoConocimiento.query.count()
        if existentes > 0:
            print(f"Ya existen {existentes} documentos en la BD. Limpiando para actualizar...")
            DocumentoConocimiento.query.delete()
            db.session.commit()
            
        for doc in FAQS_INICIALES:
            nuevo_doc = DocumentoConocimiento(
                titulo=doc['titulo'],
                categoria=doc['categoria'],
                contenido_texto=doc['contenido']
                # Nota: vector_embedding se dejará vacío por ahora. Lo llenaremos en la Fase 2.
            )
            db.session.add(nuevo_doc)
            
        db.session.commit()
        print("¡Exito! Se han inyectado 4 documentos clave a la Base de Conocimiento.")

if __name__ == '__main__':
    inyectar_documentos()
