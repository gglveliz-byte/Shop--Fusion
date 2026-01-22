"""
Script para migrar productos existentes y asignarles categorias
Ejecutar una sola vez: python migrate_categorias.py
"""

from app import app, db
from models import Producto

def migrar_categorias():
    with app.app_context():
        # Primero agregar la columna si no existe
        try:
            db.session.execute(db.text("ALTER TABLE productos ADD COLUMN categoria VARCHAR(50) DEFAULT 'otros'"))
            db.session.commit()
            print("Columna 'categoria' agregada exitosamente")
        except Exception as e:
            db.session.rollback()
            print(f"La columna ya existe o error: {e}")

        # Obtener todos los productos
        productos = Producto.query.all()

        # Palabras clave para detectar categorias
        telefonos_keywords = ['samsung', 'galaxy', 'xiaomi', 'redmi', 'tecno', 'infinix', 'honor', 'zte', 'iphone', 'spark', 'hot', 'note', 'smart']
        computadoras_keywords = ['hp', 'lenovo', 'dell', 'asus', 'vivobook', 'ideapad', 'inspiron', 'tuf', 'gaming', 'laptop', 'core i', 'ryzen', 'celeron', 'loq']
        ropa_keywords = ['camiseta', 'pantalon', 'camisa', 'chaqueta', 'vestido', 'falda', 'short', 'polo', 'sudadera', 'adidas', 'puma', 'nike clothing', 'deportivo']
        zapatos_keywords = ['zapato', 'zapatilla', 'tenis', 'bota', 'sandalia', 'nike air', 'air max', 'jordan']

        actualizados = 0

        for producto in productos:
            nombre_lower = producto.nombre.lower()
            categoria_detectada = 'otros'

            # Detectar categoria por palabras clave
            # Primero verificar zapatos (Nike Air Max es zapatos, no ropa)
            for keyword in zapatos_keywords:
                if keyword in nombre_lower:
                    categoria_detectada = 'zapatos'
                    break

            # Si no es zapatos, verificar otras categorias
            if categoria_detectada == 'otros':
                for keyword in telefonos_keywords:
                    if keyword in nombre_lower:
                        categoria_detectada = 'telefonos'
                        break

            if categoria_detectada == 'otros':
                for keyword in computadoras_keywords:
                    if keyword in nombre_lower:
                        categoria_detectada = 'computadoras'
                        break

            if categoria_detectada == 'otros':
                for keyword in ropa_keywords:
                    if keyword in nombre_lower:
                        categoria_detectada = 'ropa'
                        break

            # Actualizar producto
            producto.categoria = categoria_detectada
            actualizados += 1
            # Evitar caracteres especiales en el print
            nombre_safe = producto.nombre.encode('ascii', 'replace').decode('ascii')
            print(f"  {producto.id}: {nombre_safe} -> {categoria_detectada}")

        db.session.commit()
        print(f"\n{actualizados} productos actualizados con sus categorias")

        # Mostrar resumen
        print("\n=== RESUMEN POR CATEGORIA ===")
        for cat in ['telefonos', 'computadoras', 'ropa', 'zapatos', 'perfumes', 'herramientas', 'hogar', 'electronica', 'accesorios', 'otros']:
            count = Producto.query.filter_by(categoria=cat).count()
            if count > 0:
                print(f"  {cat}: {count} productos")

if __name__ == '__main__':
    migrar_categorias()
