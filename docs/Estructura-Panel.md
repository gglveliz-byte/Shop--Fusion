# Documento de Investigación: Paneles en e-commerce

> **Historial de Revisiones (Última actualización)**
> * **Fase 6 Completada:** Refactorización, seguridad de red y validación de endpoints aplicadas exitosamente. El documento refleja el estado actual de la plataforma modularizada.

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
- **Módulo de Contabilidad**: [NUEVO]
  - Visualización del Balance General (Ingresos, Gastos, Utilidad).
  - Libro Diario (Historial de transacciones de PayPal, comisiones pagadas, etc.).
- **Gestión de Marca (White-Label) y Configuración**: [ACTUALIZADO]
  - Configuración de identidad: Nombre de tienda, Logo y Favicon.
  - Personalización visual: Control de colores (Primario, Secundario, Acento).
  - Contacto directo y Textos: WhatsApp de soporte, Copyright, Pie de Página.
  - SEO y Finanzas: Descripción SEO y Tasa de IVA (Impuestos) dinámica.
- **Gestión de Atención al Cliente (Tickets y FAQ)**: [NUEVO]
  - Sistema de Tickets de Soporte categorizados por prioridad y estado (asignación de agentes).
  - Base de Conocimiento Institucional (FAQ) que alimenta al Asistente de IA (Qwen) mediante Embeddings Vectoriales.

### Casos de Uso Principales
1. **Subir productos**: Administrador crea nuevos productos con imágenes y precios
2. **Configurar promociones**: Establecer precios de oferta en productos
3. **Personalizar Marca**: Ajustar la identidad visual del sitio (Colores y Logos)
4. **Revisar reportes**: Consultar métricas de ventas y rendimiento de afiliados
5. **Gestionar pagos**: Procesar pagos de comisiones a afiliados
6. **Control de calidad**: Validar pedidos antes de procesarlos

---

## Panel Afiliados

### Descripción
El panel de afiliados está diseñado para vendedores independientes que promocionan productos de Marca Blanca. Permite generar enlaces personalizados, calcular comisiones y gestionar pedidos generados por sus ventas.

### Funciones y Opciones Disponibles
- **Dashboard Personal**: Estadísticas de comisiones (pendientes, generadas, pagadas, total ganado)
- **Catálogo de Productos**:
  - Ver todos los productos activos con cálculo automático de comisión
  - Generar enlaces personalizados para cada producto
  - **Herramientas de Marketing Avanzadas**: [NUEVO]
    - Botón "Estado": Compartir directamente en WhatsApp Status / Instagram Stories.
    - Botón "Descargar": Descarga automática de imagen del producto + texto publicitario optimizado.
    - Botón "Copiar": Copiado rápido de descripción y enlace al portapapeles.
- **Gestión de Pedidos**:
  - Ver pedidos generados por sus enlaces
  - Marcar pedidos como pagados (cuando recibe el pago del cliente)
  - Validar pedidos para que aparezcan en el panel del admin
  - Cancelar pedidos si es necesario
- **Historial de Comisiones**:
  - Ver todas las comisiones generadas y pagadas
  - Filtrar por estado (pendiente, generada, pagada)
- **CRM y Pipeline de Ventas**: [NUEVO]
  - Gestión de Oportunidades con clientes potenciales (Prospecto, Negociación, etc.).
  - Sistema de Agenda y Recordatorios para realizar seguimiento oportuno.
- **Perfil Personal**:
  - Editar nombre, WhatsApp y contraseña
  - Ver enlace de tienda personal

### Casos de Uso Principales
1. **Compartir en Estados**: Usar el botón de compartir para publicar en Historias de Instagram/WhatsApp
2. **Descargar material**: Obtener imágenes y textos para publicidad externa
3. **Consultar ganancias**: Revisar comisiones pendientes y totales ganados
4. **Gestionar ventas**: Marcar pedidos como pagados y validarlos
5. **Actualizar perfil**: Mantener información de contacto actualizada

---

## Panel Cliente

### Descripción
La tienda pública es la interfaz principal para clientes finales. Incluye navegación de productos, carrito de compras, proceso de checkout y seguimiento de pedidos. La estética del sitio se adapta dinámicamente a la configuración de Marca Blanca del administrador.

### Funciones y Opciones Disponibles
- **Página Principal**: Catálogo de productos con filtros por categoría.
- **Asistente de IA (Qwen)**: [NUEVO] Chatbot inteligente para soporte y consultas de productos.
- **Detalle de Producto**: Información completa, imágenes y opciones de compra.
- **Carrito de Compras**:
  - Agregar productos con cantidades.
  - Actualizar cantidades y eliminar productos.
  - Calcular totales automáticamente con impuestos/comisiones.
- **Proceso de Checkout**:
  - Formulario de datos personales (**Cifrados automáticamente** vía Fase 3 Hardening).
  - Integración con PayPal para pagos en línea.
  - Opción de pago contra entrega coordinado vía WhatsApp.
- **Confirmación de Pedido**: Resumen del pedido con enlace directo a WhatsApp.

### Casos de Uso Principales
1. **Agregar productos al carrito**: Navegar catálogo y seleccionar productos.
2. **Realizar pago seguro**: Completar checkout con datos protegidos por cifrado.
3. **Revisar estado del pedido**: Ver confirmación y detalles del pedido.
4. **Comprar con afiliado**: Acceder a tienda personalizada de vendedor
5. **Interactuar con IA**: Consultar dudas sobre productos al asistente Qwen.

---

## Flujo del Proceso de Compra del Cliente

### Paso a Paso

1. **Acceso a la Tienda**
   - Cliente ingresa a la URL principal o a URL de afiliado.
   - El sistema carga los colores y logo configurados por el administrador (White-Label).

2. **Navegación y Selección**
   - Explora productos por categorías y ve detalles individuales.
   - Agrega productos al carrito con las cantidades deseadas.

3. **Gestión del Carrito**
   - Revisa productos agregados, modifica cantidades o elimina ítems.
   - Ve el total calculado automáticamente.

4. **Proceso de Checkout**
   - Ingresa datos personales (Nombre, Teléfono, Dirección). 
   - **Nota de Seguridad**: Estos datos se cifran con Fernet (AES-256) antes de tocar la base de datos.
   - Elige método de pago (WhatsApp o PayPal).

5. **Confirmación del Pedido**
   - Recibe confirmación con ID de pedido y resumen.
   - Enlace directo a WhatsApp para coordinar la entrega con el vendedor.
   - Para pagos PayPal: Confirmación automática de pago completado y validación inmediata.

6. **Seguimiento (Futuro)**
   - Sistema preparado para seguimiento de estado del pedido en tiempo real.
   - Notificaciones automáticas por WhatsApp sobre cambios de estado (Enviado, Entregado).

### Estados del Pedido
- **Pendiente**: Pedido creado, esperando pago o validación de comprobante.
- **Pagado**: Pago confirmado automáticamente (PayPal) o manualmente (Vendedor/Admin).
- **Validado**: Vendedor confirmó el pago y el administrador ha recibido la notificación para despacho.
- **Cancelado**: Pedido anulado por el cliente, vendedor o administrador.

### Integraciones Técnicas y Seguridad
- **PayPal**: Procesamiento automático de pagos con comisión del 5.4% integrada en el checkout.
- **WhatsApp**: Comunicación directa y automatizada para confirmación de pedidos y soporte.
- **Marca Blanca (White-Label)**: Motor de plantillas dinámico que adapta colores y logos según la configuración del administrador.
- **Sistema de Facturación**: [NUEVO] Generación automática de facturas (PDF o vista web) con desglose de impuestos (IVA dinámico).
- **Protección PII y Sesiones Seguras**: Blindaje de datos sensibles mediante cifrado Fernet (AES-256) y autenticación segura con Hashes.
- **Asistente de IA (Qwen)**: Integración vía API para soporte inteligente (con restricciones CORS para evitar abusos).
- **Redis y Rate Limiting**: Protección contra ataques de fuerza bruta usando almacenamiento en memoria persistente para contadores de login.
- **Base de Datos y Transacciones**: PostgreSQL gestionado con Flask-Migrate y bloqueos transaccionales pesimistas (Race Conditions mitigadas).

---

## Conclusiones

El sistema Shop Fusion ha evolucionado hacia una plataforma de **Marca Blanca Blindada**, permitiendo:
- **Administrador**: Personalización total de la identidad visual y control de seguridad.
- **Afiliados**: Herramientas de marketing directo para redes sociales.
- **Clientes**: Una experiencia de compra segura y personalizada.



## Comparación de Paneles

| Panel         | Tipo de Usuario           | Función Principal | Acceso | Acciones Clave |
|---------------|---------------------------|------------------|--------|----------------|
| Administrador | Administrador del sistema | Gestión completa del e-commerce | Privado | Crear productos, gestionar pedidos, pagar comisiones |
| Afiliado      | Vendedor independiente    | Promoción y venta de productos | Privado | Compartir enlaces, validar pedidos, ver ganancias |
| Cliente       | Usuario final             | Compra de productos | Público | Navegar, comprar, pagar |

## Diagrama de Flujo del Cliente

Inicio  
↓  
Accede a tienda (normal o afiliado)  
↓  
Explora productos  
↓  
Agrega al carrito  
↓  
Revisa carrito  
↓  
Ingresa datos  
↓  
Selecciona método de pago  
↓  
Confirma pedido  
↓  
Fin

La arquitectura soporta escalabilidad con separación clara de responsabilidades y flujos optimizados para conversión de ventas.