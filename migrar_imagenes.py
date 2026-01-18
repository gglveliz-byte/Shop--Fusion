# -*- coding: utf-8 -*-
"""
Migración: Agregar campo 'imagenes' a la tabla productos
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from app import create_app, db

app = create_app()

with app.app_context():
    print("\n" + "="*60)
    print("MIGRANDO BASE DE DATOS: Agregando campo 'imagenes'")
    print("="*60 + "\n")

    try:
        # Ejecutar SQL para agregar columna si no existe
        with db.engine.connect() as conn:
            # Verificar si la columna ya existe
            result = conn.execute(db.text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'shop_fusion'
                AND table_name = 'productos'
                AND column_name = 'imagenes'
            """))

            if result.fetchone():
                print("[INFO] La columna 'imagenes' ya existe en la tabla productos")
            else:
                # Agregar columna
                conn.execute(db.text("""
                    ALTER TABLE shop_fusion.productos
                    ADD COLUMN imagenes JSON DEFAULT '[]'::json
                """))
                conn.commit()
                print("[OK] Columna 'imagenes' agregada exitosamente")

        print("\n" + "="*60)
        print("MIGRACIÓN COMPLETADA")
        print("="*60)

    except Exception as e:
        print(f"\n[ERROR] Error en la migración: {e}")
        import traceback
        traceback.print_exc()
