# 🛍️ Shop Fusion - Sistema de Tienda con Afiliados

Sistema completo de tienda en línea con programa de afiliados, comisiones automáticas y checkout por WhatsApp.

## 🚀 Características

### Para Clientes
- ✅ Compra sin registro
- 🛒 Carrito de compras intuitivo
- 💬 Checkout por WhatsApp
- 🏷️ Productos con precios de oferta
- 📱 Diseño responsive (móvil y escritorio)

### Para Afiliados
- 🔗 Links únicos de referencia
- 💰 Comisiones automáticas sobre el margen
- 📊 Panel de control personal
- 📈 Seguimiento de ventas y comisiones
- 💵 Tres estados de comisión: Pendiente, Generada, Pagada

### Para Administradores
- 📦 Gestión completa de productos (CRUD)
- 👥 Gestión de afiliados
- 🛒 Gestión de pedidos
- 💰 Control de comisiones
- ⚙️ Configuración de porcentajes por afiliado

## 📋 Requisitos

- Python 3.8+
- PostgreSQL
- pip

## 🔧 Instalación

### 1. Clonar el repositorio o descargar los archivos

### 2. Crear entorno virtual

```bash
python -m venv venv
```

### 3. Activar entorno virtual

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 5. Configurar variables de entorno

El archivo `.env` ya está configurado con la base de datos PostgreSQL en Render:

```env
DATABASE_URL=postgresql://...
SECRET_KEY=...
```

⚠️ **IMPORTANTE:** Cambia el número de WhatsApp en [config.py:27](config.py#L27)

### 6. Inicializar la base de datos

```bash
python init_db.py
```

Este script:
- Crea todas las tablas necesarias
- Crea un usuario administrador por defecto
- Crea productos de ejemplo
- Crea un afiliado de ejemplo

**Credenciales por defecto:**

Admin:
- Usuario: `admin`
- Contraseña: `admin123`

Afiliado de ejemplo:
- Email: `juan@email.com`
- Contraseña: `afiliado123`
- Código: `AFI001`

### 7. Ejecutar la aplicación

```bash
python app.py
```

La aplicación estará disponible en: `http://localhost:5000`

## 📁 Estructura del Proyecto

```
SHOP FUSION NUEVO/
├── app.py                  # Aplicación principal
├── config.py               # Configuración
├── models.py               # Modelos de base de datos
├── init_db.py              # Script de inicialización
├── requirements.txt        # Dependencias
├── .env                    # Variables de entorno
├── routes/                 # Rutas de la aplicación
│   ├── __init__.py
│   ├── auth.py            # Autenticación
│   ├── admin.py           # Panel admin
│   ├── afiliado.py        # Panel afiliado
│   └── tienda.py          # Tienda pública
├── templates/             # Templates HTML
│   ├── base.html
│   ├── auth/              # Login
│   ├── admin/             # Admin panel
│   ├── afiliado/          # Afiliado panel
│   └── tienda/            # Tienda pública
└── static/                # Archivos estáticos
    ├── css/
    │   └── style.css
    ├── js/
    └── uploads/           # Imágenes de productos
```

## 🗄️ Base de Datos

### Tablas

1. **admins** - Administradores del sistema
2. **afiliados** - Afiliados con código único
3. **productos** - Catálogo de productos
4. **pedidos** - Pedidos de clientes
5. **comisiones** - Comisiones generadas

### Diagrama de Relaciones

```
afiliados (1) ──── (N) pedidos
afiliados (1) ──── (N) comisiones
pedidos (1) ──── (N) comisiones
```

## 🔐 Acceso al Sistema

### Rutas Públicas
- `/` - Tienda principal
- `/producto/<id>` - Detalle de producto
- `/carrito` - Carrito de compras
- `/checkout` - Finalizar compra
- `/unete` - Únete como afiliado

### Rutas de Autenticación
- `/auth/admin/login` - Login administrador
- `/auth/afiliado/login` - Login afiliado
- `/auth/logout` - Cerrar sesión

### Panel Admin
- `/admin/dashboard` - Dashboard
- `/admin/productos` - Gestión de productos
- `/admin/pedidos` - Gestión de pedidos
- `/admin/afiliados` - Gestión de afiliados
- `/admin/comisiones` - Gestión de comisiones

### Panel Afiliado
- `/afiliado/dashboard` - Dashboard
- `/afiliado/productos` - Productos para compartir
- `/afiliado/comisiones` - Mis comisiones
- `/afiliado/pedidos` - Pedidos generados

## 💡 Flujo de Funcionamiento

### 1. Afiliado comparte link
```
https://tienda.com/producto/5?ref=AFI001
```

### 2. Cliente navega y compra
- El código `AFI001` se guarda en sesión
- Cliente agrega productos al carrito
- Realiza checkout con sus datos
- Sistema abre WhatsApp con mensaje pre-llenado

### 3. Admin valida pago
- Recibe confirmación por WhatsApp
- Marca pedido como "Pagado"
- Sistema calcula comisión automáticamente

### 4. Afiliado ve su comisión
- Ingresa a su panel
- Ve comisión generada
- Espera que admin la marque como "Pagada"

## 💰 Cálculo de Comisiones

### Fórmula
```
Margen = Precio Final - Precio Proveedor
Comisión = Margen × (Porcentaje Afiliado / 100)
```

### Ejemplo
```
Producto:
- Precio Final: $50
- Precio Proveedor: $25
- Margen: $25

Afiliado con 80%:
- Comisión: $25 × 0.80 = $20
```

### Con Precio de Oferta
```
Producto:
- Precio Final: $50
- Precio Proveedor: $25
- Precio Oferta: $40
- Margen: $40 - $25 = $15

Afiliado con 80%:
- Comisión: $15 × 0.80 = $12
```

## ⚙️ Configuración

### Cambiar número de WhatsApp

Edita [config.py:27](config.py#L27):

```python
WHATSAPP_NUMBER = '593999999999'  # Tu número aquí
```

### Cambiar porcentaje de comisión por afiliado

Desde el panel admin:
1. Ve a "Afiliados"
2. Edita el afiliado
3. Cambia "Porcentaje de comisión"
4. Guarda cambios

### Agregar productos

Desde el panel admin:
1. Ve a "Productos"
2. Clic en "+ Nuevo Producto"
3. Completa el formulario
4. Sube imagen (opcional)
5. Guarda

## 🔒 Seguridad

- ✅ Contraseñas encriptadas con bcrypt
- ✅ Sesiones seguras con Flask-Login
- ✅ Validación de archivos subidos
- ✅ CSRF protection (incluido en Flask)
- ✅ SQL Injection protection (SQLAlchemy ORM)

⚠️ **Recomendaciones para Producción:**
1. Cambiar `SECRET_KEY` en `.env`
2. Cambiar contraseña del admin por defecto
3. Activar HTTPS (cambiar `SESSION_COOKIE_SECURE = True`)
4. Configurar backups automáticos de la base de datos

## 🐛 Troubleshooting

### Error de conexión a base de datos
Verifica que el `DATABASE_URL` en `.env` sea correcto.

### Las imágenes no se muestran
Verifica que la carpeta `static/uploads/` tenga permisos de escritura.

### Error al importar módulos
Asegúrate de tener el entorno virtual activado y las dependencias instaladas.

## 📝 Licencia

Este proyecto es de código abierto y está disponible para uso personal y comercial.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📧 Contacto

Para soporte o consultas, contacta al administrador del sistema.

---

**Versión:** 1.0
**Fecha:** 17 de Enero de 2026
**Estado:** Producción Ready ✅
