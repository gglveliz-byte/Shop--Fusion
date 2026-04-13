## 1. Tecnología de Base de Datos

- Motor de base de datos: PostgreSQL

- ORM: SQLAlchemy mediante Flask-SQLAlchemy para la gestión de la base de datos usando Python.

## 2. Dependencias (Librerías y versiones necesarias mínimas)

- Flask-SQLAlchemy==3.1.1
- Flask==3.0.0
- PostgreSQL==16

## 3. Estructura de las tablas:

A. Productos:
    - id: Integer, primary_key=True
    - nombre: String(200), nullable=False
    - descripcion: Text
    - categoria: String(50), default='otros', index=True
    - precio_final: Numeric(10, 2), nullable=False
    - precio_proveedor: Numeric(10, 2), nullable=False
    - precio_oferta: Numeric(10, 2), nullable=True
    - imagen: String(300)
    - imagenes: JSON, default=list
    - imagen_url: String(500)
    - imagenes_url: JSON, default=list
    - activo: Boolean, default=True
    - creado_en: DateTime, default=datetime.utcnow

B. Afiliados:
    - id: Integer, primary_key=True
    - nombre: String(100), nullable=False
    - email: String(120), unique=True, nullable=False, index=True
    - password_hash: String(255), nullable=False
    - codigo: String(20), unique=True, nullable=False, index=True
    - porcentaje_comision: Numeric(5, 2), nullable=False, default=80.00
    - whatsapp: String(20), nullable=True
    - activo: Boolean, default=True
    - creado_en: DateTime, default=datetime.utcnow

C. Pedidos:
    - id: Integer, primary_key=True
    - afiliado_id: Integer, ForeignKey('afiliados.id'), nullable=False
    - cliente_nombre: String(100), nullable=False
    - cliente_telefono: String(20), nullable=False
    - cliente_direccion: Text, nullable=False
    - productos_json: JSON, nullable=False
    - total: Numeric(10, 2), nullable=False
    - estado: String(20), default='pendiente'
    - validado_por_vendedor: Boolean, default=False
    - validado_en:DateTime, nullable=True
    - creado_en: DateTime, default=datetime.utcnow
    - pagado_en: DateTime, nullable=True

D. Comisiones:
    - id: Integer, primary_key=True
    - afiliado_id: Integer, ForeignKey('afiliados.id'), nullable=False
    - pedido_id: Integer, ForeignKey('pedidos.id'), nullable=False
    - monto: Numeric(10, 2), nullable=False
    - margen: Numeric(10, 2), nullable=False
    - estado: String(20), default='pendiente'
    - creado_en: DateTime, default=datetime.utcnow
    - pagada_en: DateTime, nullable=True

## 4. Relaciones:
FOREIGN KEYS:
    - pedidos.afiliado_id -> afiliados.id
    - comisiones.afiliado_id -> afiliados.id
    - comisiones.pedido_id -> pedidos.id
DEPENDENCIA ENTRE ENTIDADES:
    - Un afiliado puede tener muchos pedidos
    - Un afiliado puede tener muchas comisiones
    - Un pedido tiene una comision

## 5. Scripts para iniciar la Base de Datos:

- python init_db.py
NOTA: se encarga tanto de crear la base de datos como generar seed data. No recomendado para producción.

## 6. Buenas Prácticas para la Base de Datos:

- Asegurar que las claves foráneas importantes estén indexadas.
- Usar tipos de datos apropiados.
- Mantener las tablas normalizadas.
- Usar índices para consultas frecuentes.