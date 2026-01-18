# -*- coding: utf-8 -*-
"""
Script para agregar laptops del catálogo a la base de datos
Con precios optimizados y descuentos variados
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from app import create_app, db
from models import Producto
from decimal import Decimal

app = create_app()

# Catálogo de Laptops con precios de proveedor y precios de venta optimizados
laptops = [
    # ============== HP ==============
    {
        "nombre": "HP 15-FC0256LA Ryzen 5",
        "descripcion": """💻 **HP 15-FC0256LA** - Potencia AMD para trabajo y estudio

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: AMD Ryzen 5 7530U (6 núcleos, hasta 4.5GHz)
• 💾 RAM: 16GB DDR5 (ultra rápida)
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: AMD Radeon Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ
• 🔋 Batería de larga duración

✅ **Ideal para:** Trabajo de oficina, estudiantes universitarios, multitarea, programación

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 540,
        "precio_final": 649,
        "precio_oferta": 619,  # Descuento de $30
    },
    {
        "nombre": "HP 15-EFD0053LA Core i5 12va",
        "descripcion": """💻 **HP 15-EFD0053LA** - Intel Core i5 de 12va Generación

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: Intel Core i5-1235U 12va Gen (10 núcleos)
• 💾 RAM: 16GB DDR4
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: Intel Iris Xe Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ

✅ **Ideal para:** Profesionales, diseño básico, office avanzado, videoconferencias

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 570,
        "precio_final": 689,
        "precio_oferta": None,  # Sin descuento
    },
    {
        "nombre": "HP 250 G10 Core i5 13va",
        "descripcion": """💻 **HP 250 G10** - Línea Empresarial Intel 13va Gen

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: Intel Core i5-1334U 13va Gen
• 💾 RAM: 16GB DDR4
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: Intel UHD Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ
• 🏢 Diseño profesional empresarial

✅ **Ideal para:** Empresas, oficinas, uso corporativo, presentaciones

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 495,
        "precio_final": 599,
        "precio_oferta": 569,  # Descuento de $30
    },
    {
        "nombre": "HP 15-FD0027LA Core i7 13va",
        "descripcion": """💻 **HP 15-FD0027LA** - Intel Core i7 de 13va Generación

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: Intel Core i7-1355U 13va Gen (10 núcleos)
• 💾 RAM: 16GB DDR4
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: Intel Iris Xe Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ

✅ **Ideal para:** Profesionales exigentes, edición de video, desarrollo de software

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 665,
        "precio_final": 799,
        "precio_oferta": 759,  # Descuento de $40
    },
    {
        "nombre": "HP 255 G10 Ryzen 7",
        "descripcion": """💻 **HP 255 G10** - AMD Ryzen 7 Empresarial

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: AMD Ryzen 7 7730U (8 núcleos)
• 💾 RAM: 16GB DDR4
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: AMD Radeon Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ

✅ **Ideal para:** Trabajo pesado, multitarea extrema, virtualización

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 525,
        "precio_final": 639,
        "precio_oferta": None,  # Sin descuento
    },
    {
        "nombre": "HP 255 G10 Ryzen 7 32GB/1TB",
        "descripcion": """💻 **HP 255 G10 MÁXIMA POTENCIA** - Ryzen 7 + 32GB RAM

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: AMD Ryzen 7 7730U (8 núcleos)
• 💾 RAM: 32GB DDR4 (¡MÁXIMA CAPACIDAD!)
• 💿 Almacenamiento: 1TB SSD M.2 NVMe
• 🎮 Gráficos: AMD Radeon Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ

✅ **Ideal para:** Programadores, diseñadores, máquinas virtuales, edición profesional

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 795,
        "precio_final": 949,
        "precio_oferta": 899,  # Descuento de $50
    },
    {
        "nombre": "HP 15-FB3019LA Gaming RTX 3050",
        "descripcion": """🎮 **HP 15-FB3019LA GAMING** - RTX 3050 para Gamers

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: AMD Ryzen 7 7445HS (6 núcleos, alto rendimiento)
• 💾 RAM: 16GB DDR5 (velocidad gaming)
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: NVIDIA RTX 3050 6GB GDDR6
• 📺 Pantalla: 15.6" Full HD 144Hz (fluido para juegos)
• ⌨️ Teclado en Español retroiluminado
• 🌀 Sistema de refrigeración gaming

✅ **Ideal para:** Gaming AAA, streaming, edición de video, diseño 3D

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 995,
        "precio_final": 1195,
        "precio_oferta": 1149,  # Descuento de $46
    },
    {
        "nombre": "HP 15-FB3022LA Gaming RTX 4050",
        "descripcion": """🎮 **HP 15-FB3022LA GAMING PRO** - RTX 4050 Última Generación

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: AMD Ryzen 7 7445HS (6 núcleos, alto rendimiento)
• 💾 RAM: 16GB DDR5 (velocidad gaming)
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: NVIDIA RTX 4050 6GB GDDR6 (¡ÚLTIMA GEN!)
• 📺 Pantalla: 15.6" Full HD 144Hz IPS
• ⌨️ Teclado en Español retroiluminado RGB
• 🌀 Sistema de refrigeración avanzado

✅ **Ideal para:** Gaming 4K, renderizado, inteligencia artificial, diseño profesional

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 1125,
        "precio_final": 1349,
        "precio_oferta": 1279,  # Descuento de $70
    },

    # ============== LENOVO ==============
    {
        "nombre": "Lenovo V15 G2 IJL Celeron",
        "descripcion": """💻 **Lenovo V15 G2 IJL** - Laptop Económica Básica

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: Intel Celeron N4500 (eficiente)
• 💾 RAM: 8GB DDR4
• 💿 Almacenamiento: 256GB SSD M.2
• 🎮 Gráficos: Intel UHD Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ
• 🔋 Excelente duración de batería

✅ **Ideal para:** Estudiantes, navegación web, Office básico, tareas escolares

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 299,
        "precio_final": 379,
        "precio_oferta": 349,  # Descuento de $30
    },
    {
        "nombre": "Lenovo IdeaPad Slim 3 Ryzen 3",
        "descripcion": """💻 **Lenovo IdeaPad Slim 3 15AMN8** - AMD Ryzen 3 DDR5

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: AMD Ryzen 3 7320U (4 núcleos)
• 💾 RAM: 8GB DDR5 (nueva generación)
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: AMD Radeon Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ
• 🪶 Diseño delgado y ligero

✅ **Ideal para:** Estudiantes universitarios, trabajo remoto, portabilidad

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 375,
        "precio_final": 459,
        "precio_oferta": None,  # Sin descuento
    },
    {
        "nombre": "Lenovo V15 G4 IRU Core i3 13va",
        "descripcion": """💻 **Lenovo V15 G4 IRU** - Intel Core i3 de 13va Gen

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: Intel Core i3-1315U 13va Gen (6 núcleos)
• 💾 RAM: 8GB DDR4
• 💿 Almacenamiento: 256GB SSD M.2
• 🎮 Gráficos: Intel UHD Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ

✅ **Ideal para:** Oficina, tareas diarias, navegación, documentos

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 375,
        "precio_final": 465,
        "precio_oferta": 439,  # Descuento de $26
    },
    {
        "nombre": "Lenovo IdeaPad Slim 3 Ryzen 5 DDR5",
        "descripcion": """💻 **Lenovo IdeaPad Slim 3 15AMN8** - Ryzen 5 con DDR5

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: AMD Ryzen 5 7530U (6 núcleos)
• 💾 RAM: 16GB DDR5 (velocidad superior)
• 💿 Almacenamiento: 256GB SSD M.2 NVMe
• 🎮 Gráficos: AMD Radeon Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ
• 🪶 Ultra delgada

✅ **Ideal para:** Profesionales móviles, trabajo híbrido, productividad

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 395,
        "precio_final": 489,
        "precio_oferta": None,  # Sin descuento
    },
    {
        "nombre": "Lenovo IdeaPad Slim 3 Core i3-N305",
        "descripcion": """💻 **Lenovo IdeaPad Slim 3 15IAH8** - Intel N305 Eficiente

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: Intel Core i3-N305 (8 núcleos eficientes)
• 💾 RAM: 8GB DDR5
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: Intel UHD Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ
• 🔋 Batería de larga duración

✅ **Ideal para:** Estudiantes, trabajo ligero, navegación, streaming

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 495,
        "precio_final": 599,
        "precio_oferta": 559,  # Descuento de $40
    },
    {
        "nombre": "Lenovo IdeaPad Slim 3 Core i5 12va",
        "descripcion": """💻 **Lenovo IdeaPad Slim 3 15IAH8** - Core i5 12va Gen

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: Intel Core i5-1245H 12va Gen (12 núcleos)
• 💾 RAM: 8GB DDR4
• 💿 Almacenamiento: 256GB SSD M.2
• 🎮 Gráficos: Intel Iris Xe
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ

✅ **Ideal para:** Trabajo intensivo, multitarea, desarrollo básico

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 595,
        "precio_final": 719,
        "precio_oferta": 679,  # Descuento de $40
    },
    {
        "nombre": "Lenovo IdeaPad Slim 3 Core i7 13va",
        "descripcion": """💻 **Lenovo IdeaPad Slim 3 15IAH8** - Core i7 13va Gen

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: Intel Core i7-13620H 13va Gen (10 núcleos)
• 💾 RAM: 16GB DDR5
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: Intel Iris Xe
• 📺 Pantalla: 15.3" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ
• 🪶 Diseño premium ultradelgado

✅ **Ideal para:** Profesionales, edición, programación avanzada

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 659,
        "precio_final": 799,
        "precio_oferta": None,  # Sin descuento
    },
    {
        "nombre": "Lenovo IdeaPad Slim 3 Ryzen 7 16GB",
        "descripcion": """💻 **Lenovo IdeaPad Slim 3 15ABR8** - Ryzen 7 Potente

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: AMD Ryzen 7 7730U (8 núcleos)
• 💾 RAM: 16GB DDR4
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: AMD Radeon Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ

✅ **Ideal para:** Multitarea extrema, máquinas virtuales, trabajo pesado

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 595,
        "precio_final": 719,
        "precio_oferta": 689,  # Descuento de $30
    },
    {
        "nombre": "Lenovo LOQ 15IRX9 Gaming RTX 3050",
        "descripcion": """🎮 **Lenovo LOQ 15IRX9 GAMING** - RTX 3050 para Gamers

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: Intel Core i7-13650HX 13va Gen (14 núcleos)
• 💾 RAM: 12GB DDR5
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: NVIDIA RTX 3050 6GB GDDR6
• 📺 Pantalla: 15.6" Full HD 144Hz
• ⌨️ Teclado en Español retroiluminado
• 🌀 Refrigeración gaming avanzada

✅ **Ideal para:** Gaming competitivo, streaming, edición de video

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 1275,
        "precio_final": 1499,
        "precio_oferta": 1429,  # Descuento de $70
    },
    {
        "nombre": "Lenovo LOQ 15IRX9 Gaming RTX 3050 44GB",
        "descripcion": """🎮 **Lenovo LOQ 15IRX9 GAMING MÁXIMO** - 44GB RAM + 1TB

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: Intel Core i7-13650HX 13va Gen (14 núcleos)
• 💾 RAM: 44GB DDR5 (¡CONFIGURACIÓN EXTREMA!)
• 💿 Almacenamiento: 1TB SSD M.2 NVMe
• 🎮 Gráficos: NVIDIA RTX 3050 6GB GDDR6
• 📺 Pantalla: 15.6" Full HD 144Hz
• ⌨️ Teclado en Español RGB
• 🌀 Sistema de refrigeración premium

✅ **Ideal para:** Streaming profesional, desarrollo de juegos, workstation portátil

📦 **Incluye:** Cargador original + Garantía del fabricante""",
        "precio_proveedor": 1435,
        "precio_final": 1699,
        "precio_oferta": 1599,  # Descuento de $100
    },

    # ============== DELL ==============
    {
        "nombre": "Dell Inspiron 3530 Core i5 13va",
        "descripcion": """💻 **Dell Inspiron 3530** - Core i5 Confiabilidad Dell

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: Intel Core i5-1334U 13va Gen
• 💾 RAM: 16GB DDR4
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: Intel UHD Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ
• 🏢 Calidad empresarial Dell

✅ **Ideal para:** Empresas, profesionales, trabajo remoto confiable

📦 **Incluye:** Cargador original + Garantía Dell""",
        "precio_proveedor": 535,
        "precio_final": 649,
        "precio_oferta": None,  # Sin descuento
    },
    {
        "nombre": "Dell Inspiron 3530 Core i5 32GB/1TB",
        "descripcion": """💻 **Dell Inspiron 3530 MÁXIMA** - 32GB RAM + 1TB SSD

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: Intel Core i5-1334U 13va Gen
• 💾 RAM: 32GB DDR4 (máxima capacidad)
• 💿 Almacenamiento: 1TB SSD M.2 NVMe
• 🎮 Gráficos: Intel UHD Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ

✅ **Ideal para:** Virtualización, bases de datos, desarrollo profesional

📦 **Incluye:** Cargador original + Garantía Dell""",
        "precio_proveedor": 765,
        "precio_final": 919,
        "precio_oferta": 869,  # Descuento de $50
    },
    {
        "nombre": "Dell Inspiron Core i7 12va 14 Pulg",
        "descripcion": """💻 **Dell Inspiron 14"** - Core i7 Compacta Premium

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: Intel Core i7-1255U 12va Gen (10 núcleos)
• 💾 RAM: 16GB DDR4
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: Intel Iris Xe
• 📺 Pantalla: 14" Full HD (más compacta y portátil)
• ⌨️ Teclado en Español con ñ
• 🪶 Ultra portátil

✅ **Ideal para:** Ejecutivos, viajeros frecuentes, trabajo móvil

📦 **Incluye:** Cargador original + Garantía Dell""",
        "precio_proveedor": 415,
        "precio_final": 519,
        "precio_oferta": 489,  # Descuento de $30
    },

    # ============== ASUS ==============
    {
        "nombre": "ASUS VivoBook E1504FA Ryzen 5",
        "descripcion": """💻 **ASUS VivoBook E1504FA** - Ryzen 5 con Huella Digital

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: AMD Ryzen 5 7520U (4 núcleos)
• 💾 RAM: 16GB DDR5
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: AMD Radeon Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ
• 👆 Lector de huella digital integrado
• 🔒 Seguridad biométrica

✅ **Ideal para:** Seguridad, profesionales, trabajo confidencial

📦 **Incluye:** Cargador original + Garantía ASUS""",
        "precio_proveedor": 560,
        "precio_final": 679,
        "precio_oferta": 639,  # Descuento de $40
    },
    {
        "nombre": "ASUS VivoBook X1502V Core i5 13va",
        "descripcion": """💻 **ASUS VivoBook X1502V** - Core i5 13va con Huella

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: Intel Core i5-13420H 13va Gen (8 núcleos)
• 💾 RAM: 16GB DDR4
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: Intel UHD Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ
• 👆 Lector de huellas
• 🪶 Diseño delgado ASUS

✅ **Ideal para:** Trabajo seguro, oficina, productividad

📦 **Incluye:** Cargador original + Garantía ASUS""",
        "precio_proveedor": 549,
        "precio_final": 669,
        "precio_oferta": None,  # Sin descuento
    },
    {
        "nombre": "ASUS VivoBook M1502Y Ryzen 7 16GB/1TB",
        "descripcion": """💻 **ASUS VivoBook M1502Y** - Ryzen 7 + 1TB Almacenamiento

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: AMD Ryzen 7 5825U (8 núcleos)
• 💾 RAM: 16GB DDR4
• 💿 Almacenamiento: 1TB SSD M.2 NVMe (¡MÁXIMO!)
• 🎮 Gráficos: AMD Radeon Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ

✅ **Ideal para:** Almacenar proyectos, multimedia, diseño

📦 **Incluye:** Cargador original + Garantía ASUS""",
        "precio_proveedor": 595,
        "precio_final": 729,
        "precio_oferta": 689,  # Descuento de $40
    },
    {
        "nombre": "ASUS VivoBook M1502Y Ryzen 7 16GB/512GB",
        "descripcion": """💻 **ASUS VivoBook M1502Y** - Ryzen 7 Equilibrado

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: AMD Ryzen 7 5825U (8 núcleos)
• 💾 RAM: 16GB DDR4
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: AMD Radeon Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ

✅ **Ideal para:** Trabajo diario pesado, multitarea

📦 **Incluye:** Cargador original + Garantía ASUS""",
        "precio_proveedor": 560,
        "precio_final": 679,
        "precio_oferta": None,  # Sin descuento
    },
    {
        "nombre": "ASUS VivoBook M1502Y Ryzen 7 8GB/1TB",
        "descripcion": """💻 **ASUS VivoBook M1502Y** - Ryzen 7 Gran Almacenamiento

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: AMD Ryzen 7 5825U (8 núcleos)
• 💾 RAM: 8GB DDR4
• 💿 Almacenamiento: 1TB SSD M.2 NVMe
• 🎮 Gráficos: AMD Radeon Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ

✅ **Ideal para:** Almacenamiento masivo, archivos multimedia

📦 **Incluye:** Cargador original + Garantía ASUS""",
        "precio_proveedor": 550,
        "precio_final": 669,
        "precio_oferta": 629,  # Descuento de $40
    },
    {
        "nombre": "ASUS VivoBook Ryzen 7 7730U 16GB",
        "descripcion": """💻 **ASUS VivoBook** - Ryzen 7 7730U Nueva Generación

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: AMD Ryzen 7 7730U (8 núcleos, nuevo)
• 💾 RAM: 16GB DDR4
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: AMD Radeon Graphics
• 📺 Pantalla: 15.6" Full HD (1920x1080)
• ⌨️ Teclado en Español con ñ

✅ **Ideal para:** Trabajo intensivo, procesador actualizado

📦 **Incluye:** Cargador original + Garantía ASUS""",
        "precio_proveedor": 645,
        "precio_final": 779,
        "precio_oferta": 749,  # Descuento de $30
    },
    {
        "nombre": "ASUS VivoBook X1605VA Core i9 13va",
        "descripcion": """💻 **ASUS VivoBook X1605VA** - Intel Core i9 PREMIUM

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: Intel Core i9 13va Gen (¡MÁXIMO PODER!)
• 💾 RAM: 16GB DDR4
• 💿 Almacenamiento: 1TB SSD M.2 NVMe
• 🎮 Gráficos: Intel Iris Xe
• 📺 Pantalla: 16" Full HD (más grande)
• ⌨️ Teclado en Español con ñ
• 👆 Lector de huellas
• ⭐ Procesador tope de gama

✅ **Ideal para:** Profesionales exigentes, desarrollo, workstation

📦 **Incluye:** Cargador original + Garantía ASUS""",
        "precio_proveedor": 925,
        "precio_final": 1099,
        "precio_oferta": 1049,  # Descuento de $50
    },
    {
        "nombre": "ASUS VivoBook M3607H Ryzen 9 OLED",
        "descripcion": """💻 **ASUS VivoBook M3607H** - Ryzen 9 + Pantalla OLED

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: AMD Ryzen 9 270 (¡POTENCIA EXTREMA!)
• 💾 RAM: 16GB DDR5
• 💿 Almacenamiento: 1TB SSD M.2 NVMe
• 🎮 Gráficos: AMD Radeon Graphics
• 📺 Pantalla: 16" OLED (colores perfectos, negro absoluto)
• ⌨️ Teclado en Español con ñ
• 🌟 Pantalla OLED premium

✅ **Ideal para:** Diseñadores, editores de video, creativos profesionales

📦 **Incluye:** Cargador original + Garantía ASUS""",
        "precio_proveedor": 899,
        "precio_final": 1079,
        "precio_oferta": None,  # Sin descuento
    },
    {
        "nombre": "ASUS TUF Gaming FX608J RTX 3050",
        "descripcion": """🎮 **ASUS TUF Gaming FX608J** - RTX 3050 Durabilidad Militar

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: AMD Ryzen 7 7445HS (alto rendimiento)
• 💾 RAM: 16GB DDR5
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: NVIDIA RTX 3050 4GB GDDR6
• 📺 Pantalla: 15.6" Full HD 144Hz
• ⌨️ Teclado en Español retroiluminado
• 🛡️ Certificación militar MIL-STD-810H
• 🌀 Refrigeración dual ventilador

✅ **Ideal para:** Gaming resistente, uso intensivo, durabilidad

📦 **Incluye:** Cargador original + Garantía ASUS""",
        "precio_proveedor": 1065,
        "precio_final": 1269,
        "precio_oferta": 1199,  # Descuento de $70
    },
    {
        "nombre": "ASUS TUF Gaming FX608J RTX 4050",
        "descripcion": """🎮 **ASUS TUF Gaming FX608J** - RTX 4050 Última Gen

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: AMD Ryzen 7 7445HS (alto rendimiento)
• 💾 RAM: 16GB DDR5
• 💿 Almacenamiento: 512GB SSD M.2 NVMe
• 🎮 Gráficos: NVIDIA RTX 4050 6GB GDDR6
• 📺 Pantalla: 15.6" Full HD 144Hz IPS
• ⌨️ Teclado en Español RGB
• 🛡️ Certificación militar
• 🌀 Sistema térmico avanzado

✅ **Ideal para:** Gaming AAA, Ray Tracing, DLSS 3

📦 **Incluye:** Cargador original + Garantía ASUS""",
        "precio_proveedor": 1235,
        "precio_final": 1449,
        "precio_oferta": 1379,  # Descuento de $70
    },
    {
        "nombre": "ASUS TUF Gaming RTX 5060 Core i7 14va",
        "descripcion": """🎮 **ASUS TUF Gaming PREMIUM** - RTX 5060 + Core i7 14va

🔥 **Especificaciones Técnicas:**
• 🧠 Procesador: Intel Core i7-14650HX 14va Gen (¡ÚLTIMO!)
• 💾 RAM: 32GB DDR5 (máxima capacidad)
• 💿 Almacenamiento: 1TB SSD M.2 NVMe
• 🎮 Gráficos: NVIDIA RTX 5060 8GB GDDR6 (¡NUEVA GEN!)
• 📺 Pantalla: 16" WUXGA (mayor resolución)
• ⌨️ Teclado mecánico RGB
• 🛡️ Durabilidad militar
• ❄️ Refrigeración líquida

✅ **Ideal para:** Gaming 4K, streaming profesional, desarrollo de juegos

📦 **Incluye:** Cargador original + Garantía ASUS""",
        "precio_proveedor": 1795,
        "precio_final": 2099,
        "precio_oferta": 1999,  # Descuento de $100
    },
]

with app.app_context():
    print("\n" + "="*60)
    print("AGREGANDO LAPTOPS A LA BASE DE DATOS")
    print("="*60 + "\n")

    agregados = 0
    existentes = 0

    for laptop in laptops:
        # Verificar si ya existe
        existe = Producto.query.filter_by(nombre=laptop["nombre"]).first()

        if existe:
            print(f"[EXISTE] {laptop['nombre']}")
            existentes += 1
            continue

        # Crear producto
        producto = Producto(
            nombre=laptop["nombre"],
            descripcion=laptop["descripcion"],
            precio_final=Decimal(str(laptop["precio_final"])),
            precio_proveedor=Decimal(str(laptop["precio_proveedor"])),
            precio_oferta=Decimal(str(laptop["precio_oferta"])) if laptop["precio_oferta"] else None,
            imagen=None,
            imagenes=[],
            activo=True
        )

        db.session.add(producto)

        # Calcular margen
        margen = laptop["precio_final"] - laptop["precio_proveedor"]
        precio_venta = laptop["precio_oferta"] if laptop["precio_oferta"] else laptop["precio_final"]
        descuento = laptop["precio_final"] - laptop["precio_oferta"] if laptop["precio_oferta"] else 0

        print(f"[OK] {laptop['nombre']}")
        print(f"     Proveedor: ${laptop['precio_proveedor']} | Venta: ${precio_venta} | Margen: ${margen} | Descuento: ${descuento}")

        agregados += 1

    db.session.commit()

    print("\n" + "="*60)
    print("RESUMEN:")
    print(f"  - Laptops agregadas: {agregados}")
    print(f"  - Laptops existentes (omitidas): {existentes}")

    # Contar total
    total = Producto.query.count()
    print(f"  - Total productos en catálogo: {total}")
    print("="*60)

    print("\n[OK] Todas las laptops han sido agregadas exitosamente!")
