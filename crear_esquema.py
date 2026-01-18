"""
Script para crear el esquema shop_fusion en PostgreSQL
"""

import psycopg2
from urllib.parse import urlparse
import os
from dotenv import load_dotenv
import sys

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

def crear_esquema():
    """Crear esquema shop_fusion en la base de datos"""

    # Parsear DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')

    # Limpiar el URL para psycopg2
    if database_url.startswith('postgresql://'):
        # Remover opciones de search_path para la conexión inicial
        database_url_clean = database_url.split('?')[0]

        url = urlparse(database_url_clean)

        print("Conectando a PostgreSQL...")

        try:
            # Conectar a la base de datos
            conn = psycopg2.connect(
                host=url.hostname,
                port=url.port,
                user=url.username,
                password=url.password,
                database=url.path[1:],  # Remover el / inicial
                sslmode='require'
            )

            conn.autocommit = True
            cursor = conn.cursor()

            print("[OK] Conectado exitosamente")

            # Crear esquema shop_fusion si no existe
            print("\nCreando esquema 'shop_fusion'...")
            cursor.execute("CREATE SCHEMA IF NOT EXISTS shop_fusion;")
            print("[OK] Esquema 'shop_fusion' creado/verificado")

            # Dar permisos al usuario actual
            print("\nConfigurando permisos...")
            cursor.execute(f"GRANT ALL ON SCHEMA shop_fusion TO {url.username};")
            cursor.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA shop_fusion GRANT ALL ON TABLES TO {url.username};")
            cursor.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA shop_fusion GRANT ALL ON SEQUENCES TO {url.username};")
            print("[OK] Permisos configurados")

            # Verificar esquemas disponibles
            print("\nEsquemas disponibles en la base de datos:")
            cursor.execute("SELECT schema_name FROM information_schema.schemata;")
            schemas = cursor.fetchall()
            for schema in schemas:
                print(f"   - {schema[0]}")

            cursor.close()
            conn.close()

            print("\n" + "="*50)
            print("[OK] ESQUEMA CREADO CORRECTAMENTE")
            print("="*50)
            print("\nAhora puedes ejecutar: python init_db.py")

        except Exception as e:
            print(f"\n[ERROR] {e}")
            print("\nPosibles soluciones:")
            print("1. Verifica que las credenciales sean correctas")
            print("2. Verifica que tengas permisos de administrador en la BD")
            print("3. Usa SQLite en su lugar (mas simple para desarrollo)")

    else:
        print("[AVISO] No estas usando PostgreSQL. Este script es solo para PostgreSQL.")
        print("Si quieres usar SQLite, cambia DATABASE_URL en .env a:")
        print("DATABASE_URL=sqlite:///shop_fusion.db")

if __name__ == '__main__':
    crear_esquema()
