from app import create_app
from models import db, ReservaStock, DocumentoConocimiento

# Creamos la aplicación de Flask para tener el contexto de la base de datos
app = create_app()

def crear_tablas_nuevas():
    """
    Este script crea ÚNICAMENTE las tablas que no existen en la base de datos,
    sin borrar ni afectar los datos de las tablas antiguas (Productos, Usuarios, etc).
    """
    with app.app_context():
        print("Iniciando revisión de la base de datos...")
        
        # db.create_all() de SQLAlchemy es inteligente:
        # Solo crea las tablas que faltan (como ReservaStock y DocumentoConocimiento).
        # IGNORA y NO SOBREESCRIBE las tablas que ya existen.
        db.create_all()
        
        print("✅ Las nuevas tablas (ReservaStock y DocumentoConocimiento) han sido creadas con éxito.")
        print("Tus datos anteriores están intactos.")

if __name__ == '__main__':
    crear_tablas_nuevas()
