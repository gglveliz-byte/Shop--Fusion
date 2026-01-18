# ⚠️ SOLUCIÓN AL ERROR DE BASE DE DATOS

## Problema
La base de datos PostgreSQL de Render tiene un problema con el esquema `public`.

## Solución 1: Usar SQLite Local (RECOMENDADO para pruebas)

1. **Renombra tu `.env` actual:**
   ```
   .env  →  .env.postgresql (guárdalo para producción)
   ```

2. **Renombra `.env.local`:**
   ```
   .env.local  →  .env
   ```

3. **Ejecuta de nuevo:**
   ```bash
   python init_db.py
   ```

Esto usará SQLite en lugar de PostgreSQL. Funciona perfectamente para desarrollo y pruebas.

## Solución 2: Crear el esquema en PostgreSQL

Si necesitas usar PostgreSQL, necesitas:

1. **Conectarte a la base de datos y crear el esquema:**
   ```sql
   CREATE SCHEMA IF NOT EXISTS public;
   GRANT ALL ON SCHEMA public TO shopfusion_user;
   ```

2. **O contactar al administrador de Render** para que te de permisos completos.

## ¿Cuál usar?

- **Para desarrollo local:** SQLite (`.env.local`)
- **Para producción:** PostgreSQL (`.env`)

---

## Para continuar AHORA:

1. Renombra los archivos:
   ```
   .env → .env.postgresql
   .env.local → .env
   ```

2. Ejecuta:
   ```bash
   python init_db.py
   python app.py
   ```

¡Listo! El sistema funcionará perfectamente con SQLite local.
