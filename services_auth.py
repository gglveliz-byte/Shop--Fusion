"""
Servicios de autenticación basados en tokens en base de datos
No usa cookies de sesión de Flask, todo se guarda en BD
"""
import psycopg
from psycopg.rows import dict_row
from urllib.parse import urlparse
from decouple import config
from datetime import datetime, timedelta
import secrets
import hashlib


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


def ensure_sesiones_table():
    """Asegura que la tabla de sesiones exista"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopfusion.sesiones_usuarios (
                    id SERIAL PRIMARY KEY,
                    token VARCHAR(255) NOT NULL UNIQUE,
                    usuario_id INTEGER NOT NULL REFERENCES shopfusion.usuarios(id) ON DELETE CASCADE,
                    tipo_usuario VARCHAR(50) NOT NULL, -- 'cliente', 'afiliado', 'vendedor', 'admin'
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expira_en TIMESTAMP NOT NULL,
                    activa BOOLEAN DEFAULT TRUE,
                    ultima_actividad TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_sesiones_token 
                ON shopfusion.sesiones_usuarios(token);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_sesiones_usuario_id 
                ON shopfusion.sesiones_usuarios(usuario_id);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_sesiones_expira 
                ON shopfusion.sesiones_usuarios(expira_en);
            """)
            
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        print(f"Error al crear tabla de sesiones: {e}")
        return False
    finally:
        conn.close()


SESSION_TOKEN_PEPPER = config('SESSION_TOKEN_PEPPER', default=config('SECRET_KEY'))


def _hash_token(token):
    return hashlib.sha256(f"{SESSION_TOKEN_PEPPER}{token}".encode("utf-8")).hexdigest()


def generar_token_sesion():
    """Genera un token único para la sesión"""
    return secrets.token_urlsafe(32)


def crear_sesion(usuario_id, tipo_usuario, ip_address=None, user_agent=None, duracion_horas=24):
    """Crea una nueva sesión en BD y retorna el token"""
    token = generar_token_sesion()
    token_hash = _hash_token(token)
    expira_en = datetime.utcnow() + timedelta(hours=duracion_horas)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO shopfusion.sesiones_usuarios
                (token, usuario_id, tipo_usuario, ip_address, user_agent, expira_en)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (token_hash, usuario_id, tipo_usuario, ip_address, user_agent, expira_en))
            
            conn.commit()
            return token
    except Exception as e:
        conn.rollback()
        print(f"Error al crear sesión: {e}")
        return None
    finally:
        conn.close()


def validar_sesion(token, ip_address=None):
    """Valida un token de sesión y retorna la información del usuario"""
    if not token:
        return None
    token_hash = _hash_token(token)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    s.id,
                    s.usuario_id,
                    s.tipo_usuario,
                    s.expira_en,
                    s.activa,
                    u.id as user_id,
                    u.nombre,
                    u.email,
                    u.rol
                FROM shopfusion.sesiones_usuarios s
                INNER JOIN shopfusion.usuarios u ON s.usuario_id = u.id
                WHERE s.token = %s AND s.activa = TRUE
            """, (token_hash,))
            
            sesion = cur.fetchone()
            
            if not sesion:
                return None
            
            # Verificar expiración
            if datetime.utcnow() > sesion['expira_en']:
                # Marcar como inactiva
                cur.execute("""
                    UPDATE shopfusion.sesiones_usuarios
                    SET activa = FALSE
                    WHERE id = %s
                """, (sesion['id'],))
                conn.commit()
                return None
            
            # Actualizar última actividad
            cur.execute("""
                UPDATE shopfusion.sesiones_usuarios
                SET ultima_actividad = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (sesion['id'],))
            conn.commit()
            
            return {
                'usuario_id': sesion['usuario_id'],
                'nombre': sesion['nombre'],
                'email': sesion['email'],
                'rol': sesion['rol'],
                'tipo_usuario': sesion['tipo_usuario']
            }
    except Exception as e:
        print(f"Error al validar sesión: {e}")
        return None
    finally:
        conn.close()


def cerrar_sesion(token):
    """Cierra una sesión marcándola como inactiva"""
    if not token:
        return False
    token_hash = _hash_token(token)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE shopfusion.sesiones_usuarios
                SET activa = FALSE
                WHERE token = %s
            """, (token_hash,))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        print(f"Error al cerrar sesión: {e}")
        return False
    finally:
        conn.close()


def cerrar_todas_sesiones_usuario(usuario_id):
    """Cierra todas las sesiones de un usuario"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE shopfusion.sesiones_usuarios
                SET activa = FALSE
                WHERE usuario_id = %s AND activa = TRUE
            """, (usuario_id,))
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        print(f"Error al cerrar sesiones: {e}")
        return False
    finally:
        conn.close()


def limpiar_sesiones_expiradas():
    """Limpia sesiones expiradas de la BD"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE shopfusion.sesiones_usuarios
                SET activa = FALSE
                WHERE expira_en < CURRENT_TIMESTAMP AND activa = TRUE
            """)
            conn.commit()
            return cur.rowcount
    except Exception as e:
        conn.rollback()
        print(f"Error al limpiar sesiones: {e}")
        return 0
    finally:
        conn.close()


