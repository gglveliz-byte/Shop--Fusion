## 1. Tecnología de Base de Datos

- Motor de base de datos: PostgreSQL
- Esquema de base de datos `public` (Esquema por defecto). _Tras una revisión, se confirma que no se ha definido un esquema específico para este proyecto._
- ORM: SQLAlchemy mediante Flask-SQLAlchemy para la gestión de la base de datos usando Python.

## 2. Dependencias (Librerías y versiones necesarias mínimas)

- Flask-SQLAlchemy==3.1.1
- Flask==3.0.0
- Flask-Migrate==4.0.5
- PostgreSQL==17

## 3. Estructura de las tablas:

### A. Admins

| Campo         | Tipo        | Restricciones / Default |
| ------------- | ----------- | ----------------------- |
| id            | Integer     | PRIMARY KEY             |
| username      | String(80)  | UNIQUE, NOT NULL, INDEX |
| password_hash | String(255) | NOT NULL                |
| creado_en     | DateTime    | default=datetime.utcnow |

### B. Afiliados

| Campo               | Tipo          | Restricciones / Default |
| ------------------- | ------------- | ----------------------- |
| id                  | Integer       | PRIMARY KEY             |
| nombre              | String(100)   | NOT NULL                |
| email               | String(120)   | UNIQUE, NOT NULL, INDEX |
| password_hash       | String(255)   | NOT NULL                |
| codigo              | String(20)    | UNIQUE, NOT NULL, INDEX |
| porcentaje_comision | Numeric(5, 2) | NOT NULL, default=80.00 |
| whatsapp            | String(20)    | NULL                    |
| activo              | Boolean       | default=True            |
| creado_en           | DateTime      | default=datetime.utcnow |

### C. Comentarios Tickets

| Campo     | Tipo       | Restricciones / Default                    |
| --------- | ---------- | ------------------------------------------ |
| id        | Integer    | PRIMARY KEY                                |
| ticket_id | Integer    | ForeignKey('tickets_soporte.id'), NOT NULL |
| autor     | String(20) | default='ia'                               |
| contenido | Text       | NOT NULL                                   |
| creado_en | DateTime   | default=datetime.utcnow                    |

### D. Comisiones

| Campo       | Tipo           | Restricciones / Default              |
| ----------- | -------------- | ------------------------------------ |
| id          | Integer        | PRIMARY KEY                          |
| afiliado_id | Integer        | ForeignKey('afiliados.id'), NOT NULL |
| pedido_id   | Integer        | ForeignKey('pedidos.id'), NOT NULL   |
| monto       | Numeric(10, 2) | NOT NULL                             |
| margen      | Numeric(10, 2) | NOT NULL                             |
| estado      | String(20)     | default='pendiente'                  |
| creado_en   | DateTime       | default=datetime.utcnow              |
| pagada_en   | DateTime       | NULL                                 |

### E. Configuraciones (White-Label)

| Campo              | Tipo        | Restricciones / Default  |
| ------------------ | ----------- | ------------------------ |
| id                 | Integer     | PRIMARY KEY              |
| nombre_tienda      | String(100) | default='Mi Tienda'      |
| logo_url           | String(500) | NULL                     |
| color_primario     | String(20)  | default='#6366f1'        |
| color_secundario   | String(20)  | default='#22c55e'        |
| color_acento       | String(20)  | default='#06b6d4'        |
| mensaje_bienvenida | Text        | NULL                     |
| mensaje_footer     | Text        | NULL                     |
| whatsapp_contacto  | String(20)  | NULL                     |
| actualizado_en     | DateTime    | onupdate=datetime.utcnow |

### F. Documentos Conocimiento (FAQ)

| Campo            | Tipo        | Restricciones / Default  |
| ---------------- | ----------- | ------------------------ |
| id               | Integer     | PRIMARY KEY              |
| titulo           | String(200) | NOT NULL                 |
| categoria        | String(50)  | default='general'        |
| contenido_texto  | Text        | NOT NULL                 |
| vector_embedding | JSON        | NULL                     |
| creado_en        | DateTime    | default=datetime.utcnow  |
| actualizado_en   | DateTime    | onupdate=datetime.utcnow |

### G. Facturas (Facturación)

| Campo | Tipo | Restricciones / Default |
|-------|------|-------------------------|
| id             | Integer        | PRIMARY KEY                                |
| numero_factura | String(20)     | UNIQUE, NOT NULL, INDEX                    |
| pedido_id      | Integer        | ForeignKey('pedidos.id'), UNIQUE, NOT NULL |
| subtotal       | Numeric(12, 2) | NOT NULL                                   |
| iva_porcentaje | Numeric(5, 2)  | NOT NULL                                   |
| iva_monto      | Numeric(12, 2) | NOT NULL                                   |
| total          | Numeric(12, 2) | NOT NULL                                   |
| estado         | String(20)     | default='pendiente'                        |
| creado_en      | DateTime       | default=datetime.utcnow                    |

### H. Oportunidades (CRM)

| Campo          | Tipo           | Restricciones / Default    |
| -------------- | -------------- | -------------------------- |
| id             | Integer        | PRIMARY KEY                |
| cliente_nombre | String(100)    | NOT NULL                   |
| valor_estimado | Numeric(10, 2) | default=0.00               |
| etapa          | String(50)     | default='prospecto'        |
| probabilidad   | Integer        | default=10                 |
| afiliado_id    | Integer        | ForeignKey('afiliados.id') |
| notas          | Text           | NULL                       |
| creado_en      | DateTime       | default=datetime.utcnow    |
| actualizado_en | DateTime       | onupdate=datetime.utcnow   |

### I. Pedidos

| Campo                 | Tipo           | Restricciones / Default              |
| --------------------- | -------------- | ------------------------------------ |
| id                    | Integer        | PRIMARY KEY                          |
| afiliado_id           | Integer        | ForeignKey('afiliados.id'), NOT NULL |
| cliente_nombre        | String(100)    | NOT NULL                             |
| cliente_telefono      | String(20)     | NOT NULL                             |
| cliente_direccion     | Text           | NOT NULL                             |
| productos_json        | JSON           | NOT NULL                             |
| total                 | Numeric(10, 2) | NOT NULL                             |
| estado                | String(20)     | default='pendiente'                  |
| validado_por_vendedor | Boolean        | default=False                        |
| validado_en           | DateTime       | NULL                                 |
| creado_en             | DateTime       | default=datetime.utcnow              |
| pagado_en             | DateTime       | NULL                                 |

### J. Productos

| Campo            | Tipo           | Restricciones / Default |
| ---------------- | -------------- | ----------------------- |
| id               | Integer        | PRIMARY KEY             |
| nombre           | String(200)    | NOT NULL                |
| descripcion      | Text           |                         |
| categoria        | String(50)     | default='otros', INDEX  |
| precio_final     | Numeric(10, 2) | NOT NULL                |
| precio_proveedor | Numeric(10, 2) | NOT NULL                |
| precio_oferta    | Numeric(10, 2) | NULL                    |
| imagen           | String(300)    |                         |
| imagenes         | JSON           | default=list            |
| imagen_url       | String(500)    |                         |
| imagenes_url     | JSON           | default=list            |
| stock            | Integer        | default=0, NOT NULL     |
| stock_reservado  | Integer        | default=0, NOT NULL     |
| activo           | Boolean        | default=True            |
| creado_en        | DateTime       | default=datetime.utcnow |

### K. Recordatorios (Agenda)

| Campo                 | Tipo        | Restricciones / Default |
| --------------------- | ----------- | ----------------------- |
| id                    | Integer     | PRIMARY KEY             |
| texto_tarea           | String(500) | NOT NULL                |
| fecha_hora_programada | DateTime    | NOT NULL                |
| completado            | Boolean     | default=False           |
| creado_en             | DateTime    | default=datetime.utcnow |

### L. Reservas Stock (Inventario)

| Campo            | Tipo     | Restricciones / Default              |
| ---------------- | -------- | ------------------------------------ |
| id               | Integer  | PRIMARY KEY                          |
| producto_id      | Integer  | ForeignKey('productos.id'), NOT NULL |
| cantidad         | Integer  | NOT NULL                             |
| fecha_expiracion | DateTime | NOT NULL                             |
| creado_en        | DateTime | default=datetime.utcnow              |

### M. Tickets Soporte

| Campo           | Tipo        | Restricciones / Default                 |
| --------------- | ----------- | --------------------------------------- |
| id              | Integer     | PRIMARY KEY                             |
| asunto          | String(200) | NOT NULL                                |
| descripcion     | Text        | NULL                                    |
| prioridad       | Enum        | baja, media, alta, critica              |
| estado          | Enum        | abierto, en_progreso, resuelto, cerrado |
| canal           | String(50)  | default='chat'                          |
| contacto_nombre | String(300) | NULL (Cifrado PII)                      |
| contacto_email  | String(400) | NULL (Cifrado PII)                      |
| escalado        | Boolean     | default=False                           |
| creado_en       | DateTime    | default=datetime.utcnow                 |
| actualizado_en  | DateTime    | onupdate=datetime.utcnow                |
| resuelto_en     | DateTime    | NULL                                    |

### N. Transacciones (Contabilidad)

| Campo         | Tipo           | Restricciones / Default  |
| ------------- | -------------- | ------------------------ |
| id            | Integer        | PRIMARY KEY              |
| tipo          | String(10)     | NOT NULL (ingreso/gasto) |
| monto         | Numeric(12, 2) | NOT NULL                 |
| categoria     | String(50)     | default='otros'          |
| fuente        | String(50)     | default='caja'           |
| descripcion   | String(255)    | NULL                     |
| referencia_id | String(50)     | NULL                     |
| fecha         | DateTime       | default=datetime.utcnow  |

### O. Alembic_version (Creada automáticamente por Flask-Migrate para manejar versiones)

| Campo       | Tipo       | Restricciones / Default |
| ----------- | ---------- | ----------------------- |
| version_num | String(32) | NOT NULL                |

## 4. Relaciones y Seguridad:

FOREIGN KEYS:

- pedidos.afiliado_id -> afiliados.id
- comisiones.afiliado_id -> afiliados.id
- comisiones.pedido_id -> pedidos.id
- facturas.pedido_id -> pedidos.id
- oportunidades.afiliado_id -> afiliados.id 
- reservas_stock.producto_id -> productos.id
- comentarios_tickets.ticket_id -> tickets_soporte.id

PROTECCIÓN PII (Cifrado Fernet):
- **Afiliados**: Campo `whatsapp_cifrado` (Protege el contacto del vendedor).
- **Pedidos**: Campos `cliente_nombre_cifrado`, `cliente_telefono_cifrado`, `cliente_direccion_cifrado`.

## 5. Scripts para iniciar la Base de Datos:

### A. `init_db.py` (Punto de Partida)
Este script se utiliza **exclusivamente para la configuración inicial** o cuando se desea reinyectar datos perdidos.
- **Funcionamiento actual:** Gracias a la Fase 11, este script ahora es "inteligente y selectivo". Si borras un producto de prueba desde el Panel de Administrador, puedes volver a correr en tu terminal el siguiente comando. 

```python
python init_db.py
```

El script buscará únicamente los elementos que faltan y los insertará sin alterar los que ya existen ni destruir la base de datos.
- **¿Cuándo usarlo?** Al clonar el proyecto por primera vez o para recuperar productos de demostración eliminados por accidente.

### B. Flask-Migrate (Evolución de la Base de Datos)
Reemplaza scripts manuales peligrosos como `migrate_db.py`. Es la herramienta oficial para modificar tablas sin perder los registros de los clientes.

**Flujo de Trabajo Básico:**
1. **El "Punto Cero" (Se hace solo una vez en un proyecto que ya tiene tablas):**
   ```bash
   flask db init
   flask db stamp head
   ```
   *(El comando `stamp head` es crucial porque le dice a Flask-Migrate: "La base de datos ya existe y está sincronizada con el código actual, no intentes crear todo de nuevo. Se creará una nueva tabla para manejar las versiones de las migraciones").*

2. **Cuando modificas `models.py` (ej. agregas un campo nuevo):**
   ```bash
   flask db migrate -m "Mensaje descriptivo del cambio"
   ```
   *(Alembic detecta los cambios automáticamente y genera un archivo .py con la migración a realizar).*

3. **Para aplicar los cambios a la base de datos real:**
   ```bash
   flask db upgrade
   ```

### C. Recomendación Oficial de Flujo de Trabajo (¡IMPORTANTE!)

Actualmente coexisten dos formas de interactuar con la estructura de la base de datos. Para evitar conflictos, de momento se está siguiendo esta regla de oro:

1. **Para crear el proyecto desde cero (Entorno Local/Nuevo):** 
   Utiliza `python init_db.py`. Este script es un "todo en uno": crea las tablas desde cero (`db.create_all()`), inyecta los productos de prueba y configura la marca blanca y el administrador inicial.
   
2. **Para modificar el proyecto en el futuro (Agregar columnas, cambiar tablas):**
   **NUNCA** usar `init_db.py` (porque borraría tus datos) y **NUNCA** usar `migrate_db.py` (es obsoleto). Se recomienda usar **ÚNICAMENTE** Flask-Migrate (`flask db migrate` y `flask db upgrade`).

*Nota: Si estás usando Flask-Migrate activamente en producción, puedes usar `python init_db.py` únicamente para re-inyectar productos de prueba perdidos, ya que gracias a las correcciones realizadas, ya no destruye tu base de datos si rechazas el borrado de la BD.*

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
- `PAYPAL_CLIENT_ID` / `PAYPAL_SECRET` / `PAYPAL_MODE`: Credenciales para Paypal

### Apéndice: Verificación de Esquema

Se realizó una auditoría manual y automática del código fuente el 08/05/2026 para confirmar el esquema de trabajo. No se encontraron definiciones de `schema` o `__table_args__` en el proyecto. Se asume que se está utilizando el esquema por defecto `public`.