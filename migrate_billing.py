"""
Script de migración para el Módulo de Facturación
Agrega la tabla 'facturas' y el campo 'iva_porcentaje'
Ejecutar: python migrate_billing.py
"""

from app import create_app
from models import db, Factura
from sqlalchemy import text

def migrate_billing():
    app = create_app()

    with app.app_context():
        print("="*60)
        print("MIGRACIÓN: MÓDULO DE FACTURACIÓN")
        print("="*60)
        
        try:
            # 1. Crear nuevas tablas (esto solo crea las que NO existen)
            db.create_all()
            print("\n[1/2] Verificando creación de tabla 'facturas'...")
            print("   ✓ Tabla 'facturas' procesada.")

            # 2. Agregar campo iva_porcentaje a configuraciones
            inspector = db.inspect(db.engine)
            columns_config = [col['name'] for col in inspector.get_columns('configuraciones')]

            if 'iva_porcentaje' not in columns_config:
                print("\n[2/2] Agregando campo 'iva_porcentaje' a 'configuraciones'...")
                db.session.execute(text("ALTER TABLE configuraciones ADD COLUMN iva_porcentaje DECIMAL(5,2) DEFAULT 15.00"))
                db.session.commit()
                print("   ✓ Columna 'iva_porcentaje' agregada exitosamente.")
            else:
                print("\n[2/2] Campo 'iva_porcentaje' ya existe.")

            print("\n" + "="*60)
            print("✓ MIGRACIÓN DE FACTURACIÓN COMPLETADA")
            print("="*60)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERROR: {str(e)}")

if __name__ == '__main__':
    migrate_billing()
