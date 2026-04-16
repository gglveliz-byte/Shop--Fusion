# Documento de Investigación: Paneles en e-commerce

## Objetivo
Analizar y documentar la estructura y funcionamiento de los paneles de Administrador, Afiliados y Cliente, describiendo sus casos de uso y el flujo de compra desde la perspectiva del cliente.

## Alcance
- Panel Administrador: Gestión de catálogo, usuarios, pedidos y métricas
- Panel Afiliados: Generación de enlaces, cálculo de comisiones y materiales de marketing
- Panel Cliente: Registro, navegación, compra y seguimiento de pedidos

---

## Panel Administrador

### Descripción
El panel de administración es el centro de control principal de Shop Fusion. Permite gestionar todo el catálogo de productos, usuarios afiliados, pedidos y comisiones. Está diseñado para administradores que necesitan una visión completa del negocio.

### Funciones y Opciones Disponibles
- **Dashboard Principal**: Estadísticas generales (productos, pedidos, afiliados, comisiones pendientes)
- **Gestión de Productos**:
  - Crear productos con nombre, descripción, categoría, precios (final, proveedor, oferta)
  - Subir imágenes (principales y adicionales) o usar URLs externas
  - Editar y desactivar productos
- **Gestión de Pedidos**:
  - Ver pedidos validados por vendedores o sin vendedor asignado
  - Marcar pedidos como pagados (solo para pedidos sin vendedor)
  - Cancelar pedidos
  - Ver detalles completos de pedidos
- **Gestión de Afiliados**:
  - Crear afiliados con código único, porcentaje de comisión y WhatsApp
  - Editar información de afiliados
  - Ver estadísticas de ventas y ganancias por afiliado
- **Gestión de Comisiones**:
  - Ver todas las comisiones (generadas, pagadas, pendientes)
  - Marcar comisiones individuales como pagadas
  - Pagar todas las comisiones de un afiliado de una vez

### Casos de Uso Principales
1. **Subir productos**: Administrador crea nuevos productos con imágenes y precios
2. **Configurar promociones**: Establecer precios de oferta en productos
3. **Revisar reportes**: Consultar métricas de ventas y rendimiento de afiliados
4. **Gestionar pagos**: Procesar pagos de comisiones a afiliados
5. **Control de calidad**: Validar pedidos antes de procesarlos

---

## Panel Afiliados

### Descripción
El panel de afiliados está diseñado para vendedores independientes que promocionan productos de Shop Fusion. Permite generar enlaces personalizados, calcular comisiones y gestionar pedidos generados por sus ventas.

### Funciones y Opciones Disponibles
- **Dashboard Personal**: Estadísticas de comisiones (pendientes, generadas, pagadas, total ganado)
- **Catálogo de Productos**:
  - Ver todos los productos activos con cálculo automático de comisión
  - Generar enlaces personalizados para cada producto
  - Filtrar productos por categorías
- **Gestión de Pedidos**:
  - Ver pedidos generados por sus enlaces
  - Marcar pedidos como pagados (cuando recibe el pago del cliente)
  - Validar pedidos para que aparezcan en el panel del admin
  - Cancelar pedidos si es necesario
- **Historial de Comisiones**:
  - Ver todas las comisiones generadas y pagadas
  - Filtrar por estado (pendiente, generada, pagada)
- **Perfil Personal**:
  - Editar nombre, WhatsApp y contraseña
  - Ver enlace de tienda personal

### Casos de Uso Principales
1. **Compartir enlaces**: Generar y compartir enlaces personalizados en redes sociales
2. **Consultar ganancias**: Revisar comisiones pendientes y totales ganados
3. **Descargar recursos**: Acceder a materiales de marketing (logos, banners)
4. **Gestionar ventas**: Marcar pedidos como pagados y validarlos
5. **Actualizar perfil**: Mantener información de contacto actualizada

---

## Panel Cliente

### Descripción
La tienda pública es la interfaz principal para clientes finales. Incluye navegación de productos, carrito de compras, proceso de checkout y seguimiento de pedidos. Soporta tanto la tienda principal como tiendas personalizadas de afiliados.

### Funciones y Opciones Disponibles
- **Página Principal**: Catálogo de productos con filtros por categoría
- **Detalle de Producto**: Información completa, imágenes y opciones de compra
- **Carrito de Compras**:
  - Agregar productos con cantidades
  - Actualizar cantidades
  - Eliminar productos
  - Calcular totales automáticamente
- **Proceso de Checkout**:
  - Formulario de datos personales (nombre, teléfono, dirección)
  - Cálculo automático de totales con comisión PayPal (5.4%)
  - Integración con PayPal para pagos en línea
  - Opción de pago contra entrega vía WhatsApp
- **Confirmación de Pedido**: Resumen del pedido con enlace directo a WhatsApp
- **Página "Únete"**: Información para convertirse en afiliado

### Casos de Uso Principales
1. **Agregar productos al carrito**: Navegar catálogo y seleccionar productos
2. **Realizar pago**: Completar checkout con datos personales
3. **Revisar estado del pedido**: Ver confirmación y detalles del pedido
4. **Comprar con afiliado**: Acceder a tienda personalizada de vendedor

---

## Flujo del Proceso de Compra del Cliente

### Paso a Paso

1. **Acceso a la Tienda**
   - Cliente ingresa a la URL principal (tienda del admin) o a URL de afiliado
   - Si viene por enlace de afiliado, se guarda el código en sesión

2. **Navegación y Selección**
   - Explora productos por categorías
   - Ve detalles de productos individuales
   - Agrega productos al carrito con cantidades deseadas

3. **Gestión del Carrito**
   - Revisa productos agregados
   - Modifica cantidades o elimina productos
   - Ve total calculado automáticamente

4. **Proceso de Checkout**
   - Ingresa datos personales (nombre, teléfono, dirección)
   - Revisa resumen del pedido con totales
   - Elige método de pago:
     - **Pago contra entrega**: Envía pedido por WhatsApp
     - **Pago con PayPal**: Procesa pago en línea con comisión adicional

5. **Confirmación del Pedido**
   - Recibe confirmación con ID de pedido
   - Enlace directo a WhatsApp para coordinar entrega
   - Para pagos PayPal: Confirmación automática de pago completado

6. **Seguimiento (Futuro)**
   - Sistema preparado para seguimiento de estado del pedido
   - Notificaciones por WhatsApp

### Estados del Pedido
- **Pendiente**: Pedido creado, esperando pago
- **Pagado**: Pago confirmado (por vendedor o PayPal)
- **Validado**: Vendedor confirmó pago y admin puede verlo
- **Cancelado**: Pedido cancelado por cliente, vendedor o admin

### Integraciones Técnicas
- **PayPal**: Procesamiento automático de pagos con comisión del 5.4%
- **WhatsApp**: Comunicación directa para pedidos y soporte
- **Sistema de Afiliados**: Códigos únicos para tracking de ventas
- **Base de Datos**: Almacenamiento de pedidos, productos y usuarios

---

## Conclusiones

El sistema Shop Fusion implementa un modelo de e-commerce B2B2C (Business-to-Business-to-Consumer) con:
- **Administrador**: Control total del catálogo y operaciones
- **Afiliados**: Vendedores independientes con comisiones
- **Clientes**: Compradores finales con múltiples opciones de pago

La arquitectura soporta escalabilidad con separación clara de responsabilidades y flujos optimizados para conversión de ventas.