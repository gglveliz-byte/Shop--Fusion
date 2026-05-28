import threading
from flask import current_app
from sqlalchemy import func
from models import db, Producto
from utils.security_logger import log_security_event

# [FASE 2 - HERRAMIENTA INVENTARIO EN TIEMPO REAL] Paso 2.1: Creación del Módulo de Inventario
def _release_stock(product_id, quantity, app):
    """
    Función interna (Callback) que se ejecuta de forma invisible cuando el cronómetro llega a cero.
    Sirve para devolver el stock bloqueado a la disponibilidad general.
    """
    # Como los Hilos (Threads) corren fuera del flujo normal de Flask, 
    # necesitamos decirle explícitamente que use el contexto original de la aplicación.
    with app.app_context():
        producto = Producto.query.get(product_id)
        # Verificamos que el producto exista y que tenga reservas activas
        if producto and producto.stock_reservado >= quantity:
            producto.stock_reservado -= quantity
            db.session.commit()

# CORRECCIÓN PARA LA HERRAMIENTA DE INVENTARIO INTELIGENTE
def search_product(query):
    """
    Busca productos por nombre o palabra clave.
    Esta función ayuda a la IA a obtener IDs REALES desde la base de datos
    y evita que invente identificadores incorrectos.
    """
    
    # Validar que exista una búsqueda válida
    if not query or not query.strip():
        return {
            "success": False,
            "error": "Debe proporcionar un nombre o palabra clave."
        }

    # Buscar coincidencias ignorando mayúsculas/minúsculas
    productos = Producto.query.filter(
        func.lower(Producto.nombre).contains(query.lower())
    ).all()

    # Si no hay coincidencias
    if not productos:
        return {
            "success": False,
            "error": f"No se encontraron productos relacionados con '{query}'."
        }

    # Retornar lista de coincidencias reales
    return {
        "success": True,
        "matches": [
            {
                "product_id": producto.id,
                "product_name": producto.nombre,
                "stock_total": producto.stock,
                "stock_bloqueado": producto.stock_reservado,
                "stock_libre": producto.stock - producto.stock_reservado,
                "activo": producto.activo
            }
            for producto in productos
        ]
    }

# [FASE 2 - HERRAMIENTA INVENTARIO EN TIEMPO REAL] Paso 2.2: Función de Auditoría
def check_stock(product_id):
    """
    Devuelve la radiografía exacta del inventario de un producto.
    La IA usa esto para informar al cliente sin venderle humo.
    """
    producto = Producto.query.get(product_id)
    if not producto:
        return {"success": False, "error": "Producto no encontrado."}
        
    stock_total = producto.stock
    stock_bloqueado = producto.stock_reservado
    stock_libre = stock_total - stock_bloqueado
    
    return {
        "success": True,
        "product_id": producto.id,
        "product_name": producto.nombre,
        "stock_total": stock_total,
        "stock_bloqueado": stock_bloqueado,
        "stock_libre": stock_libre
    }

# [FASE 2 - HERRAMIENTA INVENTARIO EN TIEMPO REAL] Paso 2.3: Función de Bloqueo Temporal
def reserve_stock(product_id, quantity, minutes=15):
    """
    Atrapa una cantidad de stock durante 'X' minutos.
    Si el cliente no paga en ese tiempo, un cronómetro liberará el stock automáticamente.
    """
    # Validar cantidad correcta
    if quantity <= 0:
        return {
            "success": False,
            "error": "La cantidad a reservar debe ser mayor a 0."
        }

    producto = Producto.query.get(product_id)
    if not producto:
        return {"success": False, "error": "Producto no encontrado."}
        
    # Verificar si el producto está activo
    if not producto.activo:
        return {
            "success": False,
            "error": "El producto se encuentra desactivado."
        }
    
    # Verificar si realmente hay stock libre suficiente para reservar
    if (producto.stock - producto.stock_reservado) < quantity:
        return {"success": False, "error": "Stock libre insuficiente para realizar esta reserva."}
        
    # Sumar la cantidad solicitada a la "caja fuerte" de reservas
    producto.stock_reservado += quantity
    db.session.commit()
    
    # Iniciar el cronómetro en un hilo paralelo (Background Thread)
    # Extraemos el objeto real de Flask para pasárselo al hilo
    app = current_app._get_current_object() 
    
    # threading.Timer requiere segundos, por lo que multiplicamos minutos * 60
    timer = threading.Timer(minutes * 60.0, _release_stock, args=[product_id, quantity, app])
    timer.daemon = True # Garantiza que si apagamos el servidor, el cronómetro muera con él
    timer.start()
    
    return {
        "success": True,
        "message": f"Se han bloqueado temporalmente {quantity} unidades del producto '{producto.nombre}' por {minutes} minutos."
    }

# [FASE 2 - HERRAMIENTA INVENTARIO EN TIEMPO REAL] Paso 2.4: Función de Actualización y Alerta
def update_stock(product_id, delta):
    """
    Aplica una suma o resta definitiva al inventario total de un producto (ej. cuando llega un proveedor o se completa una venta).
    Si el stock cae por debajo del umbral, genera un registro automático de advertencia.
    """
    # Validar que exista un cambio real
    if delta == 0:
        return {
            "success": False,
            "error": "El valor delta no puede ser 0."
        }

    producto = Producto.query.get(product_id)
    if not producto:
        return {"success": False, "error": "Producto no encontrado."}
    
    # Verificar si el producto está activo
    if not producto.activo:
        return {
            "success": False,
            "error": "El producto se encuentra desactivado."
        }
        
    UMBRAL_ALERTA = 5 # Nivel crítico
    
    # Delta puede ser positivo (llegó mercadería) o negativo (salió mercadería)
    nuevo_stock = producto.stock + delta
    
    # Evitar stock negativo
    if nuevo_stock < 0:
        return {
            "success": False,
            "error": "Operación cancelada: El stock no puede quedar en números negativos."
        }

    # Evitar inconsistencias con stock reservado
    if nuevo_stock < producto.stock_reservado:
        return {
            "success": False,
            "error": (
                "Operación cancelada: "
                "El stock total no puede ser menor que el stock reservado."
            )
        }

    # Aplicar la actualización permanente
    producto.stock = nuevo_stock
    db.session.commit()
    
    # Lógica de Alarma: Si el stock bajó y quedó igual o menor al umbral
    if delta < 0 and nuevo_stock <= UMBRAL_ALERTA:
        # Disparamos un registro en el Logger de Seguridad que programamos antes
        log_security_event(
            event_type="ALERTA_INVENTARIO",
            status="CRITICAL",
            details=f"URGENTE: El producto '{producto.nombre}' (ID: {producto.id}) ha caído a un nivel crítico de stock ({nuevo_stock} unidades restantes)."
        )
        alerta_generada = True
    else:
        alerta_generada = False
        
    return {
        "success": True,
        "product_id": producto.id,
        "new_stock": nuevo_stock,
        "alert_triggered": alerta_generada,
        "message": f"Stock actualizado de forma permanente a {nuevo_stock} unidades."
    }