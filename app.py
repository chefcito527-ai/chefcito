import os
import json
import re
import secrets
import logging
import bcrypt
import psycopg2
import psycopg2.extras
from psycopg2 import pool as pg_pool
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from dotenv import load_dotenv
from google import genai

load_dotenv()

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
_secret = os.getenv("SECRET_KEY")
if not _secret:
    logging.warning("SECRET_KEY no definida en .env. Sesiones no persistirán entre reinicios.")
    _secret = secrets.token_hex(32)
app.secret_key = _secret
app.config.update({
    "SESSION_COOKIE_HTTPONLY": True,
    "SESSION_COOKIE_SAMESITE": "Lax",
})
if os.getenv("PYTHONANYWHERE_DOMAIN"):
    app.config["SESSION_COOKIE_SECURE"] = True


# ─── Neon / PostgreSQL Connection Pool ──────────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("ERROR: DATABASE_URL no definida en .env")

# Pool de conexiones: mínimo 1, máximo 10 conexiones simultáneas
_db_pool: pg_pool.ThreadedConnectionPool = None

def get_pool() -> pg_pool.ThreadedConnectionPool:
    global _db_pool
    if _db_pool is None or _db_pool.closed:
        _db_pool = pg_pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=DATABASE_URL,
        )
        logging.info("Pool de conexiones a Neon inicializado.")
    return _db_pool


def get_db():
    """Retorna una conexión del pool. Usar siempre dentro de un bloque try/finally con release_db()."""
    return get_pool().getconn()


def release_db(conn):
    """Devuelve la conexión al pool."""
    try:
        get_pool().putconn(conn)
    except Exception as e:
        logging.error("Error al devolver conexión al pool: %s", e)


# Todas las consultas SQL se realizan con parámetros (%s) y never con concatenación directa
# de valores de usuario. Esto protege contra inyección SQL al ejecutar consultas con psycopg2.

# ─── Helpers ─────────────────────────────────────────────────

def login_required(view):
    """Decorador para proteger rutas que requieren sesión."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def hash_password(plain: str) -> str:
    """Genera un hash bcrypt de la contraseña en texto plano."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(plain: str, hashed: str) -> bool:
    """Verifica si la contraseña plana coincide con el hash almacenado."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _get_csrf_token() -> str:
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    return session["_csrf_token"]


def generate_csrf_token() -> str:
    """Genera o retorna un token CSRF para incluir en formularios y meta tags."""
    return _get_csrf_token()


def validate_csrf_token(token: str | None) -> bool:
    expected = session.get("_csrf_token")
    if not expected or not token:
        return False
    return secrets.compare_digest(expected, token)


def csrf_protect(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if request.method == "GET":
            return view(*args, **kwargs)

        token = request.headers.get("X-CSRF-Token", "") if request.is_json else request.form.get("csrf_token", "")
        if not validate_csrf_token(token):
            if request.is_json:
                return jsonify({"error": "Token CSRF ausente o inválido."}), 400
            template_name = "registro.html" if request.endpoint == "registro" else "login.html"
            return render_template(template_name, error="Token CSRF ausente o inválido."), 400

        return view(*args, **kwargs)
    return wrapped


app.jinja_env.globals["csrf_token"] = generate_csrf_token


def obtener_receta_ia(ingredientes_usuario: str, personas: int, api_key: str) -> dict:
    """Genera una receta con Google Gemini. La api_key la provee el usuario."""
    client = genai.Client(api_key=api_key)

    prompt = f"""Eres ChefBot, un chef profesional con 20 años de experiencia en cocina
        internacional y creativa.
        <tarea>
            Genera UNA receta completa, deliciosa y realista usando los ingredientes disponibles
            del usuario.
            Adapta las cantidades exactamente para {personas} persona(s).
        </tarea>
        <ingredientes_disponibles>
            {ingredientes_usuario}
        </ingredientes_disponibles>
        <reglas_criticas>
            1. OUTPUT: JSON puro únicamente. Cero texto antes o después. Sin markdown.
                Sin ```json. Sin explicaciones.
            2. IDIOMA: Todo en español, incluyendo unidades de medida.
            3. INGREDIENTES: Usa al menos el 90% de los ingredientes dados. 
                Puedes asumir sal, pimienta y aceite como básicos de cocina.
            4. CANTIDADES: Todas las cantidades deben estar ajustadas para exactamente 
                {personas} persona(s).
            5. DIFICULTAD: Solo puede ser "Fácil", "Medio" o "Difícil". Sin variaciones.
            6. PASOS: Mínimo 5 pasos. Cada paso debe empezar con "Paso N:" y ser accionable
                y específico.
            7. TIEMPO: Indica el tiempo total (preparación + cocción).
            8. CREATIVIDAD: El nombre del plato debe ser atractivo y descriptivo, no genérico.
        </reglas_criticas>
        <formato_json_requerido>
            {{
                "titulo_plato": "Nombre creativo y descriptivo del plato",
                "lista_ingredientes": [
                    "cantidad + unidad + ingrediente + forma de corte/preparación",
                    "ejemplo: 300g de pechuga de pollo cortada en cubos medianos"
                ],
                "pasos_preparacion": [
                    "Paso 1: acción específica y clara",
                    "Paso 2: acción específica y clara"
                ],
                "tiempo_estimado": "X minutos (Y min preparación + Z min cocción)",
                "nivel_dificultad": "Fácil|Medio|Difícil"
            }}
        </formato_json_requerido>
        Recuerda: responde SOLO con el JSON. Ni una palabra fuera de las llaves."""

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-preview",
        contents=prompt,
        config={
            "temperature": 0.7,
            "top_p": 0.9,
            "max_output_tokens": 1500,
        }
    )
    texto_respuesta = response.text.strip()
    texto_respuesta = re.sub(r"```(?:json)?\s*", "", texto_respuesta).strip()
    texto_respuesta = re.sub(r"```\s*$", "", texto_respuesta).strip()

    match = re.search(r"\{.*\}", texto_respuesta, re.DOTALL)
    if match:
        texto_respuesta = match.group(0)

    return json.loads(texto_respuesta)

# ─── Rutas Públicas ──────────────────────────────────────────

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/terminos")
def terminos():
    return render_template("terminos.html")

@app.route("/privacidad")
def privacidad():
    return render_template("privacidad.html")

@app.route("/api-policy")
def api_policy():
    return render_template("api_policy.html")

@app.route("/login", methods=["GET", "POST"])
@csrf_protect
def login():
    if "user_id" in session:
        return redirect(url_for("recetas"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not email or not password:
            return render_template("login.html", error="Por favor completa todos los campos.", email_value=email)

        conn = None
        try:
            conn = get_db()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT id, email, nombre, password_hash FROM users WHERE email = %s", (email,))
                user = cur.fetchone()

            if not user or not check_password(password, user["password_hash"]):
                return render_template("login.html", error="Correo o contraseña incorrectos.", email_value=email)

            session["user_id"]    = str(user["id"])
            session["user_email"] = user["email"]
            session["user_name"]  = user["nombre"]
            return redirect(url_for("recetas"))

        except Exception as e:
            logging.error("Error en /login: %s", e)
            return render_template("login.html", error="Error al iniciar sesión. Intenta de nuevo.", email_value=email)
        finally:
            if conn:
                release_db(conn)

    return render_template("login.html")


@app.route("/registro", methods=["GET", "POST"])
@csrf_protect
def registro():
    if "user_id" in session:
        return redirect(url_for("recetas"))

    if request.method == "POST":
        nombre    = request.form.get("nombre", "").strip()
        email     = request.form.get("email", "").strip().lower()
        password  = request.form.get("password", "").strip()
        password2 = request.form.get("password2", "").strip()
        terminos  = request.form.get("terminos")

        # Validaciones locales
        if not nombre or not email or not password or not password2:
            return render_template("registro.html", error="Por favor completa todos los campos.",
                                   nombre_value=nombre, email_value=email)

        if not terminos:
            return render_template("registro.html", error="Debes aceptar los Términos y Condiciones y Política de Privacidad para continuar.",
                                   nombre_value=nombre, email_value=email)

        if password != password2:
            return render_template("registro.html", error="Las contraseñas no coinciden.",
                                   nombre_value=nombre, email_value=email)

        if len(password) < 6:
            return render_template("registro.html", error="La contraseña debe tener al menos 6 caracteres.",
                                   nombre_value=nombre, email_value=email)

        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            return render_template("registro.html", error="El formato del correo electrónico no es válido.",
                                   nombre_value=nombre, email_value=email)

        conn = None
        try:
            conn = get_db()
            # Verificar si el email ya existe
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                if cur.fetchone():
                    return render_template("registro.html",
                                           error="Este correo ya está registrado. ¿Quieres iniciar sesión?",
                                           nombre_value=nombre, email_value=email)

            # Crear el usuario
            password_hash = hash_password(password)
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "INSERT INTO users (email, nombre, password_hash) VALUES (%s, %s, %s) RETURNING id, email, nombre",
                    (email, nombre, password_hash)
                )
                new_user = cur.fetchone()
                conn.commit()

            session["user_id"]    = str(new_user["id"])
            session["user_email"] = new_user["email"]
            session["user_name"]  = new_user["nombre"]
            return redirect(url_for("recetas"))

        except Exception as e:
            if conn:
                conn.rollback()
            logging.error("Error en /registro: %s", e)
            msg = str(e)
            if "unique" in msg.lower() or "duplicate" in msg.lower():
                msg = "Este correo ya está registrado. ¿Quieres iniciar sesión?"
            else:
                msg = "No se pudo crear la cuenta. Inténtalo de nuevo."
            return render_template("registro.html", error=msg, nombre_value=nombre, email_value=email)
        finally:
            if conn:
                release_db(conn)

    return render_template("registro.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


# ─── Rutas Protegidas ────────────────────────────────────────

@app.route("/recetas")
@login_required
def recetas():
    return render_template("generador.html", user_name=session.get("user_name"))


@app.route("/mis-recetas")
@login_required
def mis_recetas():
    """Lista todas las recetas generadas por el usuario autenticado."""
    user_id = session.get("user_id")
    conn = None
    try:
        conn = get_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, titulo_plato, lista_ingredientes, pasos_preparacion,
                       tiempo_estimado, nivel_dificultad, guardada, created_at
                FROM recetas
                WHERE user_id = %s
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            recetas_data = cur.fetchall()

        # psycopg2 con RealDictCursor devuelve JSONB ya deserializado como listas,
        # pero por seguridad normalizamos igualmente.
        recetas_list = []
        for r in recetas_data:
            row = dict(r)
            if isinstance(row.get("lista_ingredientes"), str):
                try:
                    row["lista_ingredientes"] = json.loads(row["lista_ingredientes"])
                except (json.JSONDecodeError, TypeError):
                    row["lista_ingredientes"] = []
            if isinstance(row.get("pasos_preparacion"), str):
                try:
                    row["pasos_preparacion"] = json.loads(row["pasos_preparacion"])
                except (json.JSONDecodeError, TypeError):
                    row["pasos_preparacion"] = []
            recetas_list.append(row)

        return render_template("mis_recetas.html",
                               recetas=recetas_list,
                               user_name=session.get("user_name"))
    except Exception as e:
        logging.error("Error al cargar mis_recetas: %s", e)
        return render_template("mis_recetas.html",
                               recetas=[],
                               user_name=session.get("user_name"))
    finally:
        if conn:
            release_db(conn)


@app.route("/receta/<uuid:receta_id>/guardar", methods=["POST"])
@login_required
@csrf_protect
def guardar_receta(receta_id):
    """Alterna el estado 'guardada' de una receta. Solo el dueño puede modificarla."""
    user_id = session.get("user_id")
    datos = request.get_json(silent=True)
    if datos is None:
        return jsonify({"error": "Petición inválida."}), 400

    nueva_guardada = bool(datos.get("guardada", False))

    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            # Verificar ownership antes de modificar (seguridad: WHERE user_id)
            cur.execute(
                "SELECT id FROM recetas WHERE id = %s AND user_id = %s",
                (str(receta_id), user_id)
            )
            if not cur.fetchone():
                return jsonify({"error": "No autorizado."}), 403

            cur.execute(
                "UPDATE recetas SET guardada = %s WHERE id = %s AND user_id = %s",
                (nueva_guardada, str(receta_id), user_id)
            )
            conn.commit()

        return jsonify({"ok": True, "guardada": nueva_guardada})
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error("Error al guardar receta %s: %s", receta_id, e)
        return jsonify({"error": "Error al actualizar la receta."}), 500
    finally:
        if conn:
            release_db(conn)


@app.route("/generar_receta", methods=["POST"])
@login_required
@csrf_protect
def generar_receta():
    datos = request.get_json(silent=True)
    if not datos:
        return jsonify({"error": "Petición inválida. Se esperaba JSON."}), 400

    ingredientes_usuario = datos.get("ingredientes", "").strip()
    api_key = datos.get("api_key", "").strip()

    try:
        personas = int(datos.get("personas", 1))
    except (ValueError, TypeError):
        personas = 1

    if not api_key:
        return jsonify({
            "error": "api_key_missing",
            "mensaje": "Necesitas configurar tu API Key de Google Gemini para usar esta función."
        }), 400

    personas = max(1, min(50, personas))

    if not ingredientes_usuario:
        return jsonify({"error": "Por favor ingresa al menos un ingrediente."}), 400

    if len(ingredientes_usuario) > 2000:
        return jsonify({"error": "La lista de ingredientes es demasiado larga (máx. 2000 caracteres)."}), 400

    user_id = session.get("user_id")

    try:
        receta = obtener_receta_ia(ingredientes_usuario, personas, api_key)
    except json.JSONDecodeError as e:
        logging.error("JSONDecodeError al parsear respuesta de IA: %s", e)
        return jsonify({"error": "La IA no pudo generar una receta válida. Intenta de nuevo."}), 500
    except Exception as e:
        msg = str(e)
        logging.error("Error en Gemini API: %s", msg)
        if any(k in msg for k in ["API_KEY", "INVALID_ARGUMENT", "quota", "billing", "PERMISSION_DENIED", "404", "NOT_FOUND"]):
            return jsonify({"error": msg}), 500
        return jsonify({"error": "Error al contactar la IA. Verifica tu API Key e inténtalo de nuevo."}), 500

    conn = None
    try:
        conn = get_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # 1. Insertar solicitud
            cur.execute(
                "INSERT INTO solicitudes (user_id, ingredientes, personas) VALUES (%s, %s, %s) RETURNING id",
                (user_id, ingredientes_usuario, personas)
            )
            solicitud_id = cur.fetchone()["id"]

            # 2. Insertar receta generada
            cur.execute(
                """
                INSERT INTO recetas
                  (solicitud_id, user_id, titulo_plato, lista_ingredientes,
                   pasos_preparacion, tiempo_estimado, nivel_dificultad, guardada)
                VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s)
                """,
                (
                    str(solicitud_id),
                    user_id,
                    receta["titulo_plato"],
                    json.dumps(receta["lista_ingredientes"], ensure_ascii=False),
                    json.dumps(receta["pasos_preparacion"], ensure_ascii=False),
                    receta.get("tiempo_estimado"),
                    receta.get("nivel_dificultad"),
                    True,  # guardada por defecto al generarla
                )
            )
            conn.commit()

        return jsonify(receta)

    except Exception as e:
        if conn:
            conn.rollback()
        logging.error("Error al guardar receta en Neon: %s", e)
        # La receta fue generada correctamente, igual la devolvemos aunque no se guardara
        return jsonify({**receta, "_warning": "Receta generada pero no se pudo guardar en la base de datos."})
    finally:
        if conn:
            release_db(conn)


application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
