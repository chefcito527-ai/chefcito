// ═══════════════════════════════════════════════════════════
//  Chefcito — app.js
//  Maneja: API Key (localStorage), generación de recetas, UI
// ═══════════════════════════════════════════════════════════

const LS_KEY = 'gemini_api_key';

document.addEventListener('DOMContentLoaded', () => {
    const inputIngredientes = document.getElementById('input-ingredientes');
    if (!inputIngredientes) return;

    // ── Refs generales ────────────────────────────────────
    const btnCocinar = document.getElementById('btn-cocinar');
    const btnNuevaReceta = document.getElementById('btn-nueva-receta');
    const btnLimpiar = document.getElementById('btn-limpiar');
    const textoBtnEl = document.getElementById('texto-btn');
    const estadoCarga = document.getElementById('estado-carga');
    const tarjetaReceta = document.getElementById('tarjeta-receta');
    const bannerError = document.getElementById('banner-error');
    const textoError = document.getElementById('texto-error');
    const btnErrorApikey = document.getElementById('btn-error-apikey');
    const tituloPlato = document.getElementById('titulo-plato');
    const etiquetaDificultad = document.querySelector('#etiqueta-dificultad span:last-child');
    const textoTiempo = document.getElementById('texto-tiempo');
    const listaIngredientes = document.getElementById('lista-ingredientes');
    const listaPasos = document.getElementById('lista-pasos');
    const bannerApikey = document.getElementById('banner-apikey');
    const labelApikeyEstado = document.getElementById('label-apikey-estado');

    // ── Refs modal API key ────────────────────────────────
    const modal = document.getElementById('modal-apikey');
    const inputApikey = document.getElementById('input-apikey');
    const btnGuardar = document.getElementById('btn-apikey-guardar');
    const btnCancelar = document.getElementById('btn-apikey-cancelar');
    const btnAbrirModal = document.getElementById('btn-abrir-modal');
    const btnAbrirModalBanner = document.getElementById('btn-abrir-modal-banner');
    const btnToggleKey = document.getElementById('btn-toggle-key');
    const iconShow = document.getElementById('icon-show');
    const iconHide = document.getElementById('icon-hide');
    const apikeyError = document.getElementById('apikey-error');
    const apikeyErrorText = document.getElementById('apikey-error-text');

    // ── Estilos inyectados desde el template ──────────────
    const S = window.RECIPE_STYLES || {};

    // ── Personas ──────────────────────────────────────────
    const spanPersonas = document.getElementById('input-personas');
    const btnMenos = document.getElementById('btn-menos');
    const btnMas = document.getElementById('btn-mas');
    let personas = 2;

    function actualizarPersonas(val) {
        personas = Math.max(1, Math.min(50, val));
        spanPersonas.textContent = personas;
        btnMenos.disabled = personas <= 1;
        btnMas.disabled = personas >= 50;
        btnMenos.style.opacity = personas <= 1 ? '0.35' : '1';
        btnMas.style.opacity = personas >= 50 ? '0.35' : '1';
    }

    if (btnMenos && btnMas) {
        btnMenos.addEventListener('click', () => actualizarPersonas(personas - 1));
        btnMas.addEventListener('click', () => actualizarPersonas(personas + 1));
        actualizarPersonas(2);
    }

    // ══════════════════════════════════════════════════════
    //  GESTIÓN DE API KEY
    // ══════════════════════════════════════════════════════

    function getApiKey() { return localStorage.getItem(LS_KEY) || ''; }
    function setApiKey(key) { localStorage.setItem(LS_KEY, key.trim()); }

    function actualizarEstadoApiKey() {
        const key = getApiKey();
        if (key) {
            const preview = key.length > 10
                ? key.substring(0, 6) + '••••' + key.slice(-4)
                : '••••••••';
            if (labelApikeyEstado) labelApikeyEstado.textContent = preview;
            if (bannerApikey) bannerApikey.style.display = 'none';
        } else {
            if (labelApikeyEstado) labelApikeyEstado.textContent = 'API Key';
            if (bannerApikey) bannerApikey.style.display = 'flex';
        }
    }

    function abrirModal() {
        inputApikey.value = getApiKey();
        ocultarApikeyError();
        modal.style.display = 'flex';
        setTimeout(() => inputApikey.focus(), 100);
    }

    function cerrarModal() {
        modal.style.display = 'none';
    }

    function mostrarApikeyError(msg) {
        apikeyErrorText.textContent = msg;
        apikeyError.style.display = 'flex';
    }

    function ocultarApikeyError() {
        apikeyError.style.display = 'none';
    }

    btnGuardar.addEventListener('click', () => {
        const val = inputApikey.value.trim();
        if (!val) {
            mostrarApikeyError('Ingresa tu API Key antes de guardar.');
            return;
        }
        if (!val.startsWith('AIza') || val.length < 20) {
            mostrarApikeyError('La clave no parece válida. Debe comenzar con "AIza" y tener al menos 20 caracteres.');
            return;
        }
        setApiKey(val);
        actualizarEstadoApiKey();
        cerrarModal();
    });

    btnCancelar.addEventListener('click', () => {
        if (!getApiKey()) {
            mostrarApikeyError('Necesitas una API Key para usar el generador de recetas.');
            return;
        }
        cerrarModal();
    });

    if (btnAbrirModal) btnAbrirModal.addEventListener('click', abrirModal);
    if (btnAbrirModalBanner) btnAbrirModalBanner.addEventListener('click', abrirModal);
    if (btnErrorApikey) btnErrorApikey.addEventListener('click', abrirModal);

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            if (!getApiKey()) return;
            cerrarModal();
        }
    });

    if (btnToggleKey) {
        btnToggleKey.addEventListener('click', () => {
            const isPassword = inputApikey.type === 'password';
            inputApikey.type = isPassword ? 'text' : 'password';
            iconShow.classList.toggle('hidden', isPassword);
            iconHide.classList.toggle('hidden', !isPassword);
        });
    }

    inputApikey.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') btnGuardar.click();
    });

    // ══════════════════════════════════════════════════════
    //  UI HELPERS
    // ══════════════════════════════════════════════════════

    function setCargando(activo) {
        btnCocinar.disabled = activo;
        textoBtnEl.textContent = activo ? 'Cocinando...' : 'Generar receta';
        if (activo) {
            estadoCarga.style.display = 'flex';
            tarjetaReceta.style.display = 'none';
        } else {
            estadoCarga.style.display = 'none';
        }
    }

    function mostrarError(mensaje, esApiKey = false) {
        textoError.textContent = mensaje;
        bannerError.style.display = 'flex';
        if (btnErrorApikey) {
            btnErrorApikey.style.display = esApiKey ? 'block' : 'none';
        }
    }

    function ocultarError() {
        bannerError.style.display = 'none';
        if (btnErrorApikey) btnErrorApikey.style.display = 'none';
    }

    function mostrarReceta(receta) {
        tituloPlato.textContent = receta.titulo_plato;
        if (etiquetaDificultad) etiquetaDificultad.textContent = receta.nivel_dificultad;
        textoTiempo.textContent = receta.tiempo_estimado;

        // ── Ingredientes ───────────────────────────────────
        listaIngredientes.innerHTML = '';
        receta.lista_ingredientes.forEach(function (item) {
            const li = document.createElement('li');
            if (S.ingredientItem) li.setAttribute('style', S.ingredientItem);

            const dot = document.createElement('span');
            if (S.ingredientDot) dot.setAttribute('style', S.ingredientDot);

            const text = document.createElement('span');
            text.textContent = item;

            li.appendChild(dot);
            li.appendChild(text);
            listaIngredientes.appendChild(li);
        });

        // ── Pasos ─────────────────────────────────────────
        listaPasos.innerHTML = '';
        receta.pasos_preparacion.forEach(function (paso, i) {
            const li = document.createElement('li');
            if (S.stepItem) li.setAttribute('style', S.stepItem);

            const numSpan = document.createElement('span');
            if (S.stepNum) numSpan.setAttribute('style', S.stepNum);
            numSpan.textContent = i + 1;

            const pasoSpan = document.createElement('span');
            if (S.stepText) pasoSpan.setAttribute('style', S.stepText);
            pasoSpan.textContent = paso;

            li.appendChild(numSpan);
            li.appendChild(pasoSpan);
            listaPasos.appendChild(li);
        });

        tarjetaReceta.style.display = 'block';
        setTimeout(() => {
            tarjetaReceta.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }

    // ══════════════════════════════════════════════════════
    //  GENERAR RECETA
    // ══════════════════════════════════════════════════════

    async function generarReceta() {
        const ingredientes_usuario = inputIngredientes.value.trim();

        if (!ingredientes_usuario) {
            mostrarError('Escribe al menos un ingrediente para que la IA haga su magia.');
            return;
        }

        const apiKey = getApiKey();
        if (!apiKey) {
            abrirModal();
            return;
        }

        ocultarError();
        setCargando(true);

        try {
            const respuesta = await fetch('/generar_receta', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content || ''
                },
                body: JSON.stringify({
                    ingredientes: ingredientes_usuario,
                    personas: personas,
                    api_key: apiKey
                })
            });

            const datos = await respuesta.json();

            if (respuesta.status === 401) {
                window.location.href = '/login';
                return;
            }

            if (!respuesta.ok && (datos.error === 'api_key_missing' || respuesta.status === 400)) {
                mostrarError(
                    datos.mensaje || 'Configura tu API Key de Google Gemini para continuar.',
                    true
                );
                return;
            }

            if (!respuesta.ok) {
                const msg = datos.error || 'Error del servidor';
                const esApiKeyError = msg.includes('API_KEY') || msg.includes('INVALID_ARGUMENT') ||
                    msg.includes('quota') || msg.includes('billing') || msg.includes('rate limit');
                throw { message: msg, esApiKey: esApiKeyError };
            }

            mostrarReceta(datos);

        } catch (error) {
            const msg = error.message || String(error);
            const esApiKey = error.esApiKey || msg.includes('quota') || msg.includes('billing') ||
                msg.includes('API') || msg.includes('rate limit');
            mostrarError(msg, esApiKey);
        } finally {
            setCargando(false);
        }
    }

    btnCocinar.addEventListener('click', generarReceta);

    btnNuevaReceta.addEventListener('click', function () {
        tarjetaReceta.style.display = 'none';
        inputIngredientes.value = '';
        inputIngredientes.focus();
    });

    btnLimpiar.addEventListener('click', function () {
        inputIngredientes.value = '';
        inputIngredientes.focus();
        ocultarError();
        tarjetaReceta.style.display = 'none';
    });

    inputIngredientes.addEventListener('keydown', function (evento) {
        if (evento.key === 'Enter' && (evento.ctrlKey || evento.metaKey)) {
            generarReceta();
        }
    });

    // ══════════════════════════════════════════════════════
    //  INIT
    // ══════════════════════════════════════════════════════
    actualizarEstadoApiKey();

    if (!getApiKey()) {
        setTimeout(abrirModal, 500);
    }
});