"""
Servicios para el sistema de afiliados de ShopFusion
"""
import psycopg
from psycopg.rows import dict_row
from urllib.parse import urlparse
from decouple import config
import secrets
import string
from datetime import datetime


def get_db_connection():
    """Conexión a la base de datos - Usa esquema shopfusion"""
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


def ensure_afiliados_tables():
    """Asegura que las tablas de afiliados existan y corrijan estructura"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Verificar si la tabla existe en el esquema shopfusion
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'shopfusion' 
                    AND table_name = 'afiliados'
                );
            """)
            resultado = cur.fetchone()
            # Con dict_row, el resultado es un diccionario, usar el nombre de la columna
            tabla_existe = resultado.get('exists', False) if resultado else False
            
            # Si la tabla existe, intentar corregir constraints incorrectas ANTES de crear
            # (pero no fallar si no tenemos permisos)
            if tabla_existe:
                # Eliminar constraint UNIQUE en nombre si existe (no debería tenerlo)
                try:
                    cur.execute("ALTER TABLE shopfusion.afiliados DROP CONSTRAINT IF EXISTS afiliados_nombre_key;")
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    # Si no tenemos permisos, continuar sin error
                    if "must be owner" in str(e).lower() or "permission denied" in str(e).lower():
                        pass
                    else:
                        # Intentar de otra forma si falla por otra razón
                        try:
                            cur.execute("""
                                SELECT constraint_name 
                                FROM information_schema.table_constraints 
                                WHERE table_schema = 'shopfusion'
                                AND table_name = 'afiliados' 
                                AND constraint_type = 'UNIQUE' 
                                AND constraint_name = 'afiliados_nombre_key';
                            """)
                            if cur.fetchone():
                                cur.execute("ALTER TABLE shopfusion.afiliados DROP CONSTRAINT afiliados_nombre_key CASCADE;")
                                conn.commit()
                        except Exception:
                            conn.rollback()
            
            # Tabla de afiliados (en esquema shopfusion)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopfusion.afiliados (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(150) NOT NULL,
                    email VARCHAR(150) NOT NULL,
                    codigo_afiliado VARCHAR(20) NOT NULL,
                    comision_porcentaje DECIMAL(5,2) NOT NULL DEFAULT 10.00,
                    password_hash TEXT NOT NULL,
                    pais VARCHAR(100),
                    metodo_pago VARCHAR(20),
                    banco VARCHAR(50),
                    numero_cuenta VARCHAR(50),
                    titular_cuenta VARCHAR(150),
                    paypal_email VARCHAR(150),
                    skrill_email VARCHAR(150),
                    frecuencia_pago VARCHAR(20) DEFAULT 'mensual',
                    estado VARCHAR(20) DEFAULT 'activo',
                    total_ganancias DECIMAL(10,2) DEFAULT 0.00,
                    total_pagado DECIMAL(10,2) DEFAULT 0.00,
                    total_ventas INTEGER DEFAULT 0,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ultima_actividad TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Si la tabla ya existía, intentar agregar columnas faltantes si es necesario
            # (pero no fallar si no tenemos permisos)
            if tabla_existe:
                # Obtener columnas existentes
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = 'shopfusion'
                    AND table_name = 'afiliados';
                """)
                # Con dict_row, acceder por nombre de columna
                columnas_existentes = [row.get('column_name') for row in cur.fetchall() if row]
                
                # Agregar columnas faltantes si no existen
                columnas_requeridas = {
                    'codigo_afiliado': "VARCHAR(20)",
                    'comision_porcentaje': "DECIMAL(5,2) DEFAULT 10.00",
                    'password_hash': "TEXT",
                    'pais': "VARCHAR(100)",
                    'metodo_pago': "VARCHAR(20)",
                    'banco': "VARCHAR(50)",
                    'numero_cuenta': "VARCHAR(50)",
                    'titular_cuenta': "VARCHAR(150)",
                    'paypal_email': "VARCHAR(150)",
                    'skrill_email': "VARCHAR(150)",
                    'frecuencia_pago': "VARCHAR(20) DEFAULT 'mensual'",
                    'estado': "VARCHAR(20) DEFAULT 'activo'",
                    'total_ganancias': "DECIMAL(10,2) DEFAULT 0.00",
                    'total_pagado': "DECIMAL(10,2) DEFAULT 0.00",
                    'total_ventas': "INTEGER DEFAULT 0",
                    'creado_en': "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    'ultima_actividad': "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
                }
                
                for col_name, col_def in columnas_requeridas.items():
                    if col_name not in columnas_existentes:
                        try:
                            cur.execute(f"ALTER TABLE shopfusion.afiliados ADD COLUMN {col_name} {col_def};")
                            conn.commit()
                        except Exception as e:
                            conn.rollback()
                            # Si el error es de permisos, solo registrar advertencia
                            if "must be owner" not in str(e).lower() and "permission denied" not in str(e).lower():
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.warning(f"⚠️ No se pudo agregar columna {col_name}: {e}")
                
                # Asegurar constraints UNIQUE correctas (sin nombre)
                try:
                    # Eliminar cualquier constraint UNIQUE en nombre
                    cur.execute("ALTER TABLE shopfusion.afiliados DROP CONSTRAINT IF EXISTS afiliados_nombre_key CASCADE;")
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    # Si no tenemos permisos, continuar sin error
                    if "must be owner" in str(e).lower() or "permission denied" in str(e).lower():
                        pass
            
            # Asegurar constraints UNIQUE en email y codigo_afiliado (para tabla nueva o existente)
            # Verificar y crear constraint UNIQUE en email si no existe
            cur.execute("""
                SELECT 1 FROM pg_constraint pc
                JOIN pg_class c ON c.oid = pc.conrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'shopfusion'
                AND c.relname = 'afiliados'
                AND pc.conname = 'afiliados_email_key' 
                LIMIT 1;
            """)
            if not cur.fetchone():
                try:
                    cur.execute("ALTER TABLE shopfusion.afiliados ADD CONSTRAINT afiliados_email_key UNIQUE (email);")
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    # Si ya existe o no tenemos permisos, ignorar el error
                    if "already exists" not in str(e).lower() and "must be owner" not in str(e).lower() and "permission denied" not in str(e).lower():
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"⚠️ No se pudo agregar constraint email: {e}")
            
            # Verificar y crear constraint UNIQUE en codigo_afiliado si no existe
            cur.execute("""
                SELECT 1 FROM pg_constraint pc
                JOIN pg_class c ON c.oid = pc.conrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'shopfusion'
                AND c.relname = 'afiliados'
                AND pc.conname = 'afiliados_codigo_afiliado_key' 
                LIMIT 1;
            """)
            if not cur.fetchone():
                try:
                    cur.execute("ALTER TABLE shopfusion.afiliados ADD CONSTRAINT afiliados_codigo_afiliado_key UNIQUE (codigo_afiliado);")
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    # Si ya existe o no tenemos permisos, ignorar el error
                    if "already exists" not in str(e).lower() and "must be owner" not in str(e).lower() and "permission denied" not in str(e).lower():
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"⚠️ No se pudo agregar constraint codigo_afiliado: {e}")
            
            # Tabla de comisiones/ventas de afiliados (en esquema shopfusion)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopfusion.comisiones_afiliados (
                    id SERIAL PRIMARY KEY,
                    afiliado_id INTEGER NOT NULL REFERENCES shopfusion.afiliados(id) ON DELETE CASCADE,
                    compra_id INTEGER NOT NULL REFERENCES shopfusion.cliente_compraron_productos(id) ON DELETE CASCADE,
                    monto_venta DECIMAL(10,2) NOT NULL,
                    comision_porcentaje DECIMAL(5,2) NOT NULL,
                    monto_comision DECIMAL(10,2) NOT NULL,
                    estado VARCHAR(20) DEFAULT 'pendiente',
                    fecha_comision TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_pago TIMESTAMP,
                    UNIQUE(compra_id, afiliado_id)
                );
            """)
            
            # Tabla de tracking de clicks/visitas (en esquema shopfusion)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopfusion.tracking_afiliados (
                    id SERIAL PRIMARY KEY,
                    afiliado_id INTEGER NOT NULL REFERENCES shopfusion.afiliados(id) ON DELETE CASCADE,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    producto_id INTEGER,
                    fecha_click TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    convertido BOOLEAN DEFAULT FALSE,
                    compra_id INTEGER REFERENCES shopfusion.cliente_compraron_productos(id) ON DELETE SET NULL
                );
            """)
            
            # Agregar columna producto_id si no existe (para tablas existentes)
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_schema = 'shopfusion'
                        AND table_name = 'tracking_afiliados' 
                        AND column_name = 'producto_id'
                    ) THEN
                        ALTER TABLE shopfusion.tracking_afiliados 
                        ADD COLUMN producto_id INTEGER;
                    END IF;
                END $$;
            """)
            
            # Tabla de descuentos activos para afiliados
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopfusion.descuentos_afiliados (
                    id SERIAL PRIMARY KEY,
                    afiliado_id INTEGER NOT NULL REFERENCES shopfusion.afiliados(id) ON DELETE CASCADE,
                    ventas_requeridas INTEGER NOT NULL DEFAULT 3,
                    ventas_actuales INTEGER NOT NULL DEFAULT 0,
                    descuento_acumulado DECIMAL(10,2) DEFAULT 0.00,
                    fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_expiracion TIMESTAMP NOT NULL,
                    estado VARCHAR(20) DEFAULT 'activo',
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Tabla de clientes asociados a afiliados (asignacion permanente)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopfusion.afiliados_clientes (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER NOT NULL REFERENCES shopfusion.usuarios(id) ON DELETE CASCADE,
                    afiliado_id INTEGER NOT NULL REFERENCES shopfusion.afiliados(id) ON DELETE CASCADE,
                    codigo_afiliado VARCHAR(20),
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(usuario_id)
                );
            """)
            
            # Tabla de comisiones manuales temporales (ajustes por admin con tiempo límite)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopfusion.comisiones_manuales_temporales (
                    id SERIAL PRIMARY KEY,
                    afiliado_id INTEGER REFERENCES shopfusion.afiliados(id) ON DELETE CASCADE,
                    comision_manual DECIMAL(5,2) NOT NULL,
                    fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_expiracion TIMESTAMP NOT NULL,
                    activa BOOLEAN DEFAULT TRUE,
                    creado_por INTEGER,  -- ID del admin que lo creó
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Tabla de configuración del sistema (comisión predeterminada)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopfusion.configuracion_sistema (
                    id SERIAL PRIMARY KEY,
                    clave VARCHAR(100) UNIQUE NOT NULL,
                    valor TEXT NOT NULL,
                    descripcion TEXT,
                    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    actualizado_por INTEGER  -- ID del admin que lo actualizó
                );
            """)
            
            # Insertar comisión predeterminada si no existe (50% para usuarios nuevos)
            cur.execute("""
                INSERT INTO shopfusion.configuracion_sistema (clave, valor, descripcion)
                VALUES ('comision_predeterminada', '50.00', 'Comisión predeterminada para usuarios nuevos (50%)')
                ON CONFLICT (clave) DO NOTHING;
            """)
            
            # Índices para mejor rendimiento (con manejo de errores de permisos)
            indices = [
                ("idx_afiliados_codigo", "afiliados", "codigo_afiliado"),
                ("idx_comisiones_afiliado", "comisiones_afiliados", "afiliado_id"),
                ("idx_comisiones_estado", "comisiones_afiliados", "estado"),
                ("idx_descuentos_afiliado", "descuentos_afiliados", "afiliado_id"),
                ("idx_descuentos_estado", "descuentos_afiliados", "estado"),
                ("idx_descuentos_expiracion", "descuentos_afiliados", "fecha_expiracion"),
                ("idx_tracking_afiliado", "tracking_afiliados", "afiliado_id"),
                ("idx_afiliados_clientes_afiliado", "afiliados_clientes", "afiliado_id"),
            ]
            
            for nombre_idx, tabla, columna in indices:
                try:
                    # Verificar si el índice ya existe
                    cur.execute("""
                        SELECT 1 FROM pg_indexes 
                        WHERE schemaname = 'shopfusion' 
                        AND indexname = %s
                        LIMIT 1;
                    """, (nombre_idx,))
                    
                    if not cur.fetchone():
                        # Crear el índice
                        cur.execute(f"""
                            CREATE INDEX IF NOT EXISTS {nombre_idx} 
                            ON shopfusion.{tabla}({columna});
                        """)
                        conn.commit()
                except Exception as e:
                    conn.rollback()
                    # Si el error es de permisos, solo registrar advertencia
                    if "must be owner" in str(e).lower() or "permission denied" in str(e).lower():
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"⚠️ No se pudo crear índice {nombre_idx}: {e}")
                    else:
                        # Para otros errores, registrar pero continuar
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"⚠️ No se pudo crear índice {nombre_idx}: {e}")
            
            conn.commit()
    except Exception as e:
        conn.rollback()
        import logging
        logger = logging.getLogger(__name__)
        error_msg = str(e).lower()
        
        # Si el error es de permisos (must be owner), solo registrar advertencia
        # y no fallar, ya que las tablas pueden existir y funcionar correctamente
        if "must be owner" in error_msg or "permission denied" in error_msg:
            logger.warning(f"⚠️ Advertencia en ensure_afiliados_tables (permisos limitados): {e}")
            logger.warning("Las tablas pueden existir pero no se pueden modificar. Continuando...")
            # No lanzar excepción, solo registrar advertencia
        else:
            # Para otros errores, registrar y lanzar
            logger.error(f"❌ Error en ensure_afiliados_tables: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise e
    finally:
        conn.close()


def generar_codigo_afiliado():
    """Genera un código único de afiliado"""
    conn = get_db_connection()
    try:
        max_intentos = 100  # Evitar loops infinitos
        intentos = 0
        
        while intentos < max_intentos:
            # Generar código de 8 caracteres alfanuméricos
            codigo = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM shopfusion.afiliados WHERE codigo_afiliado = %s", (codigo,))
                if not cur.fetchone():
                    return codigo
            
            intentos += 1
        
        # Si llegamos aquí, algo está mal
        raise Exception("No se pudo generar un código único después de múltiples intentos")
    finally:
        conn.close()


def limpiar_comisiones_manuales_expiradas():
    """Desactiva comisiones manuales temporales que han expirado"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE shopfusion.comisiones_manuales_temporales
                SET activa = FALSE
                WHERE activa = TRUE AND fecha_expiracion < CURRENT_TIMESTAMP
            """)
            cantidad = cur.rowcount
            conn.commit()
            if cantidad > 0:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f'[LIMPIAR_COMISIONES] {cantidad} comisiones manuales temporales expiradas desactivadas')
            return cantidad
    except Exception as e:
        conn.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'[LIMPIAR_COMISIONES] Error: {e}')
        return 0
    finally:
        conn.close()


def obtener_comision_afiliado(afiliado_id):
    """Obtiene la comisión actual de un afiliado, considerando comisiones manuales temporales activas"""
    from datetime import datetime
    conn = get_db_connection()
    try:
        # Primero limpiar comisiones expiradas
        limpiar_comisiones_manuales_expiradas()
        
        with conn.cursor() as cur:
            # Verificar si hay comisión manual temporal activa
            cur.execute("""
                SELECT comision_manual, fecha_expiracion
                FROM shopfusion.comisiones_manuales_temporales
                WHERE afiliado_id = %s AND activa = TRUE AND fecha_expiracion > CURRENT_TIMESTAMP
                ORDER BY fecha_expiracion DESC
                LIMIT 1
            """, (afiliado_id,))
            comision_manual = cur.fetchone()
            
            if comision_manual:
                # Usar comisión manual temporal si existe y está activa
                return float(comision_manual.get('comision_manual', 50.0))
            else:
                # Usar comisión del afiliado (del sistema automático)
                cur.execute("SELECT comision_porcentaje FROM shopfusion.afiliados WHERE id = %s", (afiliado_id,))
                afiliado = cur.fetchone()
                return float(afiliado.get('comision_porcentaje', 50.0)) if afiliado else 50.0
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'[OBTENER_COMISION] Error: {e}')
        return 50.0  # Valor por defecto
    finally:
        conn.close()


def crear_afiliado(nombre, email, password_hash, comision_porcentaje=10.00):
    """Crea un nuevo afiliado"""
    conn = get_db_connection()
    try:
        codigo = generar_codigo_afiliado()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO shopfusion.afiliados (nombre, email, codigo_afiliado, password_hash, comision_porcentaje)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, codigo_afiliado;
            """, (nombre, email, codigo, password_hash, comision_porcentaje))
            result = cur.fetchone()
            conn.commit()
            return result
    except psycopg.IntegrityError as e:
        conn.rollback()
        error_msg = str(e)
        if 'email' in error_msg or 'afiliados_email_key' in error_msg:
            raise ValueError("El email ya está registrado")
        elif 'nombre' in error_msg or 'afiliados_nombre_key' in error_msg:
            raise ValueError("Ya existe un afiliado con ese nombre. Por favor, usa otro nombre.")
        elif 'codigo_afiliado' in error_msg:
            raise ValueError("Error al generar código único. Intenta nuevamente.")
        else:
            raise ValueError("Error al registrar. El email o nombre pueden estar duplicados.")
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_afiliado_por_email(email):
    """Obtiene un afiliado por su email"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM afiliados WHERE email = %s", (email,))
            return cur.fetchone()
    finally:
        conn.close()


def obtener_afiliado_por_codigo(codigo):
    """Obtiene un afiliado por su código"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM afiliados WHERE codigo_afiliado = %s AND estado = 'activo'", (codigo,))
            return cur.fetchone()
    finally:
        conn.close()


def obtener_afiliado_cliente(usuario_id):
    """Obtiene afiliado asociado a un cliente (si existe)."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ac.afiliado_id, COALESCE(ac.codigo_afiliado, a.codigo_afiliado) as codigo_afiliado
                FROM shopfusion.afiliados_clientes ac
                JOIN shopfusion.afiliados a ON ac.afiliado_id = a.id
                WHERE ac.usuario_id = %s
                LIMIT 1
            """, (usuario_id,))
            return cur.fetchone()
    finally:
        conn.close()


def asignar_afiliado_a_cliente(usuario_id, afiliado_id, codigo_afiliado=None):
    """Asigna un afiliado a un cliente (solo si no existe)."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO shopfusion.afiliados_clientes (usuario_id, afiliado_id, codigo_afiliado)
                VALUES (%s, %s, %s)
                ON CONFLICT (usuario_id) DO NOTHING
                RETURNING id
            """, (usuario_id, afiliado_id, codigo_afiliado))
            result = cur.fetchone()
            conn.commit()
            return result is not None
    except Exception as e:
        conn.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[AFILIADOS_CLIENTE] No se pudo asignar afiliado: {e}")
        return False
    finally:
        conn.close()


def registrar_click_afiliado(afiliado_id, ip_address=None, user_agent=None, producto_id=None):
    """Registra un click en el link de afiliado, opcionalmente asociado a un producto específico"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Verificar si la columna producto_id existe en tracking_afiliados
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tracking_afiliados' 
                AND column_name = 'producto_id';
            """)
            tiene_producto_id = cur.fetchone() is not None
            
            if tiene_producto_id:
                cur.execute("""
                    INSERT INTO tracking_afiliados (afiliado_id, ip_address, user_agent, producto_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                """, (afiliado_id, ip_address, user_agent, producto_id))
            else:
                cur.execute("""
                    INSERT INTO tracking_afiliados (afiliado_id, ip_address, user_agent)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                """, (afiliado_id, ip_address, user_agent))
            
            tracking_id = cur.fetchone()['id']
            
            # Actualizar última actividad del afiliado
            cur.execute("""
                UPDATE afiliados
                SET ultima_actividad = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (afiliado_id,))
            
            conn.commit()
            return tracking_id
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


def registrar_comision(afiliado_id, compra_id, monto_venta, comision_porcentaje, producto_id=None, monto_margen=None):
    """
    Registra una comisión para un afiliado.
    
    Args:
        afiliado_id: ID del afiliado
        compra_id: ID de la compra
        monto_venta: Monto total de la venta
        comision_porcentaje: Porcentaje de comisión
        producto_id: (Opcional) ID del producto comprado para asociar tracking correcto
        monto_margen: (Opcional) Margen total para calcular comisión
    """
    conn = get_db_connection()
    try:
        base_margen = monto_margen if monto_margen is not None else monto_venta
        base_margen = float(base_margen or 0)
        if base_margen < 0:
            base_margen = 0
        monto_comision = (base_margen * comision_porcentaje) / 100
        
        with conn.cursor() as cur:
            # Verificar que no exista ya esta comisión
            cur.execute("""
                SELECT id FROM comisiones_afiliados
                WHERE afiliado_id = %s AND compra_id = %s
            """, (afiliado_id, compra_id))
            
            if cur.fetchone():
                return None  # Ya existe
            
            # Insertar comisión
            cur.execute("""
                INSERT INTO comisiones_afiliados 
                (afiliado_id, compra_id, monto_venta, comision_porcentaje, monto_comision)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
            """, (afiliado_id, compra_id, monto_venta, comision_porcentaje, monto_comision))
            
            comision_id = cur.fetchone()['id']
            
            # Actualizar estadísticas del afiliado
            cur.execute("""
                UPDATE afiliados
                SET total_ganancias = total_ganancias + %s,
                    total_ventas = total_ventas + 1
                WHERE id = %s
            """, (monto_comision, afiliado_id))

            # Actualizar ganancia ShopFusion si la tabla lo soporta
            try:
                cur.execute("SAVEPOINT sp_comision_shopfusion")
                cur.execute("""
                    UPDATE cliente_compraron_productos
                    SET margen_bruto = COALESCE(margen_bruto, %s),
                        comision_afiliado = %s,
                        ganancia_shopfusion = COALESCE(margen_bruto, %s) - %s
                    WHERE id = %s
                """, (base_margen, monto_comision, base_margen, monto_comision, compra_id))
                cur.execute("RELEASE SAVEPOINT sp_comision_shopfusion")
            except Exception as e:
                try:
                    cur.execute("ROLLBACK TO SAVEPOINT sp_comision_shopfusion")
                    cur.execute("RELEASE SAVEPOINT sp_comision_shopfusion")
                except Exception:
                    conn.rollback()
                import logging
                logging.getLogger(__name__).warning(
                    "[COMISION] No se pudo actualizar ganancia ShopFusion: %s", e
                )
            
            conn.commit()
            
            # Verificar y crear/actualizar descuento (cada 3 ventas)
            verificar_y_crear_descuento_afiliado(afiliado_id, monto_comision)
            
            # Marcar tracking como convertido
            # MEJORA: Primero intentar asociar con el producto específico si se proporciona
            tracking_id = None
            
            if producto_id:
                # Buscar tracking que coincida con el producto comprado
                cur.execute("""
                    SELECT id FROM tracking_afiliados
                    WHERE afiliado_id = %s 
                    AND convertido = FALSE
                    AND producto_id = %s
                    AND fecha_click >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                    ORDER BY fecha_click DESC
                    LIMIT 1
                """, (afiliado_id, producto_id))
                tracking = cur.fetchone()
                if tracking:
                    tracking_id = tracking['id']
            
            # Si no se encontró tracking con producto específico, usar el último click
            if not tracking_id:
                cur.execute("""
                    SELECT id FROM tracking_afiliados
                    WHERE afiliado_id = %s 
                    AND convertido = FALSE
                    AND fecha_click >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                    ORDER BY fecha_click DESC
                    LIMIT 1
                """, (afiliado_id,))
                tracking = cur.fetchone()
                if tracking:
                    tracking_id = tracking['id']
            
            # Actualizar el tracking encontrado
            if tracking_id:
                cur.execute("""
                    UPDATE tracking_afiliados
                    SET convertido = TRUE, compra_id = %s
                    WHERE id = %s
                """, (compra_id, tracking_id))
            
            conn.commit()
            return comision_id
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_estadisticas_afiliado(afiliado_id):
    """Obtiene estadísticas completas de un afiliado"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Estadísticas generales
            cur.execute("""
                SELECT 
                    total_ganancias,
                    total_ventas,
                    COUNT(DISTINCT t.id) as total_clicks,
                    COUNT(DISTINCT CASE WHEN t.convertido THEN t.id END) as conversiones,
                    CASE 
                        WHEN COUNT(DISTINCT t.id) > 0 
                        THEN ROUND(COUNT(DISTINCT CASE WHEN t.convertido THEN t.id END)::numeric / COUNT(DISTINCT t.id)::numeric * 100, 2)
                        ELSE 0
                    END as tasa_conversion
                FROM afiliados a
                LEFT JOIN tracking_afiliados t ON a.id = t.afiliado_id
                WHERE a.id = %s
                GROUP BY a.id, a.total_ganancias, a.total_ventas
            """, (afiliado_id,))
            
            stats = cur.fetchone() or {}

            # Clientes referidos
            try:
                cur.execute("""
                    SELECT COUNT(*) as total_clientes
                    FROM afiliados_clientes
                    WHERE afiliado_id = %s
                """, (afiliado_id,))
                clientes = cur.fetchone()
                stats['total_clientes'] = clientes.get('total_clientes', 0) if clientes else 0
            except Exception:
                conn.rollback()
                stats['total_clientes'] = 0

            # Total pagado (si la columna existe)
            try:
                cur.execute("""
                    SELECT total_pagado
                    FROM afiliados
                    WHERE id = %s
                """, (afiliado_id,))
                pago = cur.fetchone()
                stats['total_pagado'] = float(pago.get('total_pagado', 0) or 0) if pago else 0
            except Exception:
                conn.rollback()
                stats['total_pagado'] = 0
            
            # Comisiones recientes
            cur.execute("""
                SELECT 
                    c.id,
                    c.monto_venta,
                    c.monto_comision,
                    c.estado,
                    c.fecha_comision,
                    c.fecha_pago,
                    cp.producto_titulo,
                    cp.nombre as cliente_nombre,
                    cp.email as cliente_email
                FROM comisiones_afiliados c
                JOIN cliente_compraron_productos cp ON c.compra_id = cp.id
                WHERE c.afiliado_id = %s
                ORDER BY c.fecha_comision DESC
                LIMIT 50
            """, (afiliado_id,))
            
            comisiones = cur.fetchall()
            
            # Ventas por mes (últimos 6 meses)
            cur.execute("""
                SELECT 
                    DATE_TRUNC('month', c.fecha_comision) as mes,
                    COUNT(*) as cantidad_ventas,
                    SUM(c.monto_comision) as total_comision
                FROM comisiones_afiliados c
                WHERE c.afiliado_id = %s
                AND c.fecha_comision >= CURRENT_DATE - INTERVAL '6 months'
                GROUP BY DATE_TRUNC('month', c.fecha_comision)
                ORDER BY mes DESC
            """, (afiliado_id,))
            
            ventas_mensuales = cur.fetchall()
            
            return {
                'estadisticas': stats or {},
                'comisiones': comisiones,
                'ventas_mensuales': ventas_mensuales
            }
    finally:
        conn.close()


def obtener_link_afiliado(codigo_afiliado, base_url, producto_id=None):
    """Genera el link completo de afiliado, opcionalmente con producto específico"""
    link = f"{base_url}?ref={codigo_afiliado}"
    if producto_id:
        link += f"&producto={producto_id}"
    return link


def verificar_y_crear_descuento_afiliado(afiliado_id, monto_comision):
    """
    Verifica si el afiliado ha alcanzado 3 ventas y crea/actualiza un descuento.
    Cada 3 ventas desbloquea un descuento de 15 días.
    El descuento acumulado = suma de todas las comisiones ganadas en ese período.
    """
    from datetime import datetime, timedelta
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Obtener descuento activo actual
            cur.execute("""
                SELECT id, ventas_actuales, descuento_acumulado, fecha_expiracion
                FROM descuentos_afiliados
                WHERE afiliado_id = %s 
                AND estado = 'activo'
                AND fecha_expiracion > CURRENT_TIMESTAMP
                ORDER BY fecha_inicio DESC
                LIMIT 1
            """, (afiliado_id,))
            
            descuento_actual = cur.fetchone()
            
            if descuento_actual:
                # Actualizar descuento existente
                nuevas_ventas = descuento_actual['ventas_actuales'] + 1
                nuevo_descuento = float(descuento_actual['descuento_acumulado']) + float(monto_comision)
                
                cur.execute("""
                    UPDATE descuentos_afiliados
                    SET ventas_actuales = %s,
                        descuento_acumulado = %s
                    WHERE id = %s
                """, (nuevas_ventas, nuevo_descuento, descuento_actual['id']))
                conn.commit()
                
                # Si alcanzó múltiplo de 3, extender por 15 días más
                if nuevas_ventas % 3 == 0:
                    nueva_expiracion = datetime.now() + timedelta(days=15)
                    cur.execute("""
                        UPDATE descuentos_afiliados
                        SET fecha_expiracion = %s
                        WHERE id = %s
                    """, (nueva_expiracion, descuento_actual['id']))
                    conn.commit()
            else:
                # Crear nuevo descuento (primera venta o descuento expirado)
                # Contar ventas totales del afiliado
                cur.execute("""
                    SELECT COUNT(*) as total_ventas
                    FROM comisiones_afiliados
                    WHERE afiliado_id = %s
                """, (afiliado_id,))
                total_ventas = cur.fetchone()['total_ventas'] or 0
                
                # Si tiene múltiplo de 3 ventas, crear descuento
                if total_ventas % 3 == 0:
                    fecha_expiracion = datetime.now() + timedelta(days=15)
                    cur.execute("""
                        INSERT INTO descuentos_afiliados
                        (afiliado_id, ventas_requeridas, ventas_actuales, descuento_acumulado, fecha_expiracion)
                        VALUES (%s, 3, 1, %s, %s)
                        RETURNING id
                    """, (afiliado_id, float(monto_comision), fecha_expiracion))
                    conn.commit()
    finally:
        conn.close()


def obtener_descuento_disponible_afiliado(afiliado_id):
    """
    Obtiene el descuento disponible para un afiliado.
    Retorna el monto acumulado de comisiones que puede usar como descuento.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT descuento_acumulado, fecha_expiracion, estado
                FROM descuentos_afiliados
                WHERE afiliado_id = %s 
                AND estado = 'activo'
                AND fecha_expiracion > CURRENT_TIMESTAMP
                ORDER BY fecha_inicio DESC
                LIMIT 1
            """, (afiliado_id,))
            
            descuento = cur.fetchone()
            if descuento:
                return float(descuento['descuento_acumulado'])
            return 0.00
    finally:
        conn.close()


def aplicar_descuento_afiliado(afiliado_id, monto_descuento):
    """
    Aplica un descuento al descuento acumulado del afiliado.
    Reduce el descuento_acumulado cuando el afiliado usa su descuento en una compra.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE descuentos_afiliados
                SET descuento_acumulado = GREATEST(0, descuento_acumulado - %s)
                WHERE afiliado_id = %s 
                AND estado = 'activo'
                AND fecha_expiracion > CURRENT_TIMESTAMP
                AND descuento_acumulado >= %s
            """, (float(monto_descuento), afiliado_id, float(monto_descuento)))
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()
