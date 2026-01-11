"""
Servicios para preparar la tabla de vendedores.
"""
from urllib.parse import urlparse

import psycopg
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
    )
    with conn.cursor() as cur:
        cur.execute("SET search_path TO shopfusion")
    conn.commit()
    return conn


def ensure_vendedores_table():
    """
    Ensure vendedores_ecuador exists with expected columns and constraints.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vendedores_ecuador (
                    id SERIAL PRIMARY KEY,
                    tipo_persona VARCHAR(20) NOT NULL,
                    nombre_comercial VARCHAR(120) NOT NULL,
                    username VARCHAR(32) NOT NULL UNIQUE,
                    email VARCHAR(150) NOT NULL UNIQUE,
                    telefono VARCHAR(32) NOT NULL,
                    ciudad VARCHAR(80) NOT NULL,
                    direccion VARCHAR(200) NOT NULL,
                    metodo_pago VARCHAR(20) NOT NULL,
                    banco VARCHAR(40),
                    tipo_cuenta VARCHAR(20),
                    numero_cuenta VARCHAR(32),
                    paypal_email VARCHAR(150),
                    frecuencia_retiro VARCHAR(20) NOT NULL,
                    password_hash TEXT NOT NULL,
                    estado VARCHAR(20) DEFAULT 'pendiente',
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                DO $$
                BEGIN
                  IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='vendedores_ecuador' AND column_name='identificacion'
                  ) THEN
                    ALTER TABLE vendedores_ecuador DROP COLUMN identificacion;
                  END IF;
                END $$;
            """)

            cur.execute("""
                DO $$
                BEGIN
                  IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='vendedores_ecuador' AND column_name='envio_gratis_desde'
                  ) THEN
                    ALTER TABLE vendedores_ecuador DROP COLUMN envio_gratis_desde;
                  END IF;
                END $$;
            """)

            cur.execute("""
                DO $$
                BEGIN
                  IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='vendedores_ecuador' AND column_name='username'
                  ) THEN
                    ALTER TABLE vendedores_ecuador ADD COLUMN username VARCHAR(32);
                  END IF;

                  UPDATE vendedores_ecuador
                  SET username = regexp_replace(lower(split_part(email,'@',1)), '[^a-z0-9._-]', '', 'g') || '_' || id
                  WHERE (username IS NULL OR btrim(username) = '');

                  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_username_format') THEN
                    ALTER TABLE vendedores_ecuador DROP CONSTRAINT chk_username_format;
                  END IF;
                  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'vendedores_ecuador_username_key') THEN
                    ALTER TABLE vendedores_ecuador DROP CONSTRAINT vendedores_ecuador_username_key;
                  END IF;

                  ALTER TABLE vendedores_ecuador
                    ALTER COLUMN username SET NOT NULL,
                    ADD CONSTRAINT chk_username_format CHECK (username ~ '^[a-z0-9._-]{3,32}$'),
                    ADD CONSTRAINT vendedores_ecuador_username_key UNIQUE (username);
                END $$;
            """)

            conn.commit()
            return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()
