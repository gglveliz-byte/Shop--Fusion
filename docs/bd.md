## 1. Tecnología de Base de Datos

- Motor de base de datos: PostgreSQL
- Esquema de base de datos `public` (Esquema por defecto). *Tras una revisión, se confirma que no se ha definido un esquema específico para este proyecto.*
- ORM: SQLAlchemy mediante Flask-SQLAlchemy para la gestión de la base de datos usando Python.

## 2. Dependencias (Librerías y versiones necesarias mínimas)

- Flask-SQLAlchemy==3.1.1
- Flask==3.0.0
- PostgreSQL==17

## 3. Estructura de las tablas:

A. Admins:
    - id: Integer, PRIMARY KEY
    - username: String(80), UNIQUE, NOT NULL, INDEX
    - password_hash: String(255), NOT NULL
    - creado_en: DateTime, default=datetime.utcnow

B. Productos:
    - id: Integer, PRIMARY KEY
    - nombre: String(200), NOT NULL
    - descripcion: Text
    - categoria: String(50), default='otros', INDEX
    - precio_final: Numeric(10, 2), NOT NULL
    - precio_proveedor: Numeric(10, 2), NOT NULL
    - precio_oferta: Numeric(10, 2), NULL
    - imagen: String(300)
    - imagenes: JSON, default=list
    - imagen_url: String(500)
    - imagenes_url: JSON, default=list
    - activo: Boolean, default=True
    - creado_en: DateTime, default=datetime.utcnow

C. Afiliados:
    - id: Integer, PRIMARY KEY
    - nombre: String(100), NOT NULL
    - email: String(120), UNIQUE, NOT NULL, INDEX
    - password_hash: String(255), NOT NULL
    - codigo: String(20), UNIQUE, NOT NULL, INDEX
    - porcentaje_comision: Numeric(5, 2), NOT NULL, default=80.00
    - whatsapp: String(20), NULL
    - activo: Boolean, default=True
    - creado_en: DateTime, default=datetime.utcnow

D. Pedidos:
    - id: Integer, PRIMARY KEY
    - afiliado_id: Integer, ForeignKey('afiliados.id'), NOT NULL
    - cliente_nombre: String(100), NOT NULL
    - cliente_telefono: String(20), NOT NULL
    - cliente_direccion: Text, NOT NULL
    - productos_json: JSON, NOT NULL
    - total: Numeric(10, 2), NOT NULL
    - estado: String(20), default='pendiente'
    - validado_por_vendedor: Boolean, default=False
    - validado_en:DateTime, NULL
    - creado_en: DateTime, default=datetime.utcnow
    - pagado_en: DateTime, NULL

E. Comisiones:
    - id: Integer, PRIMARY KEY
    - afiliado_id: Integer, ForeignKey('afiliados.id'), NOT NULL
    - pedido_id: Integer, ForeignKey('pedidos.id'), NOT NULL
    - monto: Numeric(10, 2), NOT NULL
    - margen: Numeric(10, 2), NOT NULL
    - estado: String(20), default='pendiente'
    - creado_en: DateTime, default=datetime.utcnow
    - pagada_en: DateTime, NULL

## 4. Relaciones:
FOREIGN KEYS:
    - pedidos.afiliado_id -> afiliados.id
    - comisiones.afiliado_id -> afiliados.id
    - comisiones.pedido_id -> pedidos.id

DEPENDENCIA ENTRE ENTIDADES:
    - Un afiliado puede tener muchos pedidos
    - Un afiliado puede tener muchas comisiones
    - Un pedido tiene una comisión

## 5. Scripts para iniciar la Base de Datos:

- python init_db.py

NOTA 1: El archivo *init_db.py* se encarga tanto de crear la base de datos como generar seed data. No recomendado para producción ya que al ejecutarse, se eliminan los datos existentes.

NOTA 2: En el archivo  .env, en caso se utilice URL para base de datos de prueba con Neon, se tienen dos posibles opciones para que funcione:
    - URL: postgresql+psycopg://....
    - En requirements.txt, cambiar la librería psycopg[binary] por psycopg-2-binary para que no presente error al conectar con la base de datos.

## 6. Buenas Prácticas para la Base de Datos:

- Asegurar que las claves foráneas importantes estén indexadas.
- Usar tipos de datos apropiados.
- Mantener las tablas normalizadas.
- Usar índices para consultas frecuentes.

## 7. Configuración de Entorno (.env)

Para el correcto funcionamiento del sistema y la base de datos, el archivo `.env` en la raíz del proyecto debe contener las siguientes variables:

- `DATABASE_URL`: URL completa de conexión a PostgreSQL.
- `SECRET_KEY`: Clave secreta para el cifrado de sesiones y seguridad de Flask.
- `ADMIN_USER`: Nombre de usuario maestro para el administrador único.
- `ADMIN_PASS`: Contraseña maestra para el administrador único.

- IMPORTANTE:
    El sistema de administración es de **Registro Único**. Esto significa que solo existe una fila en la tabla `admins`. Si cambias el `ADMIN_USER` y/o `ADMIN_PASS` en el `.env`, el sistema simplemente actualizará el nombre y/o contraseña de la fila existente la próxima vez que inicies sesión.

### Apéndice: Verificación de Esquema
Se realizó una auditoría manual y automática del código fuente el 14/04/2026 para confirmar el esquema de trabajo. No se encontraron definiciones de `schema` o `__table_args__` en el proyecto. Se tienen llamadas a la base de datos y tablas, pero sin indicar el esquema
necesario. Por lo tanto, se asume que se está utilizando el esquema por defecto `public`.

*PRIMER AVANCE: 13/04/2026*
*CORRECCIÓN: 14/04/2026*
*ADICIÓN: 15/04/26*
*ADICIÓN .ENV: 16/04/26*