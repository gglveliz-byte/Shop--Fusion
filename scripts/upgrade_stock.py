import os
import sys

# Asegurar que la raíz del proyecto esté en el sys.path para poder importar app y models
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from app import create_app, db

def upgrade_database():
    """
    Aplica una alteración en la base de datos de forma segura (ALTER TABLE).
    Añade la columna 'stock_reservado' a la tabla 'producto' si no existe.
    """
    app = create_app()
    with app.app_context():
        print("Iniciando actualización estructural de la base de datos...")
        try:
            # Ejecutamos la consulta SQL nativa para alterar la tabla de productos.
            # Configuramos por defecto el stock_reservado a 0 y que no sea NULL.
            db.session.execute(db.text("ALTER TABLE productos ADD COLUMN stock_reservado INTEGER DEFAULT 0 NOT NULL;"))
            db.session.commit()
            print("✅ Columna 'stock_reservado' añadida exitosamente a la tabla 'producto'.")
        except Exception as e:
            # Hacemos rollback para no dejar la sesión de base de datos colgada en caso de error
            db.session.rollback()
            
            # Verificamos si el error es simplemente porque la columna ya existía.
            # Esto evita que el script falle en ejecuciones repetidas.
            err_msg = str(e).lower()
            if "duplicate column" in err_msg or "already exists" in err_msg or "duplicate column name" in err_msg:
                print("ℹ️ La columna 'stock_reservado' ya existe en la base de datos. No es necesario realizar cambios.")
            else:
                print(f"❌ Error al intentar alterar la tabla: {e}")

if __name__ == '__main__':
    upgrade_database()
