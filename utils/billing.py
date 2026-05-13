from decimal import Decimal, ROUND_HALF_UP
from models import Pedido, Configuracion

def calculate_invoice_data(pedido):
    """
    Calcula el desglose de impuestos para una factura basado en un pedido.
    Retorna un diccionario con: subtotal, iva_porcentaje, iva_monto, total.
    """
    # 1. Obtener la configuración actual para saber el porcentaje de IVA
    config = Configuracion.query.first()
    iva_porcentaje = Decimal(str(config.iva_porcentaje if config else 15.00))
    
    # 2. Obtener el total del pedido
    # Asumimos que el total del pedido es el monto final a pagar (incluye impuestos)
    total_pedido = Decimal(str(pedido.total))
    
    # 3. Calcular desglose (Fórmula para desglosar IVA: Total / (1 + %IVA))
    # Ejemplo: Si total es 115 y IVA es 15%, el subtotal es 115 / 1.15 = 100
    divisor = Decimal('1') + (iva_porcentaje / Decimal('100'))
    subtotal = (total_pedido / divisor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # 4. Calcular el monto exacto del impuesto
    iva_monto = (total_pedido - subtotal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    return {
        "subtotal": subtotal,
        "iva_porcentaje": iva_porcentaje,
        "iva_monto": iva_monto,
        "total": total_pedido
    }

def format_currency(value):
    """Formatea un valor decimal como moneda para el HTML"""
    return f"${value:,.2f}"
