"""
Script de migración para agregar nuevos campos sin eliminar datos
Ejecutar: python migrate_db.py
"""

import sys

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from app import create_app
from models import db, Afiliado, Pedido
from sqlalchemy import text

def migrate_database():
    """Agregar nuevos campos a las tablas existentes"""
    app = create_app()

    with app.app_context():
        print("="*60)
        print("MIGRACIÓN DE BASE DE DATOS")
        print("="*60)
        print("\nEste script agregará los siguientes campos:")
        print("  - afiliados.whatsapp (VARCHAR)")
        print("  - pedidos.validado_por_vendedor (BOOLEAN)")
        print("  - pedidos.validado_en (DATETIME)")
        print("\n⚠️  NO se eliminarán datos existentes")
        print("="*60)
        
        try:
            # Verificar si los campos ya existen
            inspector = db.inspect(db.engine)
            columns_afiliados = [col['name'] for col in inspector.get_columns('afiliados')]
            columns_pedidos = [col['name'] for col in inspector.get_columns('pedidos')]

            # Agregar campo whatsapp a afiliados
            if 'whatsapp' not in columns_afiliados:
                print("\n[1/3] Agregando campo 'whatsapp' a tabla 'afiliados'...")
                db.session.execute(text("ALTER TABLE afiliados ADD COLUMN whatsapp VARCHAR(20)"))
                db.session.commit()
                print("   ✓ Campo 'whatsapp' agregado exitosamente")
            else:
                print("\n[1/3] Campo 'whatsapp' ya existe en 'afiliados'")

            # Agregar campo validado_por_vendedor a pedidos
            if 'validado_por_vendedor' not in columns_pedidos:
                print("\n[2/3] Agregando campo 'validado_por_vendedor' a tabla 'pedidos'...")
                db.session.execute(text("ALTER TABLE pedidos ADD COLUMN validado_por_vendedor BOOLEAN DEFAULT FALSE"))
                db.session.commit()
                print("   ✓ Campo 'validado_por_vendedor' agregado exitosamente")
            else:
                print("\n[2/3] Campo 'validado_por_vendedor' ya existe en 'pedidos'")

            # Agregar campo validado_en a pedidos
            if 'validado_en' not in columns_pedidos:
                print("\n[3/3] Agregando campo 'validado_en' a tabla 'pedidos'...")
                # PostgreSQL usa TIMESTAMP, MySQL/MariaDB usa DATETIME
                db_type = db.engine.dialect.name
                if db_type == 'postgresql':
                    db.session.execute(text("ALTER TABLE pedidos ADD COLUMN validado_en TIMESTAMP"))
                else:
                    db.session.execute(text("ALTER TABLE pedidos ADD COLUMN validado_en DATETIME"))
                db.session.commit()
                print("   ✓ Campo 'validado_en' agregado exitosamente")
            else:
                print("\n[3/3] Campo 'validado_en' ya existe en 'pedidos'")

            print("\n" + "="*60)
            print("✓ MIGRACIÓN COMPLETADA EXITOSAMENTE")
            print("="*60)
            print("\nTodos los campos han sido agregados sin perder datos.")
            print("Puedes continuar usando la aplicación normalmente.\n")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERROR durante la migración: {str(e)}")
            print("\nSi el error indica que el campo ya existe, puedes ignorarlo.")
            print("Si es otro error, revisa la conexión a la base de datos.\n")
            return False

    return True

if __name__ == '__main__':
    migrate_database()
