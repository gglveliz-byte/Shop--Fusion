@echo off
echo ========================================
echo   SHOP FUSION - Sistema de Afiliados
echo ========================================
echo.

REM Verificar si existe el entorno virtual
if not exist "venv\" (
    echo [!] No se encontro el entorno virtual
    echo [*] Creando entorno virtual...
    python -m venv venv
    echo [OK] Entorno virtual creado
    echo.
)

REM Activar entorno virtual
echo [*] Activando entorno virtual...
call venv\Scripts\activate

REM Instalar/Actualizar dependencias
echo [*] Instalando dependencias...
pip install -r requirements.txt --quiet

echo.
echo ========================================
echo   Iniciando aplicacion...
echo ========================================
echo.
echo Accede a: http://localhost:5000
echo.
echo Presiona Ctrl+C para detener
echo.

REM Ejecutar la aplicación
python app.py

pause
