# -*- coding: utf-8 -*-
"""
Script para agregar productos de celulares con fichas técnicas
Ejecutar: python agregar_productos.py
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from app import create_app, db
from models import Producto
from decimal import Decimal

# Crear app
app = create_app()

# Productos con fichas técnicas completas
productos = [
    # ============ SAMSUNG ============
    {
        "nombre": "Samsung Galaxy A07 128GB",
        "descripcion": """📱 **Samsung Galaxy A07 128GB** - Rendimiento y Estilo

✨ **Características Principales:**
• 📲 Pantalla: 6.6" HD+ 90Hz
• 💾 Almacenamiento: 128GB
• 🔋 Batería: 5000mAh de larga duración
• 📸 Cámara Principal: 50MP + 2MP Profundidad
• 🤳 Cámara Frontal: 8MP
• 🧠 Procesador: MediaTek Helio G85
• 🎮 RAM: 4GB/6GB
• 🔒 Seguridad: Sensor de huellas lateral

🎯 **Ideal para:** Uso diario, redes sociales, streaming y fotografía casual

✅ **Incluye:** Cargador + Cable USB + Funda protectora""",
        "precio_proveedor": 118,
        "precio_final": 169,  # Ganancia: $51
        "precio_oferta": 159,  # Oferta: $41 ganancia
        "imagenes": []
    },
    {
        "nombre": "Samsung Galaxy A16 256GB",
        "descripcion": """📱 **Samsung Galaxy A16 256GB** - Potencia y Capacidad

✨ **Características Principales:**
• 📲 Pantalla: 6.7" FHD+ Super AMOLED 90Hz
• 💾 Almacenamiento: 256GB (Expandible hasta 1TB)
• 🔋 Batería: 5000mAh con carga rápida 25W
• 📸 Triple Cámara: 50MP Principal + 5MP Ultra Wide + 2MP Macro
• 🤳 Cámara Frontal: 13MP
• 🧠 Procesador: MediaTek Dimensity 6300
• 🎮 RAM: 8GB
• 🔒 Seguridad: Sensor de huellas en pantalla
• 📶 Conectividad: 5G Ready

🎯 **Ideal para:** Gaming, multitarea, fotografía avanzada

✅ **Incluye:** Cargador rápido + Cable USB-C + Funda + Mica protectora""",
        "precio_proveedor": 155,
        "precio_final": 219,  # Ganancia: $64
        "precio_oferta": 209,  # Oferta: $54 ganancia
        "imagenes": []
    },
    {
        "nombre": "Samsung Galaxy A17 128GB",
        "descripcion": """📱 **Samsung Galaxy A17 128GB** - Elegancia y Rendimiento

✨ **Características Principales:**
• 📲 Pantalla: 6.6" FHD+ Super AMOLED 120Hz
• 💾 Almacenamiento: 128GB
• 🔋 Batería: 5000mAh con carga rápida
• 📸 Triple Cámara: 64MP Principal + 8MP Ultra Wide + 2MP Macro
• 🤳 Cámara Frontal: 16MP con modo retrato
• 🧠 Procesador: Samsung Exynos
• 🎮 RAM: 6GB/8GB
• 🔒 Knox Security + Sensor de huellas en pantalla
• 🌈 Diseño premium con acabado mate

🎯 **Ideal para:** Creadores de contenido, gaming moderado

✅ **Garantía oficial Samsung""",
        "precio_proveedor": 169,
        "precio_final": 239,  # Ganancia: $70
        "precio_oferta": 229,  # Oferta: $60 ganancia
        "imagenes": []
    },

    # ============ XIAOMI / REDMI ============
    {
        "nombre": "Xiaomi Redmi A5 64GB",
        "descripcion": """📱 **Xiaomi Redmi A5 64GB** - Accesible y Confiable

✨ **Características Principales:**
• 📲 Pantalla: 6.52" HD+ IPS
• 💾 Almacenamiento: 64GB (Expandible)
• 🔋 Batería: 5000mAh
• 📸 Cámara Principal: 13MP con IA
• 🤳 Cámara Frontal: 5MP
• 🧠 Procesador: MediaTek Helio
• 🎮 RAM: 3GB
• 🎨 Diseño moderno y ergonómico

🎯 **Ideal para:** Primer smartphone, uso básico

✅ **Relación calidad-precio excepcional""",
        "precio_proveedor": 72,
        "precio_final": 109,  # Ganancia: $37
        "precio_oferta": 99,   # Oferta: $27 ganancia
        "imagenes": []
    },
    {
        "nombre": "Xiaomi Redmi A5 128GB",
        "descripcion": """📱 **Xiaomi Redmi A5 128GB** - Más Espacio, Mejor Experiencia

✨ **Características Principales:**
• 📲 Pantalla: 6.52" HD+ IPS
• 💾 Almacenamiento: 128GB (Expandible hasta 512GB)
• 🔋 Batería: 5000mAh
• 📸 Cámara Principal: 13MP con IA mejorada
• 🤳 Cámara Frontal: 5MP
• 🧠 Procesador: MediaTek Helio G36
• 🎮 RAM: 4GB
• 🎵 Doble altavoz

🎯 **Ideal para:** Multimedia, almacenamiento de fotos y apps

✅ **Sistema MIUI optimizado""",
        "precio_proveedor": 85,
        "precio_final": 129,  # Ganancia: $44
        "precio_oferta": 119,  # Oferta: $34 ganancia
        "imagenes": []
    },
    {
        "nombre": "Xiaomi Redmi 14C 256GB",
        "descripcion": """📱 **Xiaomi Redmi 14C 256GB** - Potencia Asequible

✨ **Características Principales:**
• 📲 Pantalla: 6.74" HD+ 90Hz Dot Drop
• 💾 Almacenamiento: 256GB + 4GB RAM
• 🔋 Batería: 5160mAh con carga rápida 18W
• 📸 Triple Cámara: 50MP Principal + 2MP Macro + IA
• 🤳 Cámara Frontal: 8MP
• 🧠 Procesador: MediaTek Helio G81
• 🎮 GPU Mali-G52
• 🔊 Altavoces duales estéreo

🎯 **Ideal para:** Gaming casual, fotografía, entretenimiento

✅ **MIUI 14 con Android 14""",
        "precio_proveedor": 108,
        "precio_final": 159,  # Ganancia: $51
        "precio_oferta": 149,  # Oferta: $41 ganancia
        "imagenes": []
    },
    {
        "nombre": "Xiaomi Redmi 15 256GB",
        "descripcion": """📱 **Xiaomi Redmi 15 256GB** - Innovación Sin Límites

✨ **Características Principales:**
• 📲 Pantalla: 6.79" FHD+ AMOLED 120Hz
• 💾 Almacenamiento: 256GB + 8GB RAM
• 🔋 Batería: 5500mAh con carga rápida 67W
• 📸 Sistema de Cámara Triple: 108MP Principal + 8MP Ultra Wide + 2MP
• 🤳 Cámara Frontal: 20MP con modo belleza
• 🧠 Procesador: Snapdragon 7 Gen 2
• 🎮 GPU Adreno 725
• 🔒 Sensor de huellas bajo pantalla ultrasónico
• 📶 5G + NFC
• 🌡️ Sistema de enfriamiento líquido

🎯 **Ideal para:** Gaming avanzado, fotografía profesional, creadores de contenido

✅ **Carga completa en 40 minutos | HyperOS basado en Android 14""",
        "precio_proveedor": 160,
        "precio_final": 229,  # Ganancia: $69
        "precio_oferta": 219,  # Oferta: $59 ganancia
        "imagenes": []
    },
    {
        "nombre": "Xiaomi Redmi 15C 256GB (4GB+4GB)",
        "descripcion": """📱 **Xiaomi Redmi 15C 256GB** - RAM Extendida Inteligente

✨ **Características Principales:**
• 📲 Pantalla: 6.74" HD+ 90Hz
• 💾 Almacenamiento: 256GB + 4GB RAM + 4GB Virtual
• 🔋 Batería: 5000mAh
• 📸 Cámara Dual: 50MP Principal + 2MP
• 🤳 Cámara Frontal: 8MP
• 🧠 Procesador: MediaTek Helio G88
• 🎮 8GB RAM Total (4GB Física + 4GB Extendida)
• 🔊 Audio Hi-Res

🎯 **Ideal para:** Multitarea fluida, apps exigentes

✅ **Tecnología de RAM Virtual para mayor rendimiento""",
        "precio_proveedor": 123,
        "precio_final": 179,  # Ganancia: $56
        "precio_oferta": 169,  # Oferta: $46 ganancia
        "imagenes": []
    },

    # ============ TECNO ============
    {
        "nombre": "Tecno Go 2 128GB",
        "descripcion": """📱 **Tecno Go 2 128GB** - Económico y Funcional

✨ **Características Principales:**
• 📲 Pantalla: 6.6" HD+ IPS
• 💾 Almacenamiento: 128GB (Expandible)
• 🔋 Batería: 5000mAh
• 📸 Cámara Dual: 13MP + IA
• 🤳 Cámara Frontal: 5MP
• 🧠 Procesador: Unisoc
• 🎮 RAM: 3GB
• 🎨 Diseño compacto

🎯 **Ideal para:** Entrada al mundo smartphone

✅ **Android Go Edition optimizado""",
        "precio_proveedor": 88,
        "precio_final": 135,  # Ganancia: $47
        "precio_oferta": 125,  # Oferta: $37 ganancia
        "imagenes": []
    },
    {
        "nombre": "Tecno Spark 40C 256GB (16GB RAM)",
        "descripcion": """📱 **Tecno Spark 40C 256GB** - Memoria Masiva

✨ **Características Principales:**
• 📲 Pantalla: 6.8" FHD+ 120Hz
• 💾 Almacenamiento: 256GB + 16GB RAM Total
• 🔋 Batería: 5200mAh con carga rápida 33W
• 📸 Cámara Triple: 64MP + 2MP + AI Lens
• 🤳 Cámara Frontal: 16MP con flash
• 🧠 Procesador: MediaTek Helio G99
• 🎮 16GB RAM (8GB + 8GB Virtual)
• 🔊 Altavoces DTS
• 💡 LED de notificaciones RGB

🎯 **Ideal para:** Gaming hardcore, edición de video

✅ **HiOS 14 | Refrigeración avanzada""",
        "precio_proveedor": 117,
        "precio_final": 169,  # Ganancia: $52
        "precio_oferta": 159,  # Oferta: $42 ganancia
        "imagenes": []
    },

    # ============ INFINIX ============
    {
        "nombre": "Infinix Smart 10 64GB",
        "descripcion": """📱 **Infinix Smart 10 64GB** - Inteligencia Accesible

✨ **Características Principales:**
• 📲 Pantalla: 6.6" HD+ 90Hz
• 💾 Almacenamiento: 64GB
• 🔋 Batería: 5000mAh
• 📸 Cámara Dual: 13MP + IA
• 🤳 Cámara Frontal: 8MP
• 🧠 Procesador: MediaTek
• 🎮 RAM: 3GB + 3GB Virtual
• 🎨 Diseño premium

🎯 **Ideal para:** Comunicación y entretenimiento

✅ **XOS optimizado para rendimiento""",
        "precio_proveedor": 77,
        "precio_final": 119,  # Ganancia: $42
        "precio_oferta": 109,  # Oferta: $32 ganancia
        "imagenes": []
    },
    {
        "nombre": "Infinix Hot 60i 256GB (4GB+4GB RAM)",
        "descripcion": """📱 **Infinix Hot 60i 256GB** - Calor de Rendimiento

✨ **Características Principales:**
• 📲 Pantalla: 6.7" FHD+ AMOLED 120Hz
• 💾 Almacenamiento: 256GB + 8GB RAM Total
• 🔋 Batería: 5000mAh con carga rápida 45W
• 📸 Cámara Triple: 50MP + 2MP Macro + AI
• 🤳 Cámara Frontal: 13MP
• 🧠 Procesador: MediaTek Helio G99
• 🎮 8GB RAM (4GB + 4GB Extendida)
• 🔒 Sensor de huellas en pantalla
• 📶 Conectividad completa

🎯 **Ideal para:** Gaming, fotografía, multitarea

✅ **Carga ultrarrápida | XOS 14""",
        "precio_proveedor": 123,
        "precio_final": 179,  # Ganancia: $56
        "precio_oferta": 169,  # Oferta: $46 ganancia
        "imagenes": []
    },
    {
        "nombre": "Infinix Hot 60 Pro 256GB (16GB RAM)",
        "descripcion": """📱 **Infinix Hot 60 Pro 256GB** - Nivel Pro

✨ **Características Principales:**
• 📲 Pantalla: 6.78" FHD+ AMOLED 144Hz
• 💾 Almacenamiento: 256GB + 16GB RAM Total
• 🔋 Batería: 5200mAh con carga rápida 70W
• 📸 Sistema de Cámara Cuádruple: 108MP + 8MP Ultra Wide + 2MP Macro + AI
• 🤳 Cámara Frontal: 32MP con dual flash
• 🧠 Procesador: MediaTek Dimensity 8200
• 🎮 16GB RAM (8GB + 8GB Virtual)
• 🔊 Altavoces JBL estéreo
• 🎮 GPU Mali-G610
• 🌡️ Sistema de enfriamiento líquido vapor

🎯 **Ideal para:** Gaming profesional, creación de contenido 4K

✅ **Carga completa en 30 minutos | 5G""",
        "precio_proveedor": 173,
        "precio_final": 249,  # Ganancia: $76
        "precio_oferta": 239,  # Oferta: $66 ganancia
        "imagenes": []
    },
    {
        "nombre": "Infinix Hot 60 Pro Plus 256GB (16GB RAM)",
        "descripcion": """📱 **Infinix Hot 60 Pro Plus 256GB** - El Máximo Poder

✨ **Características Principales:**
• 📲 Pantalla: 6.8" 2K AMOLED 165Hz con Gorilla Glass Victus
• 💾 Almacenamiento: 256GB UFS 3.1 + 16GB RAM
• 🔋 Batería: 5500mAh con carga ultrarrápida 120W + carga inalámbrica 50W
• 📸 Sistema de Cámara Premium: 200MP Principal + 13MP Ultra Wide + 5MP Macro + 2MP Depth
• 🤳 Cámara Frontal: 60MP con OIS
• 🧠 Procesador: MediaTek Dimensity 9200+
• 🎮 16GB RAM LPDDR5X (8GB + 8GB Virtual)
• 🔊 Sistema de audio Harman Kardon
• 🎮 GPU Immortalis-G715
• 🌡️ Sistema de refrigeración líquido mejorado
• 📶 5G+ | WiFi 7 | NFC

🎯 **Ideal para:** Gaming extremo, fotografía profesional, edición de video 4K

✅ **Carga completa en 15 minutos | Certificación IP68""",
        "precio_proveedor": 203,
        "precio_final": 289,  # Ganancia: $86
        "precio_oferta": 279,  # Oferta: $76 ganancia
        "imagenes": []
    },
    {
        "nombre": "Infinix Note 50 Pro 256GB (16GB RAM)",
        "descripcion": """📱 **Infinix Note 50 Pro 256GB** - Productividad Extrema

✨ **Características Principales:**
• 📲 Pantalla: 6.95" 2K AMOLED 144Hz con stylus
• 💾 Almacenamiento: 256GB + 16GB RAM
• 🔋 Batería: 6000mAh con carga rápida 100W
• 📸 Cámara Cuádruple: 200MP + 13MP + 8MP Telephoto 3x + 2MP
• 🤳 Cámara Frontal: 32MP
• 🧠 Procesador: MediaTek Dimensity 8300
• 🎮 16GB RAM (8GB + 8GB Virtual)
• ✏️ Incluye Stylus X-Pen con presión 4096 niveles
• 🔊 Quad speakers con Dolby Atmos
• 📶 5G | WiFi 6E

🎯 **Ideal para:** Profesionales, diseñadores, estudiantes, gamers

✅ **El smartphone más completo de Infinix | Garantía extendida""",
        "precio_proveedor": 250,
        "precio_final": 349,  # Ganancia: $99
        "precio_oferta": 339,  # Oferta: $89 ganancia
        "imagenes": []
    },

    # ============ HONOR ============
    {
        "nombre": "Honor X5c 64GB",
        "descripcion": """📱 **Honor X5c 64GB** - Elegancia Honor

✨ **Características Principales:**
• 📲 Pantalla: 6.5" HD+ IPS 90Hz
• 💾 Almacenamiento: 64GB
• 🔋 Batería: 5000mAh
• 📸 Cámara Dual: 13MP + 2MP
• 🤳 Cámara Frontal: 5MP
• 🧠 Procesador: MediaTek
• 🎮 RAM: 3GB
• 🎨 Diseño premium Honor

🎯 **Ideal para:** Uso diario elegante

✅ **Magic UI optimizado""",
        "precio_proveedor": 80,
        "precio_final": 125,  # Ganancia: $45
        "precio_oferta": 115,  # Oferta: $35 ganancia
        "imagenes": []
    },
    {
        "nombre": "Honor X5c 128GB (4GB RAM)",
        "descripcion": """📱 **Honor X5c 128GB** - Más Espacio Honor

✨ **Características Principales:**
• 📲 Pantalla: 6.5" HD+ IPS 90Hz
• 💾 Almacenamiento: 128GB + 4GB RAM
• 🔋 Batería: 5200mAh
• 📸 Cámara Dual: 13MP + 2MP con IA
• 🤳 Cámara Frontal: 5MP con modo belleza
• 🧠 Procesador: MediaTek Helio G85
• 🎮 RAM: 4GB
• 🔒 Sensor de huellas lateral
• 🎨 Acabado premium

🎯 **Ideal para:** Multimedia y almacenamiento

✅ **Magic UI 7.0""",
        "precio_proveedor": 89,
        "precio_final": 139,  # Ganancia: $50
        "precio_oferta": 129,  # Oferta: $40 ganancia
        "imagenes": []
    },
    {
        "nombre": "Honor X6c 256GB (6GB RAM)",
        "descripcion": """📱 **Honor X6c 256GB** - Potencia y Estilo

✨ **Características Principales:**
• 📲 Pantalla: 6.77" FHD+ IPS 120Hz
• 💾 Almacenamiento: 256GB + 6GB RAM
• 🔋 Batería: 5300mAh con carga rápida 40W
• 📸 Triple Cámara: 50MP + 5MP Ultra Wide + 2MP
• 🤳 Cámara Frontal: 16MP
• 🧠 Procesador: Snapdragon 6 Gen 1
• 🎮 RAM: 6GB
• 🔒 Sensor de huellas en pantalla
• 📶 5G Ready

🎯 **Ideal para:** Performance equilibrado

✅ **Diseño Honor insignia""",
        "precio_proveedor": 128,
        "precio_final": 189,  # Ganancia: $61
        "precio_oferta": 179,  # Oferta: $51 ganancia
        "imagenes": []
    },
    {
        "nombre": "Honor X7d 256GB",
        "descripcion": """📱 **Honor X7d 256GB** - Diseño Premium

✨ **Características Principales:**
• 📲 Pantalla: 6.8" FHD+ AMOLED 144Hz
• 💾 Almacenamiento: 256GB + 8GB RAM
• 🔋 Batería: 5500mAh con carga rápida 66W
• 📸 Cámara Triple: 108MP + 8MP Ultra Wide + 2MP Macro
• 🤳 Cámara Frontal: 32MP
• 🧠 Procesador: Snapdragon 7 Gen 1
• 🎮 RAM: 8GB
• 🔊 Altavoces estéreo
• 🌈 Diseño curvo premium
• 📶 5G

🎯 **Ideal para:** Gaming y fotografía avanzada

✅ **Magic UI 8.0 con IA""",
        "precio_proveedor": 178,
        "precio_final": 259,  # Ganancia: $81
        "precio_oferta": 249,  # Oferta: $71 ganancia
        "imagenes": []
    },
    {
        "nombre": "Honor 400 Lite 256GB",
        "descripcion": """📱 **Honor 400 Lite 256GB** - Gama Media Premium

✨ **Características Principales:**
• 📲 Pantalla: 6.9" 2K AMOLED 165Hz con HDR10+
• 💾 Almacenamiento: 256GB UFS 3.1 + 12GB RAM
• 🔋 Batería: 6000mAh con carga rápida 100W + inalámbrica 50W
• 📸 Sistema Cuádruple: 200MP Principal + 12MP Ultra Wide + 8MP Telephoto 3x + 2MP
• 🤳 Cámara Frontal: 50MP con 4K 60fps
• 🧠 Procesador: Snapdragon 8 Gen 2
• 🎮 RAM: 12GB LPDDR5
• 🔊 Sistema de audio Harman Kardon
• 🎮 GPU Adreno 740
• 🔒 Sensor ultrasónico bajo pantalla
• 📶 5G+ | WiFi 7 | NFC
• 🌡️ Sistema de enfriamiento vapor chamber

🎯 **Ideal para:** Fotografía profesional, gaming extremo, creadores

✅ **Honor OS con IA avanzada | Certificación IP68 | Carga completa 20min""",
        "precio_proveedor": 280,
        "precio_final": 389,  # Ganancia: $109
        "precio_oferta": 379,  # Oferta: $99 ganancia
        "imagenes": []
    },

    # ============ ZTE ============
    {
        "nombre": "ZTE A56 128GB",
        "descripcion": """📱 **ZTE A56 128GB** - Relación Calidad-Precio

✨ **Características Principales:**
• 📲 Pantalla: 6.52" HD+ IPS
• 💾 Almacenamiento: 128GB
• 🔋 Batería: 4500mAh
• 📸 Cámara Dual: 13MP + 2MP
• 🤳 Cámara Frontal: 5MP
• 🧠 Procesador: Unisoc
• 🎮 RAM: 3GB
• 🎨 Diseño compacto

🎯 **Ideal para:** Usuario básico

✅ **Android stock limpio""",
        "precio_proveedor": 79,
        "precio_final": 125,  # Ganancia: $46
        "precio_oferta": 115,  # Oferta: $36 ganancia
        "imagenes": []
    },
    {
        "nombre": "ZTE A56 Pro 128GB",
        "descripcion": """📱 **ZTE A56 Pro 128GB** - Versión Mejorada

✨ **Características Principales:**
• 📲 Pantalla: 6.6" HD+ IPS 90Hz
• 💾 Almacenamiento: 128GB
• 🔋 Batería: 5000mAh con carga rápida
• 📸 Cámara Triple: 16MP + 5MP + 2MP
• 🤳 Cámara Frontal: 8MP
• 🧠 Procesador: MediaTek Helio G36
• 🎮 RAM: 4GB
• 🔒 Sensor de huellas
• 🎨 Diseño premium

🎯 **Ideal para:** Uso diario fluido

✅ **ZTE UI optimizado""",
        "precio_proveedor": 85,
        "precio_final": 135,  # Ganancia: $50
        "precio_oferta": 125,  # Oferta: $40 ganancia
        "imagenes": []
    },
]

# Productos iPhone
iphones = [
    # iPhone 11
    {
        "nombre": "iPhone 11 64GB - Open Box",
        "descripcion": """📱 **iPhone 11 64GB** - El Clásico que Nunca Falla

✨ **Características Principales:**
• 📲 Pantalla: 6.1" Liquid Retina HD (LCD)
• 💾 Almacenamiento: 64GB
• 🔋 Batería: 100% de salud garantizada
• 📸 Dual Camera: 12MP Wide + 12MP Ultra Wide
• 🤳 Cámara Frontal TrueDepth: 12MP con Face ID
• 🧠 Chip: A13 Bionic
• 🎥 Video 4K a 60fps
• 💧 Resistencia al agua IP68
• 🎨 Disponible en múltiples colores

🎯 **Perfecto para:** Usuarios que quieren calidad Apple sin gastar de más

✅ **Open Box = Como nuevo | Batería 100% | Garantía incluida**""",
        "precio_proveedor": 245,
        "precio_final": 329,  # Ganancia: $84
        "precio_oferta": 319,  # Oferta: $74 ganancia
        "imagenes": []
    },
    {
        "nombre": "iPhone 11 128GB - Open Box",
        "descripcion": """📱 **iPhone 11 128GB** - Más Espacio para Tus Momentos

✨ **Características Principales:**
• 📲 Pantalla: 6.1" Liquid Retina HD
• 💾 Almacenamiento: 128GB - Doble capacidad
• 🔋 Batería: 100% de salud
• 📸 Sistema de cámara dual 12MP
• 🤳 TrueDepth 12MP
• 🧠 A13 Bionic
• 🎥 Slow-motion selfies
• 💧 IP68
• 🌈 6 colores disponibles

🎯 **Ideal para:** Quienes usan muchas apps y fotos

✅ **Estado impecable | Batería nueva**""",
        "precio_proveedor": 280,
        "precio_final": 369,  # Ganancia: $89
        "precio_oferta": 359,  # Oferta: $79 ganancia
        "imagenes": []
    },
    {
        "nombre": "iPhone 12 64GB - Open Box",
        "descripcion": """📱 **iPhone 12 64GB** - Diseño Premium 5G

✨ **Características Principales:**
• 📲 Pantalla: 6.1" Super Retina XDR OLED
• 💾 Almacenamiento: 64GB
• 🔋 Batería: 100% de salud
• 📸 Dual Camera: 12MP con modo Noche mejorado
• 🤳 TrueDepth: 12MP con Dolby Vision
• 🧠 Chip: A14 Bionic
• 📶 Conectividad 5G
• 🎥 HDR Dolby Vision
• 💎 Ceramic Shield
• 💧 IP68

🎯 **Perfecto para:** Entrada al ecosistema 5G de Apple

✅ **Open Box certificado | Batería 100%**""",
        "precio_proveedor": 285,
        "precio_final": 379,  # Ganancia: $94
        "precio_oferta": 369,  # Oferta: $84 ganancia
        "imagenes": []
    },
    {
        "nombre": "iPhone 12 128GB - Open Box",
        "descripcion": """📱 **iPhone 12 128GB** - El Equilibrio Perfecto

✨ **Características Principales:**
• 📲 Pantalla: 6.1" Super Retina XDR
• 💾 Almacenamiento: 128GB
• 🔋 Batería: 100% de salud
• 📸 Dual 12MP con Smart HDR 3
• 🤳 12MP TrueDepth
• 🧠 A14 Bionic
• 📶 5G ultrarrápido
• 🎥 4K Dolby Vision hasta 30fps
• 💎 Cristal Ceramic Shield
• 🧲 MagSafe

🎯 **Ideal para:** Usuario que busca rendimiento y capacidad

✅ **Impecable | Batería 100% | Accesorios incluidos**""",
        "precio_proveedor": 300,
        "precio_final": 399,  # Ganancia: $99
        "precio_oferta": 389,  # Oferta: $89 ganancia
        "imagenes": []
    },
    {
        "nombre": "iPhone 12 256GB - Open Box",
        "descripcion": """📱 **iPhone 12 256GB** - Máxima Capacidad

✨ **Características Principales:**
• 📲 Pantalla: 6.1" Super Retina XDR
• 💾 Almacenamiento: 256GB - Espacio de sobra
• 🔋 Batería: 100% de salud
• 📸 Sistema dual 12MP profesional
• 🤳 12MP con modo retrato
• 🧠 A14 Bionic Neural Engine
• 📶 5G
• 🎥 ProRes y Dolby Vision
• 💎 Ceramic Shield
• 🧲 MagSafe

🎯 **Perfecto para:** Creadores de contenido y power users

✅ **Como nuevo | Batería 100% | Garantía**""",
        "precio_proveedor": 350,
        "precio_final": 459,  # Ganancia: $109
        "precio_oferta": 449,  # Oferta: $99 ganancia
        "imagenes": []
    },
    # iPhone 12 Pro
    {
        "nombre": "iPhone 12 Pro 128GB - Open Box",
        "descripcion": """📱 **iPhone 12 Pro 128GB** - Nivel Profesional

✨ **Características Principales:**
• 📲 Pantalla: 6.1" Super Retina XDR ProMotion
• 💾 Almacenamiento: 128GB
• 🔋 Batería: 100% de salud
• 📸 Triple cámara Pro: 12MP Wide + Ultra Wide + Telephoto 2x
• 🎯 LiDAR Scanner para AR
• 🤳 12MP TrueDepth
• 🧠 A14 Bionic
• 📶 5G mmWave
• 🎥 Apple ProRAW + ProRes
• 💎 Marco de acero inoxidable quirúrgico
• 💧 IP68

🎯 **Ideal para:** Fotógrafos y videógrafos

✅ **Estado premium | Batería 100%**""",
        "precio_proveedor": 400,
        "precio_final": 529,  # Ganancia: $129
        "precio_oferta": 519,  # Oferta: $119 ganancia
        "imagenes": []
    },
    {
        "nombre": "iPhone 12 Pro 256GB - Open Box",
        "descripcion": """📱 **iPhone 12 Pro 256GB** - Pro con Espacio Pro

✨ **Características Principales:**
• 📲 Pantalla: 6.1" Super Retina XDR
• 💾 Almacenamiento: 256GB
• 🔋 Batería: 100% de salud
• 📸 Sistema Pro de triple cámara con LiDAR
• 🤳 12MP TrueDepth con modo noche
• 🧠 A14 Bionic
• 📶 5G completo
• 🎥 ProRAW 12MP + Dolby Vision 4K 60fps
• 💎 Diseño premium acero inoxidable
• 🧲 MagSafe
• 💧 IP68

🎯 **Perfecto para:** Profesionales creativos

✅ **Condición impecable | Batería 100%**""",
        "precio_proveedor": 425,
        "precio_final": 559,  # Ganancia: $134
        "precio_oferta": 549,  # Oferta: $124 ganancia
        "imagenes": []
    },
    {
        "nombre": "iPhone 12 Pro 512GB - Open Box",
        "descripcion": """📱 **iPhone 12 Pro 512GB** - Máxima Capacidad Pro

✨ **Características Principales:**
• 📲 Pantalla: 6.1" Super Retina XDR
• 💾 Almacenamiento: 512GB - Capacidad extrema
• 🔋 Batería: 100% de salud
• 📸 Triple cámara Pro + LiDAR
• 🤳 12MP TrueDepth avanzada
• 🧠 A14 Bionic
• 📶 5G
• 🎥 Apple ProRAW + ProRes Video
• 💎 Acabado premium
• 🧲 Accesorios MagSafe
• 💧 Resistencia IP68

🎯 **Ideal para:** Profesionales que necesitan todo el espacio

✅ **Prácticamente nuevo | Batería 100%**""",
        "precio_proveedor": 450,
        "precio_final": 589,  # Ganancia: $139
        "precio_oferta": 579,  # Oferta: $129 ganancia
        "imagenes": []
    },
    # iPhone 12 Pro Max
    {
        "nombre": "iPhone 12 Pro Max 128GB - Open Box",
        "descripcion": """📱 **iPhone 12 Pro Max 128GB** - El Más Grande

✨ **Características Principales:**
• 📲 Pantalla: 6.7" Super Retina XDR - La más grande
• 💾 Almacenamiento: 128GB
• 🔋 Batería: 100% de salud - Mayor duración
• 📸 Triple cámara Pro con sensor más grande + LiDAR
• 🎯 Estabilización óptica de imagen con sensor-shift
• 🤳 12MP TrueDepth
• 🧠 A14 Bionic
• 📶 5G completo
• 🎥 ProRAW + Dolby Vision HDR
• 💎 Diseño premium máximo
• 💧 IP68

🎯 **Perfecto para:** Quienes quieren la mejor cámara y pantalla

✅ **Estado excelente | Batería 100%**""",
        "precio_proveedor": 500,
        "precio_final": 659,  # Ganancia: $159
        "precio_oferta": 649,  # Oferta: $149 ganancia
        "imagenes": []
    },
    {
        "nombre": "iPhone 12 Pro Max 256GB - Open Box",
        "descripcion": """📱 **iPhone 12 Pro Max 256GB** - Máximo Rendimiento

✨ **Características Principales:**
• 📲 Pantalla: 6.7" Super Retina XDR
• 💾 Almacenamiento: 256GB
• 🔋 Batería: 100% de salud - La mejor autonomía
• 📸 Sistema de cámara Pro máximo con sensor shift OIS
• 🎯 LiDAR para fotos nocturnas profesionales
• 🤳 12MP TrueDepth
• 🧠 A14 Bionic
• 📶 5G ultrarrápido
• 🎥 ProRAW + ProRes + Dolby Vision 4K 60fps
• 💎 Marco de acero inoxidable
• 🧲 MagSafe
• 💧 IP68

🎯 **Ideal para:** Fotógrafos y videógrafos profesionales

✅ **Como nuevo | Batería 100% | Todos los accesorios**""",
        "precio_proveedor": 550,
        "precio_final": 719,  # Ganancia: $169
        "precio_oferta": 709,  # Oferta: $159 ganancia
        "imagenes": []
    },
]

# Agregar más iPhones (13, 14, 15, 16)
iphones_adicionales = [
    # iPhone 13
    {
        "nombre": "iPhone 13 128GB - Open Box",
        "descripcion": """📱 **iPhone 13 128GB** - Rendimiento Superior

✨ **Características Principales:**
• 📲 Pantalla: 6.1" Super Retina XDR más brillante
• 💾 Almacenamiento: 128GB
• 🔋 Batería: 100% - Hasta 19h de video
• 📸 Dual 12MP con Photographic Styles y Cinematic Mode
• 🤳 12MP TrueDepth con modo Cinematic
• 🧠 A15 Bionic (mismo del 13 Pro)
• 📶 5G
• 🎥 Modo Cinematográfico 1080p 30fps
• 💎 Ceramic Shield
• 💧 IP68

🎯 **Perfecto para:** Rendimiento Apple actual a buen precio

✅ **Open Box | Batería 100% | Garantía**""",
        "precio_proveedor": 370,
        "precio_final": 489,  # Ganancia: $119
        "precio_oferta": 479,  # Oferta: $109 ganancia
        "imagenes": []
    },
    {
        "nombre": "iPhone 13 256GB - Open Box",
        "descripcion": """📱 **iPhone 13 256GB** - Más Espacio, Mismo Poder

✨ **Características Principales:**
• 📲 Pantalla: 6.1" Super Retina XDR
• 💾 Almacenamiento: 256GB
• 🔋 Batería: 100% de salud
• 📸 Dual 12MP con modo Cinematográfico
• 🤳 12MP TrueDepth
• 🧠 A15 Bionic
• 📶 5G
• 🎥 HDR 4 con Dolby Vision
• 💎 Diseño premium
• 🧲 MagSafe
• 💧 IP68

🎯 **Ideal para:** Usuario exigente con apps y fotos

✅ **Estado impecable | Batería 100%**""",
        "precio_proveedor": 420,
        "precio_final": 559,  # Ganancia: $139
        "precio_oferta": 549,  # Oferta: $129 ganancia
        "imagenes": []
    },
    # iPhone 13 Pro
    {
        "nombre": "iPhone 13 Pro 128GB - Open Box",
        "descripcion": """📱 **iPhone 13 Pro 128GB** - ProMotion 120Hz

✨ **Características Principales:**
• 📲 Pantalla: 6.1" Super Retina XDR con ProMotion 120Hz
• 💾 Almacenamiento: 128GB
• 🔋 Batería: 100% de salud
• 📸 Triple cámara Pro: 12MP Telephoto 3x + Wide + Ultra Wide
• 🌙 Modo Noche en todas las cámaras
• 🤳 12MP TrueDepth con ProRes
• 🧠 A15 Bionic con GPU 5-core
• 📶 5G
• 🎥 ProRes video + Modo Cinematográfico
• 💎 Acero inoxidable quirúrgico
• 💧 IP68

🎯 **Perfecto para:** Profesionales creativos

✅ **Condición premium | Batería 100%**""",
        "precio_proveedor": 480,
        "precio_final": 629,  # Ganancia: $149
        "precio_oferta": 619,  # Oferta: $139 ganancia
        "imagenes": []
    },
    {
        "nombre": "iPhone 13 Pro 256GB - Open Box",
        "descripcion": """📱 **iPhone 13 Pro 256GB** - Pro Completo

✨ **Características Principales:**
• 📲 Pantalla: 6.1" ProMotion 120Hz
• 💾 Almacenamiento: 256GB
• 🔋 Batería: 100% de salud
• 📸 Sistema Pro de triple cámara con macro
• 🎯 LiDAR Scanner
• 🤳 12MP TrueDepth con Night mode
• 🧠 A15 Bionic Pro
• 📶 5G mmWave
• 🎥 Apple ProRes + ProRAW
• 💎 Diseño premium
• 🧲 MagSafe
• 💧 IP68

🎯 **Ideal para:** Creadores de contenido profesional

✅ **Como nuevo | Batería 100%**""",
        "precio_proveedor": 500,
        "precio_final": 659,  # Ganancia: $159
        "precio_oferta": 649,  # Oferta: $149 ganancia
        "imagenes": []
    },
    # iPhone 13 Pro Max
    {
        "nombre": "iPhone 13 Pro Max 128GB - Open Box",
        "descripcion": """📱 **iPhone 13 Pro Max 128GB** - El Máximo de 13

✨ **Características Principales:**
• 📲 Pantalla: 6.7" ProMotion 120Hz - La más grande
• 💾 Almacenamiento: 128GB
• 🔋 Batería: 100% - Hasta 28h de video
• 📸 Triple cámara Pro con sensores más grandes
• 🌙 Modo Noche mejorado con LiDAR
• 🤳 12MP TrueDepth
• 🧠 A15 Bionic con GPU 5-core
• 📶 5G completo
• 🎥 ProRes 4K + Modo Cinematográfico
• 💎 Premium máximo
• 💧 IP68

🎯 **Perfecto para:** Máxima pantalla y batería

✅ **Estado excelente | Batería 100%**""",
        "precio_proveedor": 550,
        "precio_final": 719,  # Ganancia: $169
        "precio_oferta": 709,  # Oferta: $159 ganancia
        "imagenes": []
    },
    {
        "nombre": "iPhone 13 Pro Max 256GB - Open Box",
        "descripcion": """📱 **iPhone 13 Pro Max 256GB** - Potencia Máxima

✨ **Características Principales:**
• 📲 Pantalla: 6.7" ProMotion 120Hz
• 💾 Almacenamiento: 256GB
• 🔋 Batería: 100% - La mejor duración
• 📸 Sistema Pro de triple cámara + macro
• 🎯 LiDAR para AR profesional
• 🤳 12MP TrueDepth avanzada
• 🧠 A15 Bionic Pro
• 📶 5G ultrarrápido
• 🎥 ProRes + ProRAW + Cinematic
• 💎 Diseño premium máximo
• 🧲 MagSafe
• 💧 IP68

🎯 **Ideal para:** Profesionales sin compromisos

✅ **Impecable | Batería 100% | Completo**""",
        "precio_proveedor": 600,
        "precio_final": 789,  # Ganancia: $189
        "precio_oferta": 779,  # Oferta: $179 ganancia
        "imagenes": []
    },
    # iPhone 14
    {
        "nombre": "iPhone 14 128GB eSIM - Open Box",
        "descripcion": """📱 **iPhone 14 128GB** - Nueva Generación con eSIM

✨ **Características Principales:**
• 📲 Pantalla: 6.1" Super Retina XDR
• 💾 Almacenamiento: 128GB
• 🔋 Batería: 100% de salud
• 📸 Dual 12MP con Photonic Engine
• 🆘 Detección de choques y SOS vía satélite
• 🤳 12MP TrueDepth con Autofocus
• 🧠 A15 Bionic mejorado
• 📱 Solo eSIM (sin bandeja física)
• 📶 5G
• 🎥 Action Mode para video estable
• 💧 IP68

🎯 **Perfecto para:** Tecnología actual de Apple

✅ **Open Box | Batería 100% | eSIM activable**""",
        "precio_proveedor": 430,
        "precio_final": 569,  # Ganancia: $139
        "precio_oferta": 559,  # Oferta: $129 ganancia
        "imagenes": []
    },
    # iPhone 14 Pro
    {
        "nombre": "iPhone 14 Pro 128GB eSIM - Open Box",
        "descripcion": """📱 **iPhone 14 Pro 128GB** - Dynamic Island

✨ **Características Principales:**
• 📲 Pantalla: 6.1" Super Retina XDR con Dynamic Island y Always-On
• 💾 Almacenamiento: 128GB
• 🔋 Batería: 100% de salud
• 📸 Triple cámara Pro: 48MP Principal + 12MP Ultra Wide + 12MP Telephoto 3x
• 🌟 Dynamic Island - Nueva interfaz interactiva
• 🤳 12MP TrueDepth con Autofocus
• 🧠 A16 Bionic (más rápido y eficiente)
• 📱 Solo eSIM
• 📶 5G
• 🎥 ProRes 4K + Action Mode
• 💎 Acero inoxidable
• 💧 IP68

🎯 **Perfecto para:** Profesionales y early adopters

✅ **Estado premium | Batería 100%**""",
        "precio_proveedor": 575,
        "precio_final": 749,  # Ganancia: $174
        "precio_oferta": 739,  # Oferta: $164 ganancia
        "imagenes": []
    },
    {
        "nombre": "iPhone 14 Pro 256GB eSIM - Open Box",
        "descripcion": """📱 **iPhone 14 Pro 256GB** - Pro con Espacio

✨ **Características Principales:**
• 📲 Pantalla: 6.1" ProMotion 120Hz con Dynamic Island
• 💾 Almacenamiento: 256GB
• 🔋 Batería: 100% de salud
• 📸 Sistema Pro: 48MP + 12MP + 12MP con zoom óptico 3x
• 🌟 Dynamic Island inteligente
• 🤳 12MP TrueDepth con Autofocus
• 🧠 A16 Bionic
• 📱 eSIM
• 📶 5G
• 🎥 48MP ProRAW + ProRes
• 💎 Premium
• 💧 IP68

🎯 **Ideal para:** Fotógrafos y creadores

✅ **Impecable | Batería 100%**""",
        "precio_proveedor": 610,
        "precio_final": 799,  # Ganancia: $189
        "precio_oferta": 789,  # Oferta: $179 ganancia
        "imagenes": []
    },
    # iPhone 14 Plus
    {
        "nombre": "iPhone 14 Plus 128GB eSIM - Open Box",
        "descripcion": """📱 **iPhone 14 Plus 128GB** - Pantalla Grande, Precio Justo

✨ **Características Principales:**
• 📲 Pantalla: 6.7" Super Retina XDR - Grande como Pro Max
• 💾 Almacenamiento: 128GB
• 🔋 Batería: 100% - Máxima duración (hasta 26h de video)
• 📸 Dual 12MP con Photonic Engine
• 🆘 Detección de choques + SOS satélite
• 🤳 12MP TrueDepth con Autofocus
• 🧠 A15 Bionic
• 📱 eSIM
• 📶 5G
• 🎥 Action Mode
• 💧 IP68

🎯 **Perfecto para:** Quienes quieren pantalla grande sin gastar Pro Max

✅ **Gran estado | Batería 100%**""",
        "precio_proveedor": 465,
        "precio_final": 619,  # Ganancia: $154
        "precio_oferta": 609,  # Oferta: $144 ganancia
        "imagenes": []
    },
    # iPhone 14 Pro Max
    {
        "nombre": "iPhone 14 Pro Max 128GB eSIM - Open Box",
        "descripcion": """📱 **iPhone 14 Pro Max 128GB** - El Mejor de 2022

✨ **Características Principales:**
• 📲 Pantalla: 6.7" ProMotion 120Hz con Dynamic Island y Always-On
• 💾 Almacenamiento: 128GB
• 🔋 Batería: 100% - Hasta 29h de video
• 📸 Triple cámara Pro: 48MP Principal + 12MP Ultra Wide + 12MP Telephoto 3x
• 🌟 Dynamic Island
• 🤳 12MP TrueDepth con Autofocus
• 🧠 A16 Bionic
• 📱 eSIM
• 📶 5G completo
• 🎥 48MP ProRAW + ProRes + Cinematic 4K
• 💎 Premium máximo
• 💧 IP68

🎯 **Perfecto para:** Quienes buscan lo máximo

✅ **Estado excelente | Batería 100%**""",
        "precio_proveedor": 700,
        "precio_final": 919,  # Ganancia: $219
        "precio_oferta": 909,  # Oferta: $209 ganancia
        "imagenes": []
    },
    {
        "nombre": "iPhone 14 Pro Max 256GB eSIM - Open Box",
        "descripcion": """📱 **iPhone 14 Pro Max 256GB** - Máxima Potencia

✨ **Características Principales:**
• 📲 Pantalla: 6.7" ProMotion con Dynamic Island
• 💾 Almacenamiento: 256GB
• 🔋 Batería: 100% - La mejor autonomía
• 📸 Sistema Pro completo 48MP
• 🌟 Dynamic Island interactiva
• 🤳 12MP TrueDepth mejorada
• 🧠 A16 Bionic
• 📱 eSIM dual
• 📶 5G
• 🎥 ProRAW 48MP + ProRes 4K
• 💎 Diseño premium
• 🧲 MagSafe
• 💧 IP68

🎯 **Ideal para:** Profesionales exigentes

✅ **Impecable | Batería 100% | Completo**""",
        "precio_proveedor": 725,
        "precio_final": 949,  # Ganancia: $224
        "precio_oferta": 939,  # Oferta: $214 ganancia
        "imagenes": []
    },
    {
        "nombre": "iPhone 14 Pro Max 512GB eSIM - Open Box",
        "descripcion": """📱 **iPhone 14 Pro Max 512GB** - Capacidad Máxima

✨ **Características Principales:**
• 📲 Pantalla: 6.7" ProMotion 120Hz con Dynamic Island
• 💾 Almacenamiento: 512GB - Espacio ilimitado
• 🔋 Batería: 100% de salud
• 📸 Triple Pro 48MP completo
• 🌟 Dynamic Island
• 🤳 12MP TrueDepth Pro
• 🧠 A16 Bionic
• 📱 eSIM
• 📶 5G ultrarrápido
• 🎥 ProRAW + ProRes sin límites
• 💎 Premium total
• 🧲 MagSafe
• 💧 IP68

🎯 **Perfecto para:** Profesionales sin compromisos de espacio

✅ **Como nuevo | Batería 100% | Todo incluido**""",
        "precio_proveedor": 750,
        "precio_final": 989,  # Ganancia: $239
        "precio_oferta": 979,  # Oferta: $229 ganancia
        "imagenes": []
    },
    # iPhone 15
    {
        "nombre": "iPhone 15 128GB eSIM - Open Box",
        "descripcion": """📱 **iPhone 15 128GB** - USB-C y Dynamic Island

✨ **Características Principales:**
• 📲 Pantalla: 6.1" Super Retina XDR con Dynamic Island
• 💾 Almacenamiento: 128GB
• 🔋 Batería: 100% de salud
• 📸 Dual 48MP Principal + 12MP Ultra Wide (2x Telephoto digital)
• 🌟 Dynamic Island ahora en modelo base
• 🤳 12MP TrueDepth con Autofocus
• 🧠 A16 Bionic (del 14 Pro)
• 🔌 USB-C (adiós Lightning!)
• 📱 eSIM
• 📶 5G
• 🎥 4K Cinematic Mode 30fps
• 🌈 Colores vibrantes nuevos
• 💧 IP68

🎯 **Perfecto para:** Tecnología actual con USB-C

✅ **Open Box | Batería 100% | Cable USB-C incluido**""",
        "precio_proveedor": 600,
        "precio_final": 789,  # Ganancia: $189
        "precio_oferta": 779,  # Oferta: $179 ganancia
        "imagenes": []
    },
    {
        "nombre": "iPhone 15 256GB eSIM - Open Box",
        "descripcion": """📱 **iPhone 15 256GB** - Más Espacio USB-C

✨ **Características Principales:**
• 📲 Pantalla: 6.1" Super Retina XDR con Dynamic Island
• 💾 Almacenamiento: 256GB
• 🔋 Batería: 100% de salud
• 📸 Sistema dual 48MP + 12MP
• 🌟 Dynamic Island
• 🤳 12MP TrueDepth Autofocus
• 🧠 A16 Bionic
• 🔌 USB-C 2.0
• 📱 eSIM dual
• 📶 5G
• 🎥 Cinematic 4K
• 🌈 Nuevos colores pasteles
• 💧 IP68

🎯 **Ideal para:** Usuario que quiere lo último

✅ **Estado premium | Batería 100%**""",
        "precio_proveedor": 625,
        "precio_final": 819,  # Ganancia: $194
        "precio_oferta": 809,  # Oferta: $184 ganancia
        "imagenes": []
    },
    # iPhone 15 Pro Max
    {
        "nombre": "iPhone 15 Pro Max 512GB eSIM - Sellado",
        "descripcion": """📱 **iPhone 15 Pro Max 512GB** - Titanio y A17 Pro

✨ **Características Principales:**
• 📲 Pantalla: 6.7" Super Retina XDR ProMotion 120Hz con Always-On
• 💾 Almacenamiento: 512GB
• 🔋 Batería: 100% - Hasta 29h de video
• 📸 Sistema Pro: 48MP Principal + 12MP Ultra Wide + 12MP Telephoto 5x óptico
• 🔍 Zoom óptico 5x (nuevo tetraprism)
• 🌟 Dynamic Island mejorada
• 🤳 12MP TrueDepth con Autofocus
• 🧠 A17 Pro (3nm) - El chip más potente
• 🎮 GPU de nivel consola con Ray Tracing
• 🔌 USB-C 3.0 (10Gbps)
• 📱 eSIM
• 📶 5G+ WiFi 6E
• 🎥 ProRes 4K 60fps + Log encoding
• 💎 Marco de Titanio grado 5 (más ligero y resistente)
• 🔘 Botón de Acción personalizable
• 💧 IP68

🎯 **Perfecto para:** Lo mejor de lo mejor de Apple

✅ **SELLADO de fábrica | Garantía completa Apple**""",
        "precio_proveedor": 950,
        "precio_final": 1249,  # Ganancia: $299
        "precio_oferta": 1239,  # Oferta: $289 ganancia
        "imagenes": []
    },
    # iPhone 16
    {
        "nombre": "iPhone 16 128GB eSIM - Sellado",
        "descripcion": """📱 **iPhone 16 128GB** - Lo Último de Apple 2024

✨ **Características Principales:**
• 📲 Pantalla: 6.1" Super Retina XDR con Dynamic Island
• 💾 Almacenamiento: 128GB
• 🔋 Batería: Nueva tecnología - Mayor duración
• 📸 Sistema Fusión 48MP + 12MP Ultra Wide mejorado
• 🤖 Apple Intelligence (IA integrada)
• 🌟 Dynamic Island
• 🤳 12MP TrueDepth avanzada
• 🧠 A18 (nuevo chip 3nm mejorado)
• 🎮 GPU con Ray Tracing hardware
• 🔌 USB-C 3.0
• 📱 eSIM
• 📶 5G Advanced
• 🎥 Dolby Vision 4K 60fps
• 🔘 Botón de Acción + Control de Cámara (nuevo botón táctil)
• 🌈 Nuevos colores vibrantes
• 💧 IP68

🎯 **Perfecto para:** Quienes quieren lo más nuevo de 2024

✅ **SELLADO | Garantía Apple 1 año | Todos los accesorios**""",
        "precio_proveedor": 719,
        "precio_final": 949,  # Ganancia: $230
        "precio_oferta": 939,  # Oferta: $220 ganancia
        "imagenes": []
    },
    {
        "nombre": "iPhone 16 256GB eSIM - Sellado",
        "descripcion": """📱 **iPhone 16 256GB** - Máxima Novedad Apple

✨ **Características Principales:**
• 📲 Pantalla: 6.1" Super Retina XDR
• 💾 Almacenamiento: 256GB
• 🔋 Batería mejorada
• 📸 Sistema Fusión 48MP completo
• 🤖 Apple Intelligence con Machine Learning
• 🌟 Dynamic Island
• 🤳 12MP TrueDepth
• 🧠 A18 Bionic
• 🎮 Gaming de siguiente nivel
• 🔌 USB-C 3.0 (10Gbps)
• 📱 eSIM
• 📶 5G
• 🎥 Video 4K Dolby Vision
• 🔘 Botón de Acción + Control de Cámara
• 🌈 Colores exclusivos 2024
• 💧 IP68

🎯 **Ideal para:** Early adopters y entusiastas Apple

✅ **NUEVO SELLADO | Garantía completa | Cable USB-C trenzado**""",
        "precio_proveedor": 790,
        "precio_final": 1049,  # Ganancia: $259
        "precio_oferta": 1039,  # Oferta: $249 ganancia
        "imagenes": []
    },
]

def agregar_productos():
    """Agregar todos los productos a la base de datos"""
    with app.app_context():
        print("\n" + "="*60)
        print("AGREGANDO PRODUCTOS A LA BASE DE DATOS")
        print("="*60 + "\n")

        # Combinar todos los productos
        todos_productos = productos + iphones + iphones_adicionales

        contador_agregados = 0
        contador_existentes = 0

        for prod_data in todos_productos:
            # Verificar si el producto ya existe
            existe = Producto.query.filter_by(nombre=prod_data['nombre']).first()

            if existe:
                print(f"[EXISTE] {prod_data['nombre']}")
                contador_existentes += 1
                continue

            # Crear nuevo producto
            producto = Producto(
                nombre=prod_data['nombre'],
                descripcion=prod_data['descripcion'],
                precio_proveedor=Decimal(str(prod_data['precio_proveedor'])),
                precio_final=Decimal(str(prod_data['precio_final'])),
                precio_oferta=Decimal(str(prod_data['precio_oferta'])) if prod_data.get('precio_oferta') else None,
                imagenes=prod_data.get('imagenes', []),
                activo=True
            )

            db.session.add(producto)
            contador_agregados += 1

            ganancia = prod_data['precio_final'] - prod_data['precio_proveedor']
            print(f"[OK] {prod_data['nombre']}")
            print(f"     Costo: ${prod_data['precio_proveedor']} | Venta: ${prod_data['precio_final']} | Ganancia: ${ganancia}")

        # Guardar todos los cambios
        try:
            db.session.commit()
            print("\n" + "="*60)
            print(f"RESUMEN:")
            print(f"  - Productos agregados: {contador_agregados}")
            print(f"  - Productos existentes (omitidos): {contador_existentes}")
            print(f"  - Total en catálogo: {contador_agregados + contador_existentes}")
            print("="*60 + "\n")
            print("[OK] Todos los productos han sido agregados exitosamente!")

        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] Error al guardar: {e}")

if __name__ == '__main__':
    agregar_productos()
