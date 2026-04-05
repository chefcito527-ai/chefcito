# Refri-IA

Proyecto Flask que genera recetas con Google Gemini usando ingredientes del usuario.

## Preparación local

1. Clona el repositorio.

2. Crea y activa un entorno virtual:

   **En Windows (PowerShell):**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

   **En Linux/macOS (bash/zsh):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Instala dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Crea un archivo `.env` basado en `.env.example` y ajusta:

   - `DATABASE_URL`
   - `SECRET_KEY`

5. Ejecuta la app localmente:

   ```bash
   python app.py
   ```

## Despliegue en Render

1. Conecta tu repositorio de GitHub a Render.

2. Crea una nueva Web Service con las siguientes configuraciones:

   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:application --bind 0.0.0.0:$PORT`
   - **Environment Variables**:
     - `DATABASE_URL`: Tu URL de PostgreSQL
     - `SECRET_KEY`: Una clave secreta segura
     - `PYTHON_VERSION`: 3.11.0 (o la versión que uses)

3. Render detectará automáticamente el puerto desde `$PORT`.

4. Tu app estará disponible en la URL proporcionada por Render.

## Notas importantes

- `app.py` ya exporta `application = app` para compatibilidad con WSGI.
- El proyecto usa `psycopg2-binary`, `bcrypt`, `google-genai` y `Flask 3.x`.
- La app espera que el usuario ingrese su propia API Key de Google Gemini desde el navegador.
- Las consultas SQL usan parámetros (`%s`), lo que protege contra inyección SQL.
- Se agregó protección CSRF en los formularios de login/registro y en la API JSON.

## Archivos clave

- `app.py` — aplicación Flask
- `wsgi.py` — punto de entrada WSGI
- `requirements.txt` — dependencias Python
- `database/schema.sql` — esquema de base de datos
- `templates/` — vistas HTML
- `static/` — CSS y JavaScript
