import calendar
from datetime import datetime, timedelta, time
from decimal import Decimal
from models import db, Pedido, Producto, Transaccion, Factura

def _get_date_range(period):
    """
    Helper para calcular el rango de fechas UTC correspondiente a un periodo legible.
    Retorna (start_date, end_date) como datetime.
    """
    now = datetime.utcnow()
    # Inicio de hoy a las 00:00:00
    today_start = datetime.combine(now.date(), time.min)
    
    if period == 'today':
        start = today_start
        end = now
    elif period == 'this_week':
        # weekday() es 0 para lunes, 6 para domingo
        start = today_start - timedelta(days=now.weekday())
        end = now
    elif period == 'this_month':
        start = datetime(now.year, now.month, 1)
        end = now
    elif period == 'last_month':
        if now.month == 1:
            start = datetime(now.year - 1, 12, 1)
            end = datetime(now.year - 1, 12, 31, 23, 59, 59)
        else:
            start = datetime(now.year, now.month - 1, 1)
            last_day = calendar.monthrange(now.year, now.month - 1)[1]
            end = datetime(now.year, now.month - 1, last_day, 23, 59, 59)
    elif period == 'this_year':
        start = datetime(now.year, 1, 1)
        end = now
    else:
        # Default a este mes si no se reconoce el periodo
        start = datetime(now.year, now.month, 1)
        end = now
        
    return start, end

def get_sales_report(period='this_month'):
    """
    Genera un informe detallado de ventas, márgenes y rendimiento del negocio.
    period: 'today', 'this_week', 'this_month', 'last_month', 'this_year'
    """
    start, end = _get_date_range(period)
    
    # 1. Obtener todos los pedidos pagados en el periodo
    pedidos_pagados = Pedido.query.filter(
        Pedido.estado == 'pagado',
        Pedido.creado_en >= start,
        Pedido.creado_en <= end
    ).all()
    
    ventas_totales = Decimal('0.00')
    cantidad_pedidos = len(pedidos_pagados)
    costo_proveedor_total = Decimal('0.00')
    
    for ped in pedidos_pagados:
        ventas_totales += ped.total
        
        # Desglosar los productos para calcular costo del proveedor (COGS)
        for item in ped.productos_json:
            p_id = item.get('id')
            cant = int(item.get('cantidad', 0))
            precio_unitario = Decimal(str(item.get('precio', 0)))
            
            # Buscar el producto en la BD para obtener su costo real
            prod = Producto.query.get(p_id)
            if prod:
                c_proveedor = prod.precio_proveedor
            else:
                # Fallback: si el producto ya no existe, estimamos un 50% de costo
                c_proveedor = precio_unitario / Decimal('2.0')
                
            costo_proveedor_total += c_proveedor * Decimal(str(cant))
            
    margen_ventas = ventas_totales - costo_proveedor_total
    ticket_promedio = ventas_totales / Decimal(str(cantidad_pedidos)) if cantidad_pedidos > 0 else Decimal('0.00')
    
    # 2. Integración con el Módulo Contable (Transacciones de Caja/Bancos)
    transacciones = Transaccion.query.filter(
        Transaccion.fecha >= start,
        Transaccion.fecha <= end
    ).all()
    
    ingresos_contables = Decimal('0.00')
    gastos_contables = Decimal('0.00')
    ingresos_por_categoria = {}
    gastos_por_categoria = {}
    
    for tx in transacciones:
        monto = tx.monto
        cat = tx.categoria or 'otros'
        
        if tx.tipo == 'ingreso':
            ingresos_contables += monto
            ingresos_por_categoria[cat] = ingresos_por_categoria.get(cat, Decimal('0.00')) + monto
        elif tx.tipo == 'gasto':
            gastos_contables += monto
            gastos_por_categoria[cat] = gastos_por_categoria.get(cat, Decimal('0.00')) + monto
            
    balance_contable_neto = ingresos_contables - gastos_contables
    
    return {
        "periodo": period,
        "rango": {
            "inicio": start.strftime('%Y-%m-%d %H:%M:%S'),
            "fin": end.strftime('%Y-%m-%d %H:%M:%S')
        },
        "ventas": {
            "ventas_totales": float(ventas_totales),
            "cantidad_pedidos": cantidad_pedidos,
            "ticket_promedio": float(ticket_promedio),
            "costo_proveedor_total": float(costo_proveedor_total),
            "margen_ventas": float(margen_ventas),
            "margen_porcentaje": float((margen_ventas / ventas_totales) * Decimal('100.0')) if ventas_totales > 0 else 0.0
        },
        "contabilidad": {
            "total_ingresos": float(ingresos_contables),
            "total_gastos": float(gastos_contables),
            "balance_neto": float(balance_contable_neto),
            "ingresos_por_categoria": {k: float(v) for k, v in ingresos_por_categoria.items()},
            "gastos_por_categoria": {k: float(v) for k, v in gastos_por_categoria.items()}
        }
    }

def _calcular_variacion(valor_actual, valor_anterior):
    """Calcula el porcentaje de variación entre dos valores financieros."""
    val_act = Decimal(str(valor_actual))
    val_ant = Decimal(str(valor_anterior))
    if val_ant == 0:
        return 100.0 if val_act > 0 else 0.0
    return float(((val_act - val_ant) / val_ant) * Decimal('100.0'))

def compare_periods(period1, period2):
    """
    Compara dos periodos financieros para analizar el crecimiento o retroceso.
    Ejemplo: compare_periods('this_month', 'last_month')
    """
    report1 = get_sales_report(period1)
    report2 = get_sales_report(period2)
    
    v_totales1 = report1["ventas"]["ventas_totales"]
    v_totales2 = report2["ventas"]["ventas_totales"]
    
    margen1 = report1["ventas"]["margen_ventas"]
    margen2 = report2["ventas"]["margen_ventas"]
    
    pedidos1 = report1["ventas"]["cantidad_pedidos"]
    pedidos2 = report2["ventas"]["cantidad_pedidos"]
    
    ticket1 = report1["ventas"]["ticket_promedio"]
    ticket2 = report2["ventas"]["ticket_promedio"]
    
    return {
        "periodo_actual": period1,
        "periodo_anterior": period2,
        "comparativa": {
            "ventas": {
                "actual": v_totales1,
                "anterior": v_totales2,
                "variacion_porcentaje": _calcular_variacion(v_totales1, v_totales2)
            },
            "margen": {
                "actual": margen1,
                "anterior": margen2,
                "variacion_porcentaje": _calcular_variacion(margen1, margen2)
            },
            "pedidos": {
                "actual": pedidos1,
                "anterior": pedidos2,
                "variacion_porcentaje": _calcular_variacion(pedidos1, pedidos2)
            },
            "ticket_promedio": {
                "actual": ticket1,
                "anterior": ticket2,
                "variacion_porcentaje": _calcular_variacion(ticket1, ticket2)
            }
        }
    }

def get_top_products(limit=5):
    """
    Rankea los productos estrella basados en la cantidad vendida en pedidos pagados históricos.
    Calcula ingresos totales y márgenes netos de ganancia agregados.
    """
    # Acumulamos estadísticas en memoria para todos los productos de pedidos pagados
    stats = {}
    
    pedidos_pagados = Pedido.query.filter_by(estado='pagado').all()
    
    for ped in pedidos_pagados:
        for item in ped.productos_json:
            p_id = item.get('id')
            nombre = item.get('nombre', 'Producto Desconocido')
            cant = int(item.get('cantidad', 0))
            precio = Decimal(str(item.get('precio', 0)))
            
            # Obtener costo del proveedor
            prod = Producto.query.get(p_id)
            c_proveedor = prod.precio_proveedor if prod else (precio / Decimal('2.0'))
            
            if p_id not in stats:
                stats[p_id] = {
                    "id": p_id,
                    "nombre": nombre,
                    "cantidad_vendida": 0,
                    "ingresos_totales": Decimal('0.00'),
                    "costo_proveedor_total": Decimal('0.00'),
                    "margen_neto_total": Decimal('0.00'),
                    "stock_actual": prod.stock if prod else 0
                }
                
            stats[p_id]["cantidad_vendida"] += cant
            stats[p_id]["ingresos_totales"] += precio * Decimal(str(cant))
            stats[p_id]["costo_proveedor_total"] += c_proveedor * Decimal(str(cant))
            stats[p_id]["margen_neto_total"] = stats[p_id]["ingresos_totales"] - stats[p_id]["costo_proveedor_total"]
            
    # Convertir a lista y ordenar descendentemente por cantidad vendida
    ranking = list(stats.values())
    ranking.sort(key=lambda x: x["cantidad_vendida"], reverse=True)
    
    # Formatear Decimals a floats para una salida JSON limpia
    for item in ranking:
        item["ingresos_totales"] = float(item["ingresos_totales"])
        item["costo_proveedor_total"] = float(item["costo_proveedor_total"])
        item["margen_neto_total"] = float(item["margen_neto_total"])
        
    return ranking[:limit]
