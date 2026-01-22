"""
Script de migracion para agregar columnas de URL de imagenes a productos
Ejecutar una sola vez: python migrate_imagen_url.py
"""

import os
import sys

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

def migrate():
    """Agregar columnas imagen_url e imagenes_url a la tabla productos"""
    app = create_app()

    with app.app_context():
        try:
            # Verificar si las columnas ya existen
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'productos'
                AND column_name IN ('imagen_url', 'imagenes_url')
            """))
            existing_columns = [row[0] for row in result.fetchall()]

            # Agregar imagen_url si no existe
            if 'imagen_url' not in existing_columns:
                print("Agregando columna imagen_url...")
                db.session.execute(text("""
                    ALTER TABLE productos
                    ADD COLUMN imagen_url VARCHAR(500)
                """))
                print("Columna imagen_url agregada correctamente")
            else:
                print("Columna imagen_url ya existe")

            # Agregar imagenes_url si no existe
            if 'imagenes_url' not in existing_columns:
                print("Agregando columna imagenes_url...")
                db.session.execute(text("""
                    ALTER TABLE productos
                    ADD COLUMN imagenes_url JSON DEFAULT '[]'
                """))
                print("Columna imagenes_url agregada correctamente")
            else:
                print("Columna imagenes_url ya existe")

            db.session.commit()
            print("\nMigracion completada exitosamente!")
            print("Ahora puedes agregar productos con URLs de imagenes.")

        except Exception as e:
            db.session.rollback()
            print(f"Error durante la migracion: {e}")
            raise

if __name__ == '__main__':
    migrate()
