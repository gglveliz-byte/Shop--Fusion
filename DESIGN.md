# 🎨 Sistema de Diseño (Design System) - Shop Fusion

Este documento establece las reglas visuales estrictas para el frontend de Shop Fusion. Su objetivo principal es mantener una apariencia **humana, profesional y limpia**, evitando estilos que parezcan generados por IA (como glassmorphism, colores neón, gradientes excesivos o bordes muy redondeados).

---

## 1. Reglas Generales y Filosofía
- **Tema:** Exclusivamente Claro (Light Theme).
- **Estilo:** "Flat" o diseño plano moderno. Limpio y corporativo.
- **Bordes:** Rectos. Está estrictamente prohibido el uso de bordes muy redondeados (`12px`, `16px`, `20px` o pill-shapes).
- **Sombras:** Sutiles y realistas.
- **Transparencias:** Se prohíbe el uso de `backdrop-filter` (efecto cristal/glassmorphism).

---

## 2. Tipografía
- **Fuente Principal:** `Inter` (importada de Google Fonts).
- **Fallbacks:** `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Roboto`, `sans-serif`.
- **Pesos permitidos:** 
  - Regular (400) - Para cuerpos de texto.
  - Medium (500) - Para botones y enlaces.
  - Bold (700) - Para subtítulos importantes.
  - Extra Bold (800) - Para títulos principales (`h1`, `h2`).

---

## 3. Paleta de Colores (Tokens)

Los colores deben usarse siempre mediante variables CSS para mantener la consistencia.

### Colores Principales (Sobrios y Corporativos)
*No usar colores vibrantes o "neón".*
- `--primary-color`: `#2563eb` (Azul corporativo, confiable)
- `--primary-dark`: `#1d4ed8` (Azul oscuro para hovers)
- `--primary-light`: `#dbeafe` (Azul muy claro para fondos sutiles)
- `--secondary-color`: `#059669` (Verde esmeralda sobrio)
- `--secondary-dark`: `#047857` (Verde esmeralda oscuro para hovers)

### Colores Neutros (Fondos y Textos)
*Evitar el negro puro (`#000`) y el blanco puro (`#fff`) para textos extensos.*
- `--bg-page`: `#f8f9fa` (Gris súper claro, fondo base de la web)
- `--bg-surface`: `#ffffff` (Blanco puro, fondo de tarjetas/paneles)
- `--text-primary`: `#1f2937` (Gris muy oscuro, casi negro, para títulos y textos principales)
- `--text-secondary`: `#4b5563` (Gris medio, para descripciones)
- `--text-muted`: `#6b7280` (Gris claro, para placeholders o textos secundarios)
- `--border-color`: `#d1d5db` (Gris claro para dividir secciones)

### Colores de Estado (Alertas / Badges)
- `--danger-color`: `#dc2626` (Rojo - Error/Eliminar)
- `--warning-color`: `#d97706` (Naranja - Precaución/Pendiente)
- `--info-color`: `#0284c7` (Azul claro - Información/Generada)

---

## 4. Efectos y Formas

### Bordes (Radios)
- `--radius`: `2px` (Botones, inputs, tarjetas estándar)
- `--radius-sm`: `1px` (Badges o elementos muy pequeños)
- *Nota: Nada superior a `4px`.*

### Sombras (Box Shadow)
- `--shadow-sm`: `0 1px 2px rgba(0, 0, 0, 0.04)` (Elementos interactivos pequeños)
- `--shadow`: `0 1px 3px rgba(0, 0, 0, 0.08)` (Tarjetas estándar)
- `--shadow-md`: `0 2px 6px rgba(0, 0, 0, 0.08)` (Modales o tarjetas destacadas)

### Transiciones (Animaciones)
- `--transition`: `all 0.15s ease`
- *Nota: Evitar `transform: scale()` o `translateY()` exagerados. Las interacciones de hover deben limitarse a cambios de color de fondo, color de texto o variaciones mínimas de opacidad/sombra.*

---

## 5. Clases Utilitarias (Naming Convention)

Para mantener el CSS limpio, usar estas clases base en el HTML:

- **Estructura:**
  - `.container`: Contenedor principal (`max-width: 1280px`).
  - `.grid`: Contenedores con display grid.
  - `.flex`: Contenedores con display flex.

- **Componentes:**
  - `.card`: Tarjetas de contenido (Usa `--bg-surface`, `--shadow`, `--radius`, y `border`).
  - `.btn`: Botón base.
    - Variantes: `.btn-primary`, `.btn-secondary`, `.btn-danger`, etc.
  - `.badge`: Etiquetas pequeñas para estados.
    - Variantes: `.badge-success`, `.badge-warning`, etc.
  - `.form-control`: Inputs, selects y textareas.

---
*Este documento reemplaza cualquier diseño anterior basado en Glassmorphism o gradientes excesivos.*
