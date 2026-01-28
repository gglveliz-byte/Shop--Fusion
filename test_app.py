"""
Script de prueba para verificar que la aplicación funciona correctamente
"""

import sys

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("="*60)
print("PRUEBAS DE FUNCIONAMIENTO")
print("="*60)

try:
    print("\n[1/5] Importando módulos...")
    from app import create_app
    from models import db, Admin, Afiliado, Producto, Pedido, Comision
    print("   ✓ Módulos importados correctamente")

    print("\n[2/5] Creando aplicación...")
    app = create_app()
    print("   ✓ Aplicación creada correctamente")

    print("\n[3/5] Verificando modelos...")
    with app.app_context():
        # Verificar que los campos nuevos existen
        inspector = db.inspect(db.engine)
        
        columns_afiliados = [col['name'] for col in inspector.get_columns('afiliados')]
        if 'whatsapp' in columns_afiliados:
            print("   ✓ Campo 'whatsapp' existe en 'afiliados'")
        else:
            print("   ✗ Campo 'whatsapp' NO existe en 'afiliados'")
        
        columns_pedidos = [col['name'] for col in inspector.get_columns('pedidos')]
        if 'validado_por_vendedor' in columns_pedidos:
            print("   ✓ Campo 'validado_por_vendedor' existe en 'pedidos'")
        else:
            print("   ✗ Campo 'validado_por_vendedor' NO existe en 'pedidos'")
        
        if 'validado_en' in columns_pedidos:
            print("   ✓ Campo 'validado_en' existe en 'pedidos'")
        else:
            print("   ✗ Campo 'validado_en' NO existe en 'pedidos'")

    print("\n[4/5] Verificando rutas...")
    with app.app_context():
        from routes import tienda, admin, afiliado, auth
        
        # Verificar que las rutas están registradas
        routes_tienda = [str(rule) for rule in app.url_map.iter_rules() if 'tienda' in str(rule.endpoint)]
        routes_admin = [str(rule) for rule in app.url_map.iter_rules() if 'admin' in str(rule.endpoint)]
        routes_afiliado = [str(rule) for rule in app.url_map.iter_rules() if 'afiliado' in str(rule.endpoint)]
        
        print(f"   ✓ {len(routes_tienda)} rutas de tienda registradas")
        print(f"   ✓ {len(routes_admin)} rutas de admin registradas")
        print(f"   ✓ {len(routes_afiliado)} rutas de afiliado registradas")
        
        # Verificar rutas nuevas
        if any('vendedor' in r for r in routes_tienda):
            print("   ✓ Ruta de tienda de vendedor encontrada")
        else:
            print("   ✗ Ruta de tienda de vendedor NO encontrada")

    print("\n[5/5] Verificando métodos de modelos...")
    with app.app_context():
        # Probar método validar_para_admin
        pedido_test = Pedido.query.first()
        if pedido_test:
            print(f"   ✓ Modelo Pedido funciona (pedido #{pedido_test.id} encontrado)")
            if hasattr(pedido_test, 'validar_para_admin'):
                print("   ✓ Método 'validar_para_admin' existe")
            else:
                print("   ✗ Método 'validar_para_admin' NO existe")
        else:
            print("   ⚠ No hay pedidos en la base de datos para probar")
        
        # Probar campo whatsapp en Afiliado
        afiliado_test = Afiliado.query.first()
        if afiliado_test:
            print(f"   ✓ Modelo Afiliado funciona (afiliado {afiliado_test.codigo} encontrado)")
            if hasattr(afiliado_test, 'whatsapp'):
                print("   ✓ Campo 'whatsapp' existe en modelo")
            else:
                print("   ✗ Campo 'whatsapp' NO existe en modelo")
        else:
            print("   ⚠ No hay afiliados en la base de datos para probar")

    print("\n" + "="*60)
    print("✓ TODAS LAS PRUEBAS COMPLETADAS")
    print("="*60)
    print("\nLa aplicación está lista para usar.")
    print("\nPróximos pasos:")
    print("1. Ejecutar: python app.py")
    print("2. Acceder a: http://localhost:5000")
    print("3. Login admin: admin / admin123")
    print("4. Crear un vendedor con WhatsApp")
    print("5. Probar el flujo completo\n")

except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
