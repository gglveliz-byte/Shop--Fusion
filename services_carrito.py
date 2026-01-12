"""
Servicios para el sistema de carrito de compras de ShopFusion
- Carritos de usuarios registrados: Base de datos
- Carritos de visitantes: Cookies (límite $50)
"""
import psycopg
from psycopg.rows import dict_row
from urllib.parse import urlparse
from decouple import config
from datetime import datetime, timedelta
import json


def get_db_connection():
    """Conexión a la base de datos - Usa esquema shopfusion"""
    from urllib.parse import unquote
    database_url = config('DATABASE_URL')
    result = urlparse(database_url)
    password = unquote(result.password) if result.password else result.password
    port = result.port if result.port else 5432
    conn = psycopg.connect(
        dbname=result.path[1:],
        user=result.username,
        password=password,
        host=result.hostname,
        port=port,
        sslmode='require',
        row_factory=dict_row
    )
    with conn.cursor() as cur:
        cur.execute("SET search_path TO shopfusion")
    conn.commit()
    return conn


def ensure_carrito_tables():
    """Asegura que las tablas de carrito existan"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Tabla de carritos de usuarios registrados (clientes)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopfusion.carritos_usuarios (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER NOT NULL REFERENCES shopfusion.usuarios(id) ON DELETE CASCADE,
                    producto_id INTEGER NOT NULL REFERENCES shopfusion.productos_vendedor(id) ON DELETE CASCADE,
                    cantidad INTEGER NOT NULL DEFAULT 1 CHECK (cantidad > 0),
                    precio_unitario DECIMAL(10, 2) NOT NULL,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(usuario_id, producto_id)
                );
            """)
            
            # Nota: se eliminó el soporte de carritos para afiliados. Los afiliados
            # solo pueden vender, no comprar, por lo que no se crea la tabla
            # `carritos_afiliados`.
            
            # Índices para mejor rendimiento
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_carritos_usuario_id 
                ON shopfusion.carritos_usuarios(usuario_id);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_carritos_producto_id 
                ON shopfusion.carritos_usuarios(producto_id);
            """)
            
            # Indices para carritos de afiliados omitidos (funcionalidad removida)
            
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        print(f"Error al crear tablas de carrito: {e}")
        return False
    finally:
        conn.close()


def obtener_carrito_usuario(usuario_id):
    """Obtiene el carrito completo de un usuario desde BD"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.id,
                    c.producto_id,
                    c.cantidad,
                    c.precio_unitario,
                    p.titulo as nombre,
                    p.descripcion,
                    p.categoria,
                    p.imagenes,
                    p.stock,
                    p.estado
                FROM shopfusion.carritos_usuarios c
                INNER JOIN shopfusion.productos_vendedor p ON c.producto_id = p.id
                WHERE c.usuario_id = %s AND p.estado = 'activo' AND p.stock > 0
                ORDER BY c.creado_en DESC
            """, (usuario_id,))
            
            items = cur.fetchall()
            
            # Formatear items
            carrito = []
            for item in items:
                # Parsear imágenes
                imagenes = item.get('imagenes', '[]')
                if isinstance(imagenes, str):
                    try:
                        imagenes = json.loads(imagenes) if imagenes.startswith('[') else [imagenes]
                    except:
                        imagenes = [imagenes] if imagenes else []
                elif not isinstance(imagenes, list):
                    imagenes = []
                
                carrito.append({
                    'producto_id': item['producto_id'],
                    'cantidad': item['cantidad'],
                    'precio': float(item['precio_unitario']),
                    'nombre': item['nombre'],
                    'descripcion': item.get('descripcion', ''),
                    'categoria': item.get('categoria', 'General'),
                    'imagen': imagenes[0] if imagenes else '/static/images/placeholder.jpg',
                    'stock': item.get('stock', 0)
                })
            
            return carrito
    except Exception as e:
        print(f"Error al obtener carrito de usuario: {e}")
        return []
    finally:
        conn.close()


def agregar_al_carrito_usuario(usuario_id, producto_id, cantidad=1):
    """Agrega o actualiza un producto en el carrito del usuario"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Verificar que el producto existe y tiene stock
            cur.execute("""
                SELECT id, titulo, precio, precio_oferta, stock, estado
                FROM shopfusion.productos_vendedor
                WHERE id = %s AND estado = 'activo'
            """, (producto_id,))
            
            producto = cur.fetchone()
            if not producto:
                return {'error': 'Producto no encontrado'}
            
            stock_disponible = producto.get('stock', 0)
            precio_final = float(producto.get('precio_oferta') or producto.get('precio') or 0)
            
            # Verificar si ya está en el carrito
            cur.execute("""
                SELECT id, cantidad FROM shopfusion.carritos_usuarios
                WHERE usuario_id = %s AND producto_id = %s
            """, (usuario_id, producto_id))
            
            item_existente = cur.fetchone()
            
            if item_existente:
                # Actualizar cantidad
                nueva_cantidad = item_existente['cantidad'] + cantidad
                if nueva_cantidad > stock_disponible:
                    return {'error': f'Solo hay {stock_disponible} unidades disponibles'}
                
                cur.execute("""
                    UPDATE shopfusion.carritos_usuarios
                    SET cantidad = %s, 
                        precio_unitario = %s,
                        actualizado_en = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (nueva_cantidad, precio_final, item_existente['id']))
            else:
                # Agregar nuevo item
                if cantidad > stock_disponible:
                    return {'error': f'Solo hay {stock_disponible} unidades disponibles'}
                
                cur.execute("""
                    INSERT INTO shopfusion.carritos_usuarios 
                    (usuario_id, producto_id, cantidad, precio_unitario)
                    VALUES (%s, %s, %s, %s)
                """, (usuario_id, producto_id, cantidad, precio_final))
            
            conn.commit()
            
            # Obtener total de items
            cur.execute("""
                SELECT SUM(cantidad) as total_items, COUNT(*) as total_productos
                FROM shopfusion.carritos_usuarios
                WHERE usuario_id = %s
            """, (usuario_id,))
            
            totales = cur.fetchone()
            
            return {
                'success': True,
                'total_items': totales['total_items'] or 0,
                'carrito_count': totales['total_productos'] or 0
            }
    except Exception as e:
        conn.rollback()
        print(f"Error al agregar al carrito: {e}")
        return {'error': 'Error al agregar producto al carrito'}
    finally:
        conn.close()


def actualizar_cantidad_carrito_usuario(usuario_id, producto_id, cantidad):
    """Actualiza la cantidad de un producto en el carrito"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Verificar stock
            cur.execute("""
                SELECT stock, precio, precio_oferta FROM shopfusion.productos_vendedor
                WHERE id = %s AND estado = 'activo'
            """, (producto_id,))
            
            producto = cur.fetchone()
            if not producto:
                return {'error': 'Producto no encontrado'}
            
            stock_disponible = producto.get('stock', 0)
            if cantidad > stock_disponible:
                return {'error': f'Solo hay {stock_disponible} unidades disponibles'}
            
            precio_final = float(producto.get('precio_oferta') or producto.get('precio') or 0)
            
            # Actualizar
            cur.execute("""
                UPDATE shopfusion.carritos_usuarios
                SET cantidad = %s,
                    precio_unitario = %s,
                    actualizado_en = CURRENT_TIMESTAMP
                WHERE usuario_id = %s AND producto_id = %s
            """, (cantidad, precio_final, usuario_id, producto_id))
            
            if cur.rowcount == 0:
                return {'error': 'Producto no encontrado en el carrito'}
            
            conn.commit()
            
            # Calcular totales
            cur.execute("""
                SELECT 
                    SUM(cantidad) as total_items,
                    SUM(cantidad * precio_unitario) as total_precio
                FROM shopfusion.carritos_usuarios
                WHERE usuario_id = %s
            """, (usuario_id,))
            
            totales = cur.fetchone()
            
            return {
                'success': True,
                'total_items': totales['total_items'] or 0,
                'total_precio': float(totales['total_precio'] or 0),
                'precio_unitario': precio_final,
                'precio_total_item': precio_final * cantidad,
                'stock_disponible': stock_disponible
            }
    except Exception as e:
        conn.rollback()
        print(f"Error al actualizar carrito: {e}")
        return {'error': 'Error al actualizar carrito'}
    finally:
        conn.close()


def eliminar_del_carrito_usuario(usuario_id, producto_id):
    """Elimina un producto del carrito del usuario"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM shopfusion.carritos_usuarios
                WHERE usuario_id = %s AND producto_id = %s
            """, (usuario_id, producto_id))
            
            conn.commit()
            
            # Calcular totales
            cur.execute("""
                SELECT SUM(cantidad) as total_items, COUNT(*) as total_productos
                FROM shopfusion.carritos_usuarios
                WHERE usuario_id = %s
            """, (usuario_id,))
            
            totales = cur.fetchone()
            
            return {
                'success': True,
                'total_items': totales['total_items'] or 0,
                'carrito_count': totales['total_productos'] or 0
            }
    except Exception as e:
        conn.rollback()
        print(f"Error al eliminar del carrito: {e}")
        return {'error': 'Error al eliminar producto'}
    finally:
        conn.close()


def limpiar_carrito_usuario(usuario_id):
    """Limpia todo el carrito del usuario (después de compra)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM shopfusion.carritos_usuarios
                WHERE usuario_id = %s
            """, (usuario_id,))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        print(f"Error al limpiar carrito: {e}")
        return False
    finally:
        conn.close()


def calcular_total_carrito_visitante(carrito_cookies):
    """Calcula el total del carrito de visitante desde cookies"""
    if not carrito_cookies:
        return 0
    
    total = 0
    for item in carrito_cookies:
        precio = float(item.get('precio', 0) or 0)
        cantidad = int(item.get('cantidad', 1) or 1)
        total += precio * cantidad
    
    return total


def validar_limite_visitante(total):
    """Valida que el total del carrito de visitante no exceda $50"""
    LIMITE_VISITANTE = 50.0
    return total <= LIMITE_VISITANTE


def migrar_carrito_cookies_a_bd(usuario_id, carrito_cookies):
    """Migra el carrito de cookies a BD cuando un visitante inicia sesión"""
    if not carrito_cookies:
        return True
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            for item in carrito_cookies:
                producto_id = item.get('producto_id')
                cantidad = item.get('cantidad', 1)

                if not producto_id:
                    continue

                cur.execute("""
                    SELECT precio, precio_oferta, estado
                    FROM shopfusion.productos_vendedor
                    WHERE id = %s AND estado = 'activo'
                """, (producto_id,))
                producto = cur.fetchone()
                if not producto:
                    continue

                precio_normal = float(producto.get('precio') or 0)
                precio_oferta_val = float(producto.get('precio_oferta') or 0)
                if precio_oferta_val > 0 and precio_oferta_val < precio_normal:
                    precio_unitario = precio_oferta_val
                else:
                    precio_unitario = precio_normal

                # Verificar si ya existe
                cur.execute("""
                    SELECT id FROM shopfusion.carritos_usuarios
                    WHERE usuario_id = %s AND producto_id = %s
                """, (usuario_id, producto_id))

                existe = cur.fetchone()

                if existe:
                    # Actualizar cantidad
                    cur.execute("""
                        UPDATE shopfusion.carritos_usuarios
                        SET cantidad = cantidad + %s,
                            precio_unitario = %s,
                            actualizado_en = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (cantidad, precio_unitario, existe['id']))
                else:
                    # Insertar nuevo
                    cur.execute("""
                        INSERT INTO shopfusion.carritos_usuarios
                        (usuario_id, producto_id, cantidad, precio_unitario)
                        VALUES (%s, %s, %s, %s)
                    """, (usuario_id, producto_id, cantidad, precio_unitario))
            
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        print(f"Error al migrar carrito: {e}")
        return False
    finally:
        conn.close()


# ========== FUNCIONES PARA CARRITO DE AFILIADOS ==========

def obtener_carrito_afiliado(afiliado_id):
    """Los afiliados no pueden comprar; no existe carrito afiliado."""
    return []


def agregar_al_carrito_afiliado(afiliado_id, producto_id, cantidad=1):
    """Operación no permitida: los afiliados no pueden agregar productos a carrito."""
    return {'error': 'Operación no permitida: los afiliados no pueden comprar productos'}


def actualizar_cantidad_carrito_afiliado(afiliado_id, producto_id, cantidad):
    return {'error': 'Operación no permitida: los afiliados no pueden comprar productos'}


def eliminar_del_carrito_afiliado(afiliado_id, producto_id):
    return {'error': 'Operación no permitida: los afiliados no pueden comprar productos'}


def limpiar_carrito_afiliado(afiliado_id):
    return False


def migrar_carrito_cookies_a_bd_afiliado(afiliado_id, carrito_cookies):
    # No migrar carritos de afiliados: los afiliados no pueden comprar.
    return False

