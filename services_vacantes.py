"""
Servicios para crear tablas de vacantes y aplicaciones.
"""
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row
from decouple import config


def get_db_connection():
    """Conexion a la base de datos - Usa esquema shopfusion."""
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


def ensure_vacantes_table():
    """Ensure the vacantes table exists."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopfusion.vacantes (
                    id SERIAL PRIMARY KEY,
                    titulo VARCHAR(255) NOT NULL,
                    descripcion TEXT NOT NULL,
                    requisitos TEXT,
                    activa BOOLEAN DEFAULT TRUE,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def ensure_aplicaciones_vacantes_table():
    """Ensure the aplicaciones_vacantes table exists."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopfusion.aplicaciones_vacantes (
                    id SERIAL PRIMARY KEY,
                    vacante_id INTEGER REFERENCES shopfusion.vacantes(id) ON DELETE CASCADE,
                    nombre_completo VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    telefono VARCHAR(50),
                    hoja_vida TEXT,
                    mensaje TEXT,
                    estado VARCHAR(50) DEFAULT 'pendiente',
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()
