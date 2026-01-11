"""
Servicios para la gestión de categorías de productos de ShopFusion
"""
import psycopg
from psycopg.rows import dict_row
from urllib.parse import urlparse
from decouple import config


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


def ensure_categorias_table():
    """Asegura que la tabla de categorías exista y tenga la estructura correcta"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Crear tabla de categorías
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopfusion.categorias (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL UNIQUE,
                    slug VARCHAR(120) NOT NULL UNIQUE,
                    descripcion TEXT,
                    icono VARCHAR(50),
                    color VARCHAR(7),
                    orden INTEGER DEFAULT 0,
                    activa BOOLEAN DEFAULT TRUE,
                    creada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    actualizada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Crear índice para búsquedas rápidas
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_categorias_nombre 
                ON shopfusion.categorias(nombre);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_categorias_activa 
                ON shopfusion.categorias(activa);
            """)
            
            # Insertar categorías iniciales si la tabla está vacía
            cur.execute("SELECT COUNT(*) as count FROM shopfusion.categorias")
            count = cur.fetchone()['count']
            
            if count == 0:
                categorias_iniciales = [
                    ("Tecnología", "tecnologia", "Productos tecnológicos y electrónicos", "fa-microchip", "#3b82f6", 1),
                    ("Electrónica", "electronica", "Dispositivos y componentes electrónicos", "fa-plug", "#8b5cf6", 2),
                    ("Celulares y Smartphones", "celulares-smartphones", "Teléfonos inteligentes y accesorios", "fa-mobile-alt", "#10b981", 3),
                    ("Computadoras y Laptops", "computadoras-laptops", "Equipos de cómputo y portátiles", "fa-laptop", "#f59e0b", 4),
                    ("Tablets", "tablets", "Tablets y dispositivos táctiles", "fa-tablet-alt", "#ef4444", 5),
                    ("Accesorios Tecnológicos", "accesorios-tecnologicos", "Accesorios para dispositivos tecnológicos", "fa-headphones", "#06b6d4", 6),
                    ("Audio y Sonido", "audio-sonido", "Equipos de audio y sonido", "fa-volume-up", "#ec4899", 7),
                    ("Gaming", "gaming", "Productos para gaming y videojuegos", "fa-gamepad", "#8b5cf6", 8),
                    ("Hogar y Jardín", "hogar-jardin", "Artículos para el hogar y jardín", "fa-home", "#84cc16", 9),
                    ("Electrodomésticos", "electrodomesticos", "Electrodomésticos para el hogar", "fa-blender", "#f97316", 10),
                    ("Muebles", "muebles", "Muebles y decoración", "fa-couch", "#a855f7", 11),
                    ("Decoración", "decoracion", "Artículos de decoración", "fa-palette", "#eab308", 12),
                    ("Cocina", "cocina", "Utensilios y productos para cocina", "fa-utensils", "#f59e0b", 13),
                    ("Baño", "bano", "Artículos para el baño", "fa-bath", "#14b8a6", 14),
                    ("Iluminación", "iluminacion", "Productos de iluminación", "fa-lightbulb", "#fbbf24", 15),
                    ("Ropa y Moda", "ropa-moda", "Ropa y artículos de moda", "fa-tshirt", "#ec4899", 16),
                    ("Calzado", "calzado", "Zapatos y calzado", "fa-shoe-prints", "#6366f1", 17),
                    ("Accesorios de Moda", "accesorios-moda", "Accesorios de moda y complementos", "fa-gem", "#db2777", 18),
                    ("Relojes", "relojes", "Relojes y cronómetros", "fa-clock", "#0891b2", 19),
                    ("Bolsos y Mochilas", "bolsos-mochilas", "Bolsos, mochilas y carteras", "fa-shopping-bag", "#be185d", 20),
                    ("Belleza y Cuidado Personal", "belleza-cuidado-personal", "Productos de belleza y cuidado", "fa-spa", "#ec4899", 21),
                    ("Cosméticos", "cosmeticos", "Cosméticos y maquillaje", "fa-paint-brush", "#f472b6", 22),
                    ("Perfumes", "perfumes", "Fragancias y perfumes", "fa-spray-can", "#a78bfa", 23),
                    ("Cuidado del Cabello", "cuidado-cabello", "Productos para el cabello", "fa-cut", "#fbbf24", 24),
                    ("Cuidado de la Piel", "cuidado-piel", "Productos para el cuidado de la piel", "fa-hand-sparkles", "#fda4af", 25),
                    ("Salud y Bienestar", "salud-bienestar", "Productos de salud y bienestar", "fa-heartbeat", "#ef4444", 26),
                    ("Fitness y Deportes", "fitness-deportes", "Artículos deportivos y fitness", "fa-running", "#10b981", 27),
                    ("Suplementos", "suplementos", "Suplementos nutricionales", "fa-capsules", "#34d399", 28),
                    ("Equipamiento Deportivo", "equipamiento-deportivo", "Equipamiento para deportes", "fa-dumbbell", "#059669", 29),
                    ("Educación", "educacion", "Productos educativos", "fa-graduation-cap", "#3b82f6", 30),
                    ("Libros", "libros", "Libros y publicaciones", "fa-book", "#6366f1", 31),
                    ("Material Escolar", "material-escolar", "Material y útiles escolares", "fa-pencil-alt", "#8b5cf6", 32),
                    ("Juguetes y Juegos", "juguetes-juegos", "Juguetes y juegos para todas las edades", "fa-puzzle-piece", "#ec4899", 33),
                    ("Bebés y Niños", "bebes-ninos", "Productos para bebés y niños", "fa-baby", "#f472b6", 34),
                    ("Automotriz", "automotriz", "Productos automotrices", "fa-car", "#64748b", 35),
                    ("Herramientas", "herramientas", "Herramientas y equipos", "fa-wrench", "#78716c", 36),
                    ("Jardín y Exterior", "jardin-exterior", "Productos para jardín y exterior", "fa-seedling", "#22c55e", 37),
                    ("Mascotas", "mascotas", "Productos para mascotas", "fa-paw", "#f59e0b", 38),
                    ("Viajes y Turismo", "viajes-turismo", "Artículos para viajes", "fa-suitcase-rolling", "#06b6d4", 39),
                    ("Alimentos y Bebidas", "alimentos-bebidas", "Alimentos y bebidas", "fa-utensils", "#f97316", 40),
                    ("Otros", "otros", "Otras categorías", "fa-box", "#9ca3af", 999),
                ]
                
                for nombre, slug, descripcion, icono, color, orden in categorias_iniciales:
                    try:
                        cur.execute("""
                            INSERT INTO shopfusion.categorias (nombre, slug, descripcion, icono, color, orden)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (nombre) DO NOTHING
                        """, (nombre, slug, descripcion, icono, color, orden))
                    except Exception as e:
                        # Si hay conflicto, ignorar
                        pass
            
            conn.commit()
    except Exception as e:
        conn.rollback()
        import logging
        logger = logging.getLogger(__name__)
        error_msg = str(e).lower()
        if "must be owner" in error_msg or "permission denied" in error_msg:
            logger.warning(f"⚠️ Advertencia en ensure_categorias_table (permisos limitados): {e}")
        else:
            logger.error(f"❌ Error en ensure_categorias_table: {e}")
            raise e
    finally:
        conn.close()


def obtener_categorias(activas=True):
    """Obtiene todas las categorías, opcionalmente solo las activas"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if activas:
                cur.execute("""
                    SELECT * FROM categorias
                    WHERE activa = TRUE
                    ORDER BY orden ASC, nombre ASC
                """)
            else:
                cur.execute("""
                    SELECT * FROM categorias
                    ORDER BY orden ASC, nombre ASC
                """)
            return cur.fetchall()
    finally:
        conn.close()


def obtener_categoria_por_id(categoria_id):
    """Obtiene una categoría por su ID"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM categorias WHERE id = %s", (categoria_id,))
            return cur.fetchone()
    finally:
        conn.close()


def obtener_categoria_por_slug(slug):
    """Obtiene una categoría por su slug"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM categorias WHERE slug = %s AND activa = TRUE", (slug,))
            return cur.fetchone()
    finally:
        conn.close()


def crear_categoria(nombre, slug=None, descripcion=None, icono=None, color=None, orden=0):
    """Crea una nueva categoría"""
    import re
    
    # Generar slug si no se proporciona
    if not slug:
        slug = re.sub(r'[^a-z0-9]+', '-', nombre.lower()).strip('-')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO categorias (nombre, slug, descripcion, icono, color, orden)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (nombre, slug, descripcion, icono, color, orden))
            result = cur.fetchone()
            conn.commit()
            return result
    except psycopg.IntegrityError as e:
        conn.rollback()
        if 'nombre' in str(e) or 'categorias_nombre_key' in str(e):
            raise ValueError("Ya existe una categoría con ese nombre")
        elif 'slug' in str(e) or 'categorias_slug_key' in str(e):
            raise ValueError("Ya existe una categoría con ese slug")
        raise ValueError("Error al crear la categoría")
    finally:
        conn.close()


def actualizar_categoria(categoria_id, campos):
    """Actualiza los campos de una categoría"""
    campos_permitidos = ['nombre', 'slug', 'descripcion', 'icono', 'color', 'orden', 'activa']
    
    sets = []
    valores = []
    
    for clave, valor in campos.items():
        if clave in campos_permitidos:
            sets.append(f"{clave} = %s")
            valores.append(valor)
    
    if not sets:
        return False
    
    # Agregar actualización de timestamp
    sets.append("actualizada_en = CURRENT_TIMESTAMP")
    valores.append(categoria_id)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            sql = f"""
                UPDATE categorias
                SET {", ".join(sets)}
                WHERE id = %s
                RETURNING *
            """
            cur.execute(sql, tuple(valores))
            result = cur.fetchone()
            conn.commit()
            return result
    except psycopg.IntegrityError as e:
        conn.rollback()
        if 'nombre' in str(e) or 'categorias_nombre_key' in str(e):
            raise ValueError("Ya existe una categoría con ese nombre")
        elif 'slug' in str(e) or 'categorias_slug_key' in str(e):
            raise ValueError("Ya existe una categoría con ese slug")
        raise ValueError("Error al actualizar la categoría")
    finally:
        conn.close()


def eliminar_categoria(categoria_id):
    """Elimina una categoría (marca como inactiva en lugar de borrar)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # En lugar de eliminar, marcamos como inactiva
            cur.execute("""
                UPDATE categorias
                SET activa = FALSE, actualizada_en = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING *
            """, (categoria_id,))
            result = cur.fetchone()
            conn.commit()
            return result
    finally:
        conn.close()


def eliminar_categoria_permanente(categoria_id):
    """Elimina permanentemente una categoría (solo si no tiene productos asociados)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Verificar si hay productos asociados
            cur.execute("""
                SELECT COUNT(*) as count FROM productos_vendedor
                WHERE categoria = (SELECT nombre FROM categorias WHERE id = %s)
            """, (categoria_id,))
            count = cur.fetchone()['count']
            
            if count > 0:
                raise ValueError(f"No se puede eliminar: hay {count} productos asociados a esta categoría")
            
            cur.execute("DELETE FROM categorias WHERE id = %s RETURNING *", (categoria_id,))
            result = cur.fetchone()
            conn.commit()
            return result
    finally:
        conn.close()


def obtener_categorias_como_lista():
    """Obtiene las categorías activas como lista simple de nombres (para compatibilidad con código existente)"""
    categorias = obtener_categorias(activas=True)
    return [cat['nombre'] for cat in categorias]

