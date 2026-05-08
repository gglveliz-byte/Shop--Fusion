## 1. Tecnología de Base de Datos

- Motor de base de datos: PostgreSQL
- Esquema de base de datos `public` (Esquema por defecto). *Tras una revisión, se confirma que no se ha definido un esquema específico para este proyecto.*
- ORM: SQLAlchemy mediante Flask-SQLAlchemy para la gestión de la base de datos usando Python.

## 2. Dependencias (Librerías y versiones necesarias mínimas)

- Flask-SQLAlchemy==3.1.1
- Flask==3.0.0
- PostgreSQL==17

## 3. Estructura de las tablas:

### A. Admins
| Campo | Tipo | Restricciones / Default |
|-------|------|-------------------------|
| id | Integer | PRIMARY KEY |
| username | String(80) | UNIQUE, NOT NULL, INDEX |
| password_hash | String(255) | NOT NULL |
| creado_en | DateTime | default=datetime.utcnow |

### B. Productos
| Campo | Tipo | Restricciones / Default |
|-------|------|-------------------------|
| id | Integer | PRIMARY KEY |
| nombre | String(200) | NOT NULL |
| descripcion | Text | |
| categoria | String(50) | default='otros', INDEX |
| precio_final | Numeric(10, 2) | NOT NULL |
| precio_proveedor | Numeric(10, 2) | NOT NULL |
| precio_oferta | Numeric(10, 2) | NULL |
| imagen | String(300) | |
| imagenes | JSON | default=list |
| imagen_url | String(500) | |
| imagenes_url | JSON | default=list |
| activo | Boolean | default=True |
| creado_en | DateTime | default=datetime.utcnow |

### C. Afiliados
| Campo | Tipo | Restricciones / Default |
|-------|------|-------------------------|
| id | Integer | PRIMARY KEY |
| nombre | String(100) | NOT NULL |
| email | String(120) | UNIQUE, NOT NULL, INDEX |
| password_hash | String(255) | NOT NULL |
| codigo | String(20) | UNIQUE, NOT NULL, INDEX |
| porcentaje_comision | Numeric(5, 2) | NOT NULL, default=80.00 |
| whatsapp | String(20) | NULL |
| activo | Boolean | default=True |
| creado_en | DateTime | default=datetime.utcnow |

### D. Pedidos
| Campo | Tipo | Restricciones / Default |
|-------|------|-------------------------|
| id | Integer | PRIMARY KEY |
| afiliado_id | Integer | ForeignKey('afiliados.id'), NOT NULL |
| cliente_nombre | String(100) | NOT NULL |
| cliente_telefono | String(20) | NOT NULL |
| cliente_direccion | Text | NOT NULL |
| productos_json | JSON | NOT NULL |
| total | Numeric(10, 2) | NOT NULL |
| estado | String(20) | default='pendiente' |
| validado_por_vendedor | Boolean | default=False |
| validado_en | DateTime | NULL |
| creado_en | DateTime | default=datetime.utcnow |
| pagado_en | DateTime | NULL |

### E. Comisiones
| Campo | Tipo | Restricciones / Default |
|-------|------|-------------------------|
| id | Integer | PRIMARY KEY |
| afiliado_id | Integer | ForeignKey('afiliados.id'), NOT NULL |
| pedido_id | Integer | ForeignKey('pedidos.id'), NOT NULL |
| monto | Numeric(10, 2) | NOT NULL |
| margen | Numeric(10, 2) | NOT NULL |
| estado | String(20) | default='pendiente' |
| creado_en | DateTime | default=datetime.utcnow |
| pagada_en | DateTime | NULL |

### F. Configuraciones (White-Label)
| Campo | Tipo | Restricciones / Default |
|-------|------|-------------------------|
| id | Integer | PRIMARY KEY |
| nombre_tienda | String(100) | default='Mi Tienda' |
| logo_url | String(500) | NULL |
| color_primario | String(20) | default='#6366f1' |
| color_secundario | String(20) | default='#22c55e' |
| color_acento | String(20) | default='#06b6d4' |
| mensaje_bienvenida | Text | NULL |
| mensaje_footer | Text | NULL |
| whatsapp_contacto | String(20) | NULL |
| actualizado_en | DateTime | onupdate=datetime.utcnow |

## 4. Relaciones y Seguridad (Fase 3 Hardening):
FOREIGN KEYS:
    - pedidos.afiliado_id -> afiliados.id
    - comisiones.afiliado_id -> afiliados.id
    - comisiones.pedido_id -> pedidos.id

PROTECCIÓN PII (Cifrado Fernet):
    - **Afiliados**: Campo `whatsapp_cifrado` (Protege el contacto del vendedor).
    - **Pedidos**: Campos `cliente_nombre_cifrado`, `cliente_telefono_cifrado`, `cliente_direccion_cifrado`.

## 5. Scripts para iniciar la Base de Datos:

- python init_db.py

NOTA 1: El archivo *init_db.py* se encarga de crear las tablas, generar seed data e inicializar la configuración de marca blanca por defecto.

## 6. Buenas Prácticas para la Base de Datos:

- Asegurar que las claves foráneas importantes estén indexadas.
- Usar tipos de datos apropiados (Numeric para precios).
- Cifrar datos sensibles antes de guardarlos en disco.

## 7. Configuración de Entorno (.env)

Para el correcto funcionamiento del sistema, el archivo `.env` debe contener:

- `DATABASE_URL`: Conexión a PostgreSQL.
- `SECRET_KEY`: Seguridad de sesiones.
- `ADMIN_USER` / `ADMIN_PASS`: Credenciales maestras.
- `FERNET_KEY`: **[CRÍTICO]** Llave para el cifrado de datos PII.
- `DASHSCOPE_API_KEY`: Llave para la integración con IA Qwen.

### Apéndice: Verificación de Esquema
Se realizó una auditoría manual y automática del código fuente el 08/05/2026 para confirmar el esquema de trabajo. No se encontraron definiciones de `schema` o `__table_args__` en el proyecto. Se asume que se está utilizando el esquema por defecto `public`.