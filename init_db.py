"""
Script para inicializar la base de datos
Crea las tablas y un usuario administrador por defecto
"""

import sys

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from app import create_app
from models import db, Admin, Afiliado, Producto

def init_database():
    """Inicializar base de datos y crear admin por defecto"""
    app = create_app()

    with app.app_context():
        print("Creando tablas en la base de datos...")

        # Eliminar tablas existentes (¡CUIDADO en producción!)
        db.drop_all()

        # Crear todas las tablas
        db.create_all()

        print("[OK] Tablas creadas exitosamente:")
        print("   - admins")
        print("   - afiliados")
        print("   - productos")
        print("   - pedidos")
        print("   - comisiones")

        # Verificar si ya existe un admin
        admin_existente = Admin.query.filter_by(username='admin').first()

        if not admin_existente:
            # Crear administrador por defecto
            admin = Admin(username='admin')
            admin.set_password('admin123')  # CAMBIAR EN PRODUCCIÓN

            db.session.add(admin)
            db.session.commit()

            print("\n[OK] Administrador creado:")
            print(f"   Usuario: admin")
            print(f"   Contraseña: admin123")
            print("\n[IMPORTANTE] Cambia la contrasena en produccion")
        else:
            print("\n[OK] Admin ya existe en la base de datos")

        # Crear algunos productos de ejemplo
        productos_ejemplo = [
            {
                'nombre': 'Zapatos Nike Air Max',
                'descripcion': 'Zapatos deportivos de alta calidad con tecnología Air Max',
                'precio_final': 50.00,
                'precio_proveedor': 25.00,
                'precio_oferta': None,
                'imagen': 'zapatos-nike.jpg',
                'activo': True
            },
            {
                'nombre': 'Camiseta Adidas',
                'descripcion': 'Camiseta deportiva 100% algodón',
                'precio_final': 30.00,
                'precio_proveedor': 15.00,
                'precio_oferta': 25.00,
                'imagen': 'camiseta-adidas.jpg',
                'activo': True
            },
            {
                'nombre': 'Pantalón Deportivo Puma',
                'descripcion': 'Pantalón cómodo para entrenamiento',
                'precio_final': 40.00,
                'precio_proveedor': 20.00,
                'precio_oferta': None,
                'imagen': 'pantalon-puma.jpg',
                'activo': True
            }
        ]

        if Producto.query.count() == 0:
            print("\nCreando productos de ejemplo...")
            for prod_data in productos_ejemplo:
                producto = Producto(**prod_data)
                db.session.add(producto)

            db.session.commit()
            print(f"[OK] {len(productos_ejemplo)} productos creados")

        # Crear un afiliado de ejemplo
        if Afiliado.query.count() == 0:
            print("\nCreando afiliado de ejemplo...")
            afiliado = Afiliado(
                nombre='Juan Perez',
                email='juan@email.com',
                codigo='AFI001',
                porcentaje_comision=80.00,
                activo=True
            )
            afiliado.set_password('afiliado123')
            db.session.add(afiliado)
            db.session.commit()

            print("[OK] Afiliado creado:")
            print(f"   Nombre: Juan Perez")
            print(f"   Email: juan@email.com")
            print(f"   Codigo: AFI001")
            print(f"   Comision: 80%")
            print(f"   Contrasena: afiliado123")

        print("\n" + "="*50)
        print("[OK] BASE DE DATOS INICIALIZADA CORRECTAMENTE")
        print("="*50)
        print("\nPuedes iniciar la aplicacion con: python app.py")

if __name__ == '__main__':
    init_database()
