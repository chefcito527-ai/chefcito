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

## Despliegue en PythonAnywhere

1. Sube el proyecto a PythonAnywhere (por SFTP, Git o ZIP).
2. En el panel "Web" de PythonAnywhere, crea una nueva aplicación Flask con Python 3.11 o 3.12.
3. Configura el WSGI para usar el archivo `wsgi.py`:

```python
import sys
path = '/home/tu_usuario/path/al/proyecto'
if path not in sys.path:
    sys.path.insert(0, path)

from wsgi import application
```

4. En la pestaña "Environment variables" del sitio web, define:

- `DATABASE_URL` con la URL de tu base de datos PostgreSQL
- `SECRET_KEY` con una clave secreta segura

5. Asegúrate de que `python-dotenv` está instalado si mantienes un archivo `.env`, o usa variables de entorno directamente.

6. En la pestaña "Static files" de PythonAnywhere, apunta `/static/` al directorio `static/` de tu proyecto.

7. Recarga la aplicación desde el panel "Web".

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
