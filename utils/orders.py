from models import db, Pedido, Producto
from decimal import Decimal
from datetime import datetime

def create_order_from_json(order_data):
    """
    Crea un pedido en la base de datos a partir de un diccionario JSON.
    Incluye validación de stock y cálculo de totales.
    
    order_data: {
        'cliente_nombre': str,
        'cliente_telefono': str,
        'cliente_direccion': str,
        'productos': [{'id': int, 'cantidad': int}],
        'afiliado_id': int (opcional)
    }
    """
    try:
        productos_json = []
        total_acumulado = Decimal('0.00')
        
        # 1. Validar productos y stock
        for item in order_data.get('productos', []):
            producto = Producto.query.get(item['id'])
            if not producto:
                return {"success": False, "error": f"Producto con ID {item['id']} no encontrado."}
            
            cantidad = int(item['cantidad'])
            if not producto.esta_disponible(cantidad):
                return {"success": False, "error": f"Stock insuficiente para '{producto.nombre}'. Disponible: {producto.stock}"}
            
            # Preparar datos para el JSON del pedido
            precio_unitario = producto.precio_venta()
            subtotal = precio_unitario * Decimal(str(cantidad))
            
            productos_json.append({
                "id": producto.id,
                "nombre": producto.nombre,
                "cantidad": cantidad,
                "precio": float(precio_unitario)
            })
            
            total_acumulado += subtotal
            
            # 2. Reducir stock inmediatamente (Lógica de la Fase 1)
            producto.reducir_stock(cantidad)

        # 3. Crear el objeto Pedido
        nuevo_pedido = Pedido(
            cliente_nombre=order_data['cliente_nombre'],
            cliente_telefono=order_data['cliente_telefono'],
            cliente_direccion=order_data['cliente_direccion'],
            productos_json=productos_json,
            total=total_acumulado,
            afiliado_id=order_data.get('afiliado_id'),
            estado='pendiente' # Se crea como pendiente hasta que se valide el pago
        )

        db.session.add(nuevo_pedido)
        db.session.commit()

        return {
            "success": True, 
            "pedido_id": nuevo_pedido.id,
            "total": float(total_acumulado),
            "mensaje": f"Pedido #{nuevo_pedido.id} creado exitosamente."
        }

    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}
