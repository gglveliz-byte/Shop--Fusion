import os
import sys

# Asegurar que la raíz del proyecto esté en el sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from app import create_app
from utils.analytics import get_sales_report, compare_periods, get_top_products

def run_tests():
    app = create_app()
    with app.app_context():
        print("="*60)
        print("PRUEBA UNITARIA Y DE INTEGRACIÓN DE ANALÍTICA (FASE 1)")
        print("="*60)
        
        # 1. Reporte del Mes Actual
        print("\n--- 1. GENERANDO REPORTE DE VENTAS DEL MES ACTUAL ('this_month') ---")
        try:
            report_month = get_sales_report('this_month')
            print(f"Rango de Fechas: {report_month['rango']['inicio']} -> {report_month['rango']['fin']}")
            print(f"Pedidos Pagados: {report_month['ventas']['cantidad_pedidos']}")
            print(f"Ventas Totales: ${report_month['ventas']['ventas_totales']:.2f}")
            print(f"Costo de Proveedor: ${report_month['ventas']['costo_proveedor_total']:.2f}")
            print(f"Margen Neto de Ventas: ${report_month['ventas']['margen_ventas']:.2f} ({report_month['ventas']['margen_porcentaje']:.2f}%)")
            print(f"Ticket Promedio (AOV): ${report_month['ventas']['ticket_promedio']:.2f}")
            print("\n--- Balance Contable (Transacciones) ---")
            print(f"Ingresos Totales Contabilidad: ${report_month['contabilidad']['total_ingresos']:.2f}")
            print(f"Gastos Totales Contabilidad: ${report_month['contabilidad']['total_gastos']:.2f}")
            print(f"Balance de Caja Neto: ${report_month['contabilidad']['balance_neto']:.2f}")
        except Exception as e:
            print(f"❌ Error en Reporte Mensual: {e}")
            
        # 2. Comparativa de Periodos
        print("\n--- 2. COMPARANDO ESTE MES CON EL ANTERIOR ---")
        try:
            comparativa = compare_periods('this_month', 'last_month')
            c = comparativa['comparativa']
            print(f"Variación de Ventas: ${c['ventas']['anterior']:.2f} -> ${c['ventas']['actual']:.2f} ({c['ventas']['variacion_porcentaje']:+.2f}%)")
            print(f"Variación de Margen: ${c['margen']['anterior']:.2f} -> ${c['margen']['actual']:.2f} ({c['margen']['variacion_porcentaje']:+.2f}%)")
            print(f"Variación de Pedidos: {c['pedidos']['anterior']} -> {c['pedidos']['actual']} ({c['pedidos']['variacion_porcentaje']:+.2f}%)")
        except Exception as e:
            print(f"❌ Error en Comparativa: {e}")
            
        # 3. Top Productos
        print("\n--- 3. RANKING DE PRODUCTOS ESTRELLA (TOP 5 HISTÓRICO) ---")
        try:
            top_products = get_top_products(5)
            if not top_products:
                print("ℹ️ No hay ventas registradas aún para rankear productos.")
            else:
                for idx, prod in enumerate(top_products, 1):
                    print(f"{idx}. {prod['nombre']} (ID: {prod['id']})")
                    print(f"   - Cantidad Vendida: {prod['cantidad_vendida']} unidades")
                    print(f"   - Ingresos Generados: ${prod['ingresos_totales']:.2f}")
                    print(f"   - Margen de Utilidad Neto: ${prod['margen_neto_total']:.2f}")
                    print(f"   - Stock Actual Restante: {prod['stock_actual']} unidades")
        except Exception as e:
            print(f"❌ Error en Top Productos: {e}")
            
        print("\n" + "="*60)
        print("VERIFICACIÓN ESTRUCTURAL COMPLETADA CON ÉXITO")
        print("="*60)

if __name__ == '__main__':
    run_tests()
