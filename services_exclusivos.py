import json
import psycopg
from psycopg.rows import dict_row
from urllib.parse import urlparse
from decouple import config


def get_db_connection():
    """
    Conexión independiente a la misma base de datos,
    usando DATABASE_URL - Usa esquema shopfusion
    """
    from urllib.parse import unquote
    database_url = config('DATABASE_URL')
    result = urlparse(database_url)
    # Decodificar la contraseña explícitamente por si acaso
    password = unquote(result.password) if result.password else result.password
    # Usar puerto por defecto si no está especificado
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
    # Configurar el esquema por defecto a shopfusion
    with conn.cursor() as cur:
        cur.execute("SET search_path TO shopfusion")
    conn.commit()
    return conn


def _link_proveedor_column_exists(conn):
    """Verifica si la columna link_proveedor existe en productos_vendedor."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'shopfusion'
                AND table_name = 'productos_vendedor' 
                AND column_name = 'link_proveedor'
            );
        """)
        resultado = cur.fetchone()
        return bool(resultado.get('exists', False)) if resultado else False


def ensure_link_proveedor_column():
    """Asegura que la columna link_proveedor exista en productos_vendedor"""
    conn = get_db_connection()
    try:
        if _link_proveedor_column_exists(conn):
            return True

        with conn.cursor() as cur:
            cur.execute("""
                ALTER TABLE shopfusion.productos_vendedor 
                ADD COLUMN link_proveedor TEXT;
            """)
            conn.commit()
            import logging
            logger = logging.getLogger(__name__)
            logger.info('[PRODUCTOS] Columna link_proveedor agregada a productos_vendedor')
            return True
    except Exception as e:
        conn.rollback()
        import logging
        logger = logging.getLogger(__name__)
        error_msg = str(e).lower()
        if "must be owner" in error_msg or "permission denied" in error_msg:
            logger.warning('[PRODUCTOS] No se pudo agregar columna link_proveedor (permisos limitados): %s', e)
        else:
            logger.error('[PRODUCTOS] Error al agregar columna link_proveedor: %s', e)
        return False
    finally:
        conn.close()


def _producto_columns(conn):
    """Devuelve el set de columnas actuales en productos_vendedor."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'shopfusion'
              AND table_name = 'productos_vendedor';
        """)
        rows = cur.fetchall()
        return {row.get('column_name') for row in rows if row and row.get('column_name')}


def ensure_extra_product_columns(conn=None):
    """Asegura columnas envio_gratis e importado (y link_proveedor si falta)."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        cols = _producto_columns(conn)
        with conn.cursor() as cur:
            if 'envio_gratis' not in cols:
                try:
                    cur.execute("ALTER TABLE shopfusion.productos_vendedor ADD COLUMN envio_gratis BOOLEAN DEFAULT FALSE;")
                    conn.commit()
                    cols.add('envio_gratis')
                except Exception:
                    conn.rollback()
            if 'importado' not in cols:
                try:
                    cur.execute("ALTER TABLE shopfusion.productos_vendedor ADD COLUMN importado BOOLEAN DEFAULT FALSE;")
                    conn.commit()
                    cols.add('importado')
                except Exception:
                    conn.rollback()
            if 'link_proveedor' not in cols:
                try:
                    cur.execute("ALTER TABLE shopfusion.productos_vendedor ADD COLUMN link_proveedor TEXT;")
                    conn.commit()
                    cols.add('link_proveedor')
                except Exception:
                    conn.rollback()
        return cols
    finally:
        if close_conn:
            conn.close()



def _compras_columns(conn):
    """Retorna un set con los nombres de columnas de cliente_compraron_productos."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'shopfusion'
              AND table_name = 'cliente_compraron_productos';
        """)
        rows = cur.fetchall()
        return {row.get('column_name') for row in rows if row and row.get('column_name')}


def ensure_compras_columns():
    """Asegura columnas de margen/comision/ganancia en cliente_compraron_productos."""
    conn = get_db_connection()
    try:
        columnas_actuales = _compras_columns(conn)
        ok = True
        columnas_requeridas = {
            'precio_proveedor': "NUMERIC(10,2)",
            'margen_bruto': "NUMERIC(10,2)",
            'comision_afiliado': "NUMERIC(10,2) DEFAULT 0.00",
            'ganancia_shopfusion': "NUMERIC(10,2) DEFAULT 0.00",
        }
        with conn.cursor() as cur:
            for col, col_def in columnas_requeridas.items():
                if col in columnas_actuales:
                    continue
                try:
                    cur.execute(
                        f"ALTER TABLE shopfusion.cliente_compraron_productos "
                        f"ADD COLUMN {col} {col_def};"
                    )
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    ok = False
                    import logging
                    logger = logging.getLogger(__name__)
                    error_msg = str(e).lower()
                    if "must be owner" in error_msg or "permission denied" in error_msg:
                        logger.warning('[COMPRAS] No se pudo agregar columna %s: %s', col, e)
                    else:
                        logger.error('[COMPRAS] Error al agregar columna %s: %s', col, e)
        return ok
    finally:
        conn.close()


def ensure_compras_envio_columns(conn=None):
    """
    Asegura columnas de datos de envio/identificacion en cliente_compraron_productos.
    Devuelve el set de columnas actuales (con las nuevas si se pudieron crear).
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    columnas_actuales = _compras_columns(conn)
    try:
        with conn.cursor() as cur:
            columnas_requeridas = {
                'provincia': "VARCHAR(150)",
                'ciudad': "VARCHAR(150)",
                'tipo_identificacion': "VARCHAR(20)",
                'numero_identificacion': "VARCHAR(50)",
            }
            for col, col_def in columnas_requeridas.items():
                if col in columnas_actuales:
                    continue
                try:
                    cur.execute(
                        f"ALTER TABLE shopfusion.cliente_compraron_productos "
                        f"ADD COLUMN {col} {col_def};"
                    )
                    conn.commit()
                    columnas_actuales.add(col)
                except Exception:
                    conn.rollback()
        return columnas_actuales
    finally:
        if close_conn:
            conn.close()


def _parse_imagenes(value):
    """
    Normaliza el campo 'imagenes' a una lista de strings.
    Acepta:
      - None / vacío
      - lista Python
      - JSON en texto: '["https://...","https://..."]'
      - formato array de Postgres: '{https://...,...}'
      - una sola URL en texto
    """
    if not value:
        return []

    # Ya es lista
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]

    # Si viene como texto
    if isinstance(value, str):
        v = value.strip()
        if not v:
            return []

        # 1) Intentar JSON puro
        try:
            data = json.loads(v)
            if isinstance(data, list):
                return [str(u).strip() for u in data if str(u).strip()]
            if isinstance(data, str) and data.strip():
                return [data.strip()]
        except json.JSONDecodeError:
            pass

        # 2) Intentar formato array de Postgres {a,b,c}
        if v.startswith('{') and v.endswith('}'):
            inner = v[1:-1]
            partes = [p.strip().strip('"') for p in inner.split(',')]
            return [p for p in partes if p]

        # 3) Asumir que es una sola URL
        return [v]

    # Cualquier otra cosa, lo convertimos a texto
    return [str(value).strip()]


def obtener_productos_exclusivos(limit=100):
    """
    Devuelve una lista de productos exclusivos activos con stock > 0
    desde la tabla productos_vendedor (para la página pública).
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            id,
            titulo,
            descripcion,
            precio,
            precio_oferta,
            precio_proveedor,
            categoria,
            imagenes,
            stock,
            estado
        FROM productos_vendedor
        WHERE estado = 'activo'
          AND stock > 0
        ORDER BY id DESC
        LIMIT %s
        """,
        (limit,)
    )
    productos = cur.fetchall()
    cur.close()
    conn.close()

    # Normalizar imagenes a lista y convertir Decimal a float
    for p in productos:
        p["imagenes"] = _parse_imagenes(p.get("imagenes"))
        # Convertir Decimal a float para evitar errores en templates
        if p.get("precio"):
            p["precio"] = float(p["precio"])
        if p.get("precio_oferta"):
            p["precio_oferta"] = float(p["precio_oferta"])
        if p.get("precio_proveedor"):
            p["precio_proveedor"] = float(p["precio_proveedor"])

    return productos


def obtener_productos_exclusivos_admin(limit=100):
    """
    Devuelve productos exclusivos para el panel de admin.
    Aqui no filtramos por stock ni por estado, para que puedas verlos todos.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    has_link = _link_proveedor_column_exists(conn)

    if has_link:
        query = """
            SELECT
                id,
                titulo,
                descripcion,
                precio,
                precio_oferta,
                precio_proveedor,
                categoria,
                imagenes,
                stock,
                estado,
                link_proveedor
            FROM productos_vendedor
            ORDER BY id DESC
        """
    else:
        query = """
            SELECT
                id,
                titulo,
                descripcion,
                precio,
                precio_oferta,
                precio_proveedor,
                categoria,
                imagenes,
                stock,
                estado
            FROM productos_vendedor
            ORDER BY id DESC
        """

    params = []
    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)

    if params:
        cur.execute(query, params)
    else:
        cur.execute(query)
    productos = cur.fetchall()
    cur.close()
    conn.close()

    for p in productos:
        p["imagenes"] = _parse_imagenes(p.get("imagenes"))
        # Convertir Decimal a float para evitar errores en templates
        if p.get("precio"):
            p["precio"] = float(p["precio"])
        if p.get("precio_oferta"):
            p["precio_oferta"] = float(p["precio_oferta"])
        if p.get("precio_proveedor"):
            p["precio_proveedor"] = float(p["precio_proveedor"])
        if not has_link:
            p["link_proveedor"] = None

    return productos



def obtener_producto_exclusivo_por_id(producto_id: int):
    """
    Devuelve un solo producto exclusivo por su ID.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    has_link = _link_proveedor_column_exists(conn)

    if has_link:
        cur.execute(
            """
            SELECT
                id,
                titulo,
                descripcion,
                precio,
                precio_oferta,
                precio_proveedor,
                categoria,
                imagenes,
                stock,
                estado,
                link_proveedor
            FROM productos_vendedor
            WHERE id = %s
            """,
            (producto_id,)
        )
    else:
        cur.execute(
            """
            SELECT
                id,
                titulo,
                descripcion,
                precio,
                precio_oferta,
                precio_proveedor,
                categoria,
                imagenes,
                stock,
                estado
            FROM productos_vendedor
            WHERE id = %s
            """,
            (producto_id,)
        )
    producto = cur.fetchone()
    cur.close()
    conn.close()

    if producto:
        producto["imagenes"] = _parse_imagenes(producto.get("imagenes"))
        if not has_link:
            producto["link_proveedor"] = None

    return producto



def actualizar_producto_exclusivo(producto_id: int, campos: dict) -> bool:
    """
    Actualiza los campos indicados de un producto exclusivo.
    'campos' es un diccionario, p.ej:
    {
        "titulo": "Nuevo título",
        "descripcion": "...",
        "precio": 123.45,
        "precio_oferta": 99.99,
        "categoria": "Tecnología",
        "stock": 5,
        "estado": "activo",
        "imagenes": ["https://...","https://..."]
    }
    Solo se actualizan las claves permitidas.
    """
    # Campos que permitimos editar
    permitidos = {
        "titulo",
        "descripcion",
        "precio",
        "precio_oferta",
        "precio_proveedor",
        "categoria",
        "stock",
        "estado",
        "imagenes",
        "link_proveedor",
        "envio_gratis",
        "importado",
    }

    try:
        conn_cols = get_db_connection()
        ensure_extra_product_columns(conn_cols)
    finally:
        try:
            conn_cols.close()
        except Exception:
            pass

    if "link_proveedor" in campos:
        conn_check = get_db_connection()
        try:
            if not _link_proveedor_column_exists(conn_check):
                campos = {k: v for k, v in campos.items() if k != "link_proveedor"}
        finally:
            conn_check.close()

    sets = []
    valores = []

    for clave, valor in campos.items():
        if clave not in permitidos:
            continue

        # Guardamos 'imagenes' como JSON válido en la columna tipo json/jsonb
        if clave == "imagenes":
            valor = json.dumps(_parse_imagenes(valor or []))

        sets.append(f"{clave} = %s")
        valores.append(valor)

    if not sets:
        # Nada que actualizar
        return False

    valores.append(producto_id)

    sql = f"""
        UPDATE shopfusion.productos_vendedor
        SET {", ".join(sets)}
        WHERE id = %s
    """

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(sql, tuple(valores))
    conn.commit()
    cur.close()
    conn.close()
    return True

def crear_producto_exclusivo(campos: dict) -> int:
    """
    Crea un nuevo producto exclusivo en la tabla productos_vendedor.

    'campos' debe incluir al menos:
      - titulo (str)
      - descripcion (str)
      - precio (float)

    Opcionales:
      - precio_oferta (float | None)
      - categoria (str | None)
      - stock (int, por defecto 0)
      - estado (str, por defecto "activo")
      - imagenes (list[str] | str | None)
      - envio_gratis (bool)
      - importado (bool)
      - link_proveedor (str)
    """
    permitidos = {
        "titulo", "descripcion", "precio", "precio_oferta", "precio_proveedor",
        "categoria", "stock", "estado", "imagenes", "link_proveedor",
        "envio_gratis", "importado",
    }

    datos = {k: v for k, v in campos.items() if k in permitidos}
    datos.setdefault("precio_oferta", None)
    datos.setdefault("precio_proveedor", 0.00)
    datos.setdefault("categoria", None)
    datos.setdefault("stock", 0)
    datos.setdefault("estado", "activo")
    datos.setdefault("envio_gratis", False)
    datos.setdefault("importado", False)

    imagenes_raw = datos.get("imagenes") or []
    datos["imagenes"] = json.dumps(_parse_imagenes(imagenes_raw))

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cols = ensure_extra_product_columns(conn)
        has_link = "link_proveedor" in cols
        has_envio = "envio_gratis" in cols
        has_importado = "importado" in cols

        insert_cols = [
            "titulo", "descripcion", "precio", "precio_oferta", "precio_proveedor",
            "categoria", "stock", "estado", "imagenes",
        ]
        valores = [
            datos.get("titulo"), datos.get("descripcion"), datos.get("precio"),
            datos.get("precio_oferta"), datos.get("precio_proveedor", 0.00),
            datos.get("categoria"), datos.get("stock"), datos.get("estado"),
            datos.get("imagenes"),
        ]

        if has_envio:
            insert_cols.append("envio_gratis")
            valores.append(bool(datos.get("envio_gratis")))
        if has_importado:
            insert_cols.append("importado")
            valores.append(bool(datos.get("importado")))
        if has_link:
            insert_cols.append("link_proveedor")
            valores.append(datos.get("link_proveedor") or None)

        placeholders = ", ".join(["%s"] * len(insert_cols))
        cols_sql = ", ".join(insert_cols)

        cur.execute(
            f"""
            INSERT INTO shopfusion.productos_vendedor ({cols_sql})
            VALUES ({placeholders})
            RETURNING id
            """,
            tuple(valores),
        )
        fila = cur.fetchone()
        conn.commit()
        return fila["id"] if fila else None
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def registrar_compra_exclusivo(
    producto_id: int,
    nombre: str,
    apellido: str,
    email: str,
    telefono: str,
    pais: str,
    direccion: str,
    cantidad: int,
    paypal_order_id: str,
    paypal_capture_id: str,
    monto_total: float,
    moneda: str = "USD",
    estado_pago: str = "pagado",
    afiliado_id: int = None,
    afiliado_codigo: str = None,
    provincia: str = "",
    ciudad: str = "",
    tipo_identificacion: str = "",
    numero_identificacion: str = "",
) -> int:
    """
    Registra una compra de producto exclusivo en la tabla cliente_compraron_productos
    y actualiza el stock del producto_vendedor.

    Devuelve el ID de la compra creada.
    """
    if cantidad <= 0:
        cantidad = 1

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        columnas_extra = ensure_compras_envio_columns(conn)
        # 1) Obtener datos del producto (snapshot de título y precio final)
        cur.execute(
            """
            SELECT
                id,
                titulo,
                COALESCE(precio_oferta, precio) AS precio_final,
                COALESCE(precio_proveedor, 0) AS precio_proveedor,
                stock
            FROM productos_vendedor
            WHERE id = %s
            FOR UPDATE
            """,
            (producto_id,)
        )
        producto = cur.fetchone()

        if not producto:
            raise ValueError(f"Producto exclusivo con ID {producto_id} no encontrado.")

        precio_final = float(producto["precio_final"] or 0)
        precio_proveedor = float(producto.get("precio_proveedor") or 0)
        stock_actual = int(producto["stock"] or 0)
        if cantidad > stock_actual:
            raise ValueError(f"Stock insuficiente para producto {producto_id}. Disponible: {stock_actual}")

        monto_total_val = float(monto_total) if monto_total is not None else (precio_final * cantidad)
        precio_unitario_pagado = (monto_total_val / cantidad) if cantidad else precio_final
        margen_bruto = (precio_unitario_pagado - precio_proveedor) * cantidad

        # 2) Insertar registro de compra
        columnas = [
            "producto_id",
            "producto_titulo",
            "producto_precio",
            "cantidad",
            "nombre",
            "apellido",
            "email",
            "telefono",
            "pais",
            "direccion",
            "paypal_order_id",
            "paypal_capture_id",
            "monto_total",
            "moneda",
            "estado_pago",
            "afiliado_id",
            "afiliado_codigo",
        ]
        valores = [
            producto_id,
            producto["titulo"],
            precio_final,
            cantidad,
            nombre,
            apellido,
            email,
            telefono,
            pais,
            direccion,
            paypal_order_id,
            paypal_capture_id,
            monto_total_val,
            moneda,
            estado_pago,
            afiliado_id,
            afiliado_codigo,
        ]

        columnas_extra = columnas_extra or _compras_columns(conn)
        # Agregar datos de envío solo si las columnas existen en la tabla
        if "provincia" in columnas_extra:
            columnas.insert(10, "provincia")
            valores.insert(10, provincia or "")
        if "ciudad" in columnas_extra:
            columnas.insert(11, "ciudad")
            valores.insert(11, ciudad or "")
        if "tipo_identificacion" in columnas_extra:
            columnas.insert(12, "tipo_identificacion")
            valores.insert(12, tipo_identificacion or "")
        if "numero_identificacion" in columnas_extra:
            columnas.insert(13, "numero_identificacion")
            valores.insert(13, numero_identificacion or "")

        if "precio_proveedor" in columnas_extra:
            columnas.append("precio_proveedor")
            valores.append(precio_proveedor)
        if "margen_bruto" in columnas_extra:
            columnas.append("margen_bruto")
            valores.append(margen_bruto)
        if "comision_afiliado" in columnas_extra:
            columnas.append("comision_afiliado")
            valores.append(0.0)
        if "ganancia_shopfusion" in columnas_extra:
            columnas.append("ganancia_shopfusion")
            valores.append(margen_bruto)

        placeholders = ", ".join(["%s"] * len(valores))
        cur.execute(
            f"""
            INSERT INTO cliente_compraron_productos ({", ".join(columnas)})
            VALUES ({placeholders})
            RETURNING id;
            """,
            tuple(valores)
        )
        compra_id = cur.fetchone()["id"]

        # 3) Actualizar stock del producto
        cur.execute(
            """
            UPDATE productos_vendedor
            SET stock = stock - %s
            WHERE id = %s
            """,
            (cantidad, producto_id)
        )

        conn.commit()
        return compra_id

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def obtener_productos_mas_vendidos(limit=10):
    """
    Obtiene los productos más vendidos basándose en las compras registradas.
    
    Args:
        limit: Número máximo de productos a retornar
    
    Returns:
        Lista de productos ordenados por cantidad de ventas
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Intentar obtener productos más vendidos contando las compras
            try:
                cur.execute("""
                    SELECT 
                        p.id,
                        p.titulo,
                        p.descripcion,
                        p.precio,
                        p.precio_oferta,
                        p.precio_proveedor,
                        p.categoria,
                        p.imagenes,
                        p.stock,
                        p.estado,
                        COALESCE(SUM(COALESCE(c.cantidad, 0)), 0)::INTEGER as total_ventas
                    FROM productos_vendedor p
                    LEFT JOIN cliente_compraron_productos c ON p.id = c.producto_id 
                        AND (c.estado_pago = 'pagado' OR c.estado_pago IS NULL)
                    WHERE p.estado = 'activo' 
                      AND p.stock > 0
                    GROUP BY p.id, p.titulo, p.descripcion, p.precio, p.precio_oferta, 
                             p.precio_proveedor, p.categoria, p.imagenes, p.stock, p.estado
                    ORDER BY total_ventas DESC, p.id DESC
                    LIMIT %s
                """, (limit,))
                productos = cur.fetchall()
            except Exception as sql_error:
                # Si falla la query, obtener productos recientes
                import logging
                logging.getLogger(__name__).warning(f"Error en query más vendidos: {sql_error}")
                productos = []
            
            # Si no hay productos vendidos, obtener productos recientes
            if not productos:
                cur.execute("""
                    SELECT 
                        id, titulo, descripcion, precio, precio_oferta, precio_proveedor,
                        categoria, imagenes, stock, estado
                    FROM productos_vendedor
                    WHERE estado = 'activo' 
                      AND stock > 0
                    ORDER BY id DESC
                    LIMIT %s
                """, (limit,))
                productos = cur.fetchall()
            
            # Normalizar imágenes y convertir Decimal a float
            for p in productos:
                p["imagenes"] = _parse_imagenes(p.get("imagenes"))
                if p.get("precio"):
                    p["precio"] = float(p["precio"])
                if p.get("precio_oferta"):
                    p["precio_oferta"] = float(p["precio_oferta"])
                if p.get("precio_proveedor"):
                    p["precio_proveedor"] = float(p["precio_proveedor"])
                # Asegurar que total_ventas existe
                if 'total_ventas' not in p:
                    p['total_ventas'] = 0
                else:
                    p['total_ventas'] = int(p['total_ventas'] or 0)
            
            return productos[:limit]
    except Exception as e:
        # Si hay error, retornar productos recientes
        import logging
        logging.getLogger(__name__).warning(f"Error al obtener más vendidos: {e}")
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    id, titulo, descripcion, precio, precio_oferta, precio_proveedor,
                    categoria, imagenes, stock, estado
                FROM productos_vendedor
                WHERE estado = 'activo' 
                  AND stock > 0
                ORDER BY id DESC
                LIMIT %s
            """, (limit,))
            productos = cur.fetchall()
            for p in productos:
                p["imagenes"] = _parse_imagenes(p.get("imagenes"))
                if p.get("precio"):
                    p["precio"] = float(p["precio"])
                if p.get("precio_oferta"):
                    p["precio_oferta"] = float(p["precio_oferta"])
                if p.get("precio_proveedor"):
                    p["precio_proveedor"] = float(p["precio_proveedor"])
                p['total_ventas'] = 0
            cur.close()
            return productos
        except:
            return []
    finally:
        conn.close()


def buscar_productos(termino_busqueda=None, categoria=None, limit=50):
    """
    Busca productos exclusivos por término de búsqueda y/o categoría.
    
    Args:
        termino_busqueda: Texto para buscar en título y descripción
        categoria: Nombre de categoría para filtrar
        limit: Número máximo de resultados
    
    Returns:
        Lista de productos que coinciden con los criterios
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Construir la consulta SQL dinámicamente
    query = """
        SELECT
            id,
            titulo,
            descripcion,
            precio,
            precio_oferta,
            precio_proveedor,
            categoria,
            imagenes,
            stock,
            estado
        FROM productos_vendedor
        WHERE estado = 'activo' AND stock > 0
    """
    params = []
    
    # Agregar filtro por término de búsqueda
    if termino_busqueda and termino_busqueda.strip():
        query += " AND (LOWER(titulo) LIKE %s OR LOWER(descripcion) LIKE %s)"
        busqueda_pattern = f"%{termino_busqueda.strip().lower()}%"
        params.extend([busqueda_pattern, busqueda_pattern])
    
    # Agregar filtro por categoría
    if categoria and categoria.strip():
        query += " AND LOWER(categoria) = LOWER(%s)"
        params.append(categoria.strip())
    
    query += " ORDER BY id DESC LIMIT %s"
    params.append(limit)
    
    cur.execute(query, tuple(params))
    productos = cur.fetchall()
    cur.close()
    conn.close()
    
    # Normalizar imágenes y convertir Decimal a float
    for p in productos:
        p["imagenes"] = _parse_imagenes(p.get("imagenes"))
        if p.get("precio"):
            p["precio"] = float(p["precio"])
        if p.get("precio_oferta"):
            p["precio_oferta"] = float(p["precio_oferta"])
        if p.get("precio_proveedor"):
            p["precio_proveedor"] = float(p["precio_proveedor"])
    
    return productos
