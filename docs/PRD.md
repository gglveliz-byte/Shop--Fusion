# PRD: Shop Fusion - Sistema de E-commerce con Afiliados e IA

## 1. Visión del Producto

### Shop Fusion (Versión Actual)
Shop Fusion es una plataforma de comercio electrónico diseñada para agilizar el ciclo de venta directo. Su núcleo se basa en la simplicidad para el cliente final (compra sin registro y checkout vía WhatsApp) y la potencia para los vendedores mediante un sistema de gestión de afiliados con comisiones automatizadas.

### Objetivo Futuro (Marca Blanca / White-Label)
La visión a largo plazo es transformar Shop Fusion en una solución **SaaS Multi-tenant**. Esto permitirá que terceros (negocios, agencias o emprendedores) puedan desplegar sus propias instancias de la tienda con personalización total de marca, configuración de productos independiente y gestión de sus propios afiliados, todo bajo una infraestructura centralizada y escalable.

---

## 2. Enfoque White-Label

El desarrollo de la plataforma se orientará hacia una arquitectura modular que facilite:
- **Personalización Visual**: Temas dinámicos que permitan cambiar logos, colores, tipografías y estilos de UI para adaptarse a la identidad de cualquier marca.
- **Gestión de Dominios**: Capacidad para que cada tienda opere bajo su propio subdominio o dominio personalizado.
- **Independencia Operativa**: Paneles de administración aislados por cada cliente (inquilino), garantizando la privacidad y seguridad de los datos.

---

## 3. Problema que Resuelve

### Negocios Digitales
Muchos negocios luchan por integrar sistemas de afiliados que sean fáciles de usar para personas no técnicas. Shop Fusion simplifica la generación de links y el seguimiento de ventas.

### E-commerce y Conversión
El abandono del carrito es un problema crítico. Al integrar el checkout por WhatsApp, se reduce la fricción, permitiendo una comunicación directa que aumenta la confianza y las tasas de conversión.

### Automatización de Operaciones
Elimina la carga manual de calcular comisiones sobre márgenes de ganancia (Precio Final - Precio Proveedor), automatizando el flujo desde que el administrador marca un pedido como pagado hasta que el afiliado ve su saldo actualizado.

---

## 4. Propuesta de Valor

### Uso de IA en Procesos Internos
Shop Fusion integra Inteligencia Artificial para optimizar la eficiencia operativa:
- **Generación de Contenido**: Creación automática de descripciones persuasivas para productos y optimización de metadatos SEO.
- **Análisis de Sentimiento**: Procesamiento de mensajes de clientes para priorizar atención urgente.
- **Asistente de Gestión**: IA que sugiere ajustes en los precios o porcentajes de comisión basados en el rendimiento histórico.

### Automatización de Ventas, Atención y Operaciones
- **Ventas**: Flujo automatizado desde el link de referido hasta el mensaje de WhatsApp.
- **Atención**: Respuestas pre-configuradas y chatbots de IA para resolver dudas frecuentes antes de pasar al cierre de venta manual.
- **Operaciones**: Sincronización automática de inventarios y estados de comisiones en tiempo real.

---

## 5. Usuarios Objetivo

- **Empresas**: Marcas que quieren delegar su fuerza de ventas a una red de afiliados sin complicaciones técnicas.
- **Emprendedores**: Personas que buscan vender productos (propios o de terceros) de forma rápida y profesional.
- **Negocios Digitales**: Agencias que necesitan una solución "llave en mano" para ofrecer tiendas en línea a sus clientes bajo un modelo de marca blanca.

---

## 6. Features Principales (MVP)

### Integración con APIs
- **WhatsApp API**: Integración con WhatsApp Business para notificaciones automáticas y flujos de chat avanzados.
- **Pasarelas de Pago**: Conectividad con PayPal (actual), Stripe y otros métodos locales para automatizar la confirmación de transacciones.
- **Logística**: Integración futura con APIs de servicios de mensajería para seguimiento de envíos.

### Automatización con IA
- **Chatbot de Ventas**: Un agente inteligente que guía al usuario en la elección del producto ideal.
- **Categorización Automática**: IA que organiza el catálogo basándose en imágenes o descripciones cortas.

### Panel de Control
- **Dashboard Admin**: Control total de productos, pedidos, gestión masiva de afiliados y reportes detallados de ingresos/egresos.
- **Dashboard Afiliado**: Interfaz intuitiva para ver links de referencia, historial de pedidos generados y visualización de comisiones (Pendientes, Generadas, Pagadas).

---

## 7. Roadmap Inicial

### Fase 1: Base Técnica
- Consolidación de la arquitectura actual (Flask/PostgreSQL).
- Optimización de la base de datos para escalabilidad.
- Refuerzo de la seguridad en sesiones y manejo de datos sensibles.

### Fase 2: Integraciones
- Conexión profunda con WhatsApp Business API para flujos interactivos.
- Expansión de pasarelas de pago (Stripe, Mercado Pago) más allá de PayPal.
- Integración de servicios de analítica avanzada.

### Fase 3: IA Operativa
- Implementación de modelos de lenguaje (LLMs) para atención al cliente automatizada.
- IA para la generación dinámica de descripciones de productos y assets visuales.
- Motor de recomendaciones para clientes basado en comportamiento.

### Fase 4: White-Label
- Migración a una arquitectura multi-tenant real.
- Sistema de personalización dinámica de UI por cada "inquilino".
- Panel maestro de administración para el control de múltiples tiendas.

---

## 8. KPIs (Indicadores Clave de Desempeño)

- **Tiempo de Automatización**: Medición y reducción del tiempo transcurrido desde la confirmación de recepción del pago hasta que la comisión es asignada al afiliado.
- **Conversión de Leads**: Porcentaje de usuarios que inician un chat de WhatsApp y concretan efectivamente la compra.
- **Reducción de Tareas Manuales**: Porcentaje de pedidos y comisiones procesadas totalmente por el sistema sin intervención manual del administrador.