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

        # Obtener credenciales desde la configuración (que lee del .env)
        # NUEVA LÓGICA SEGURA (FASE 1): Creación de administrador desde variables de entorno (.env).
        # Sirve para: Eliminar credenciales hardcoded y prevenir exposición de claves en consola.
        # Afecta a: Proceso de inicialización (requiere configurar el .env previamente).
        env_user = app.config.get('ADMIN_USER')
        env_pass = app.config.get('ADMIN_PASS')

        if not env_user or not env_pass:
            print("\n[AVISO DE SEGURIDAD] No se detectaron ADMIN_USER o ADMIN_PASS en el .env")
            print("El script continuará creando productos, pero no se generará un administrador inseguro.")
        else:
            admin_existente = Admin.query.filter_by(username=env_user).first()
            if not admin_existente:
                admin = Admin(username=env_user)
                admin.set_password(env_pass)
                db.session.add(admin)
                db.session.commit()
                print(f"\n[OK] Administrador '{env_user}' creado exitosamente desde el .env")
            else:
                print(f"\n[OK] El administrador '{env_user}' ya existe en la base de datos")

        # --- CÓDIGO ORIGINAL COMENTADO Y REEMPLAZADO POR SEGURIDAD (Error E10 / E4) ---
        """
        admin_existente = Admin.query.filter_by(username='admin').first()
        if not admin_existente:
            admin = Admin(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("\n[OK] Administrador creado: admin / admin123")
        """

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

        # SEGURIDAD (FASE 1): Se deshabilita la creación de afiliados de ejemplo con claves hardcoded.
        # Sirve para: Evitar el Error E10 y asegurar que todos los afiliados sean creados con claves seguras.
        print("\n[AVISO] No se crearán afiliados de ejemplo por razones de seguridad (Error E10).")
        print("Utiliza el panel de administrador para registrar afiliados con credenciales seguras.")

        # --- CÓDIGO ORIGINAL COMENTADO Y REEMPLAZADO POR SEGURIDAD (Error E10 / E4) ---
        """
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
        """

        print("\n" + "="*50)
        print("[OK] BASE DE DATOS INICIALIZADA CORRECTAMENTE")
        print("="*50)
        print("\nPuedes iniciar la aplicacion con: python app.py")

if __name__ == '__main__':
    init_database()
