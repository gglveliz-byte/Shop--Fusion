# 📦 Guía de Instalación Rápida - Shop Fusion

## Opción 1: Instalación Automática (Windows)

### 1. Doble clic en `run.bat`

El script automáticamente:
- ✅ Crea el entorno virtual (si no existe)
- ✅ Instala las dependencias
- ✅ Inicia la aplicación

### 2. Inicializar la base de datos (solo la primera vez)

Abre otra terminal y ejecuta:

```bash
venv\Scripts\activate
python init_db.py
```

### 3. Accede a la aplicación

Abre tu navegador en: `http://localhost:5000`

---

## Opción 2: Instalación Manual

### Paso 1: Crear entorno virtual

```bash
python -m venv venv
```

### Paso 2: Activar entorno virtual

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### Paso 3: Instalar dependencias

```bash
pip install -r requirements.txt
```

### Paso 4: Inicializar base de datos

```bash
python init_db.py
```

Esto creará:
- ✅ Todas las tablas
- ✅ Admin por defecto: `admin` / `admin123`
- ✅ Afiliado de ejemplo: `juan@email.com` / `afiliado123`
- ✅ Productos de ejemplo

### Paso 5: Configurar WhatsApp (IMPORTANTE)

Edita el archivo `config.py` línea 27:

```python
WHATSAPP_NUMBER = '593999999999'  # Cambia por tu número
```

### Paso 6: Ejecutar la aplicación

```bash
python app.py
```

### Paso 7: Acceder

Abre tu navegador en: `http://localhost:5000`

---

## 🔐 Credenciales por Defecto

### Administrador
- **URL:** `http://localhost:5000/auth/admin/login`
- **Usuario:** `admin`
- **Contraseña:** `admin123`

⚠️ **IMPORTANTE:** Cambia la contraseña después del primer login

### Afiliado de Ejemplo
- **URL:** `http://localhost:5000/auth/afiliado/login`
- **Email:** `juan@email.com`
- **Contraseña:** `afiliado123`
- **Código:** `AFI001`

---

## ✅ Verificación de Instalación

### 1. Verificar que la aplicación esté corriendo

Si ves esto en la terminal:
```
* Running on http://127.0.0.1:5000
* Restarting with stat
```

¡Todo está bien! ✅

### 2. Probar el acceso

Visita: `http://localhost:5000`

Deberías ver la página principal de la tienda con productos de ejemplo.

### 3. Probar login de admin

1. Ve a: `http://localhost:5000/auth/admin/login`
2. Ingresa: `admin` / `admin123`
3. Deberías ver el dashboard del administrador

---

## 🐛 Solución de Problemas

### Error: "No module named 'flask'"

**Solución:** Asegúrate de tener el entorno virtual activado

```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# Luego instala las dependencias
pip install -r requirements.txt
```

### Error: "Could not connect to database"

**Solución:** Verifica que el `DATABASE_URL` en `.env` sea correcto

### Error: "Permission denied" al subir imágenes

**Solución:** Verifica que la carpeta `static/uploads/` tenga permisos de escritura

```bash
# Linux/Mac
chmod 755 static/uploads/
```

### La aplicación no inicia

**Solución:** Verifica que el puerto 5000 no esté en uso

```bash
# Windows
netstat -ano | findstr :5000

# Linux/Mac
lsof -i :5000
```

Si está en uso, puedes cambiar el puerto editando `app.py`:

```python
if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Cambia el puerto
```

---

## 📱 Configuración de WhatsApp

### Obtener tu número de WhatsApp Business

1. Formato: `[código país][número sin espacios ni guiones]`
2. Ejemplo Ecuador: `593999999999`
3. Ejemplo México: `525512345678`

### Configurar en el sistema

Edita `config.py`:

```python
WHATSAPP_NUMBER = '593999999999'  # Tu número aquí
```

---

## 🚀 Próximos Pasos

Una vez instalado:

1. ✅ Cambia la contraseña del admin
2. ✅ Configura tu número de WhatsApp
3. ✅ Elimina los productos de ejemplo
4. ✅ Crea tus productos reales
5. ✅ Crea tus afiliados
6. ✅ ¡Comienza a vender!

---

## 📚 Documentación Adicional

- [README.md](README.md) - Documentación completa
- [SRS](SRS.md) - Especificaciones del sistema
- [config.py](config.py) - Configuración

---

## 💬 Soporte

Si tienes problemas con la instalación:

1. Verifica que Python 3.8+ esté instalado: `python --version`
2. Verifica que pip funcione: `pip --version`
3. Lee los mensajes de error completos
4. Revisa la sección de troubleshooting

---

**¡Listo para empezar! 🎉**
