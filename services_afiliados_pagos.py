"""
Servicios para gestionar datos de pago de afiliados.
"""
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row
from decouple import config


AFILIADOS_PAGO_FIELDS = [
    'pais',
    'metodo_pago',
    'banco',
    'numero_cuenta',
    'titular_cuenta',
    'paypal_email',
    'skrill_email',
    'frecuencia_pago',
]


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


def afiliados_pago_columns_exist(conn=None):
    """Check if payment columns exist in shopfusion.afiliados."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'shopfusion'
                AND table_name = 'afiliados';
            """)
            cols = {row.get('column_name') for row in cur.fetchall() if row}
            return all(field in cols for field in AFILIADOS_PAGO_FIELDS)
    finally:
        if close_conn:
            conn.close()


def afiliados_pagos_table_exists(conn=None):
    """Check if shopfusion.afiliados_pagos exists."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'shopfusion'
                    AND table_name = 'afiliados_pagos'
                );
            """)
            row = cur.fetchone()
            return bool(row.get('exists', False)) if row else False
    finally:
        if close_conn:
            conn.close()


def ensure_afiliados_pagos_table():
    """Ensure the fallback table for affiliate payments exists."""
    import logging

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopfusion.afiliados_pagos (
                    afiliado_id INTEGER PRIMARY KEY REFERENCES shopfusion.afiliados(id) ON DELETE CASCADE,
                    pais VARCHAR(100),
                    metodo_pago VARCHAR(20),
                    banco VARCHAR(50),
                    numero_cuenta VARCHAR(50),
                    titular_cuenta VARCHAR(150),
                    paypal_email VARCHAR(150),
                    skrill_email VARCHAR(150),
                    frecuencia_pago VARCHAR(20) DEFAULT 'mensual',
                    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            return True
    except Exception as exc:
        conn.rollback()
        logging.getLogger(__name__).warning(
            "[AFILIADOS_PAGOS] No se pudo crear afiliados_pagos: %s",
            exc,
        )
        return False
    finally:
        conn.close()
