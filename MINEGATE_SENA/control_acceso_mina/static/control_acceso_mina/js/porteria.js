/**
 * Control de Acceso por visita — escaneo y registros individuales
 */
(function () {
    'use strict';

    const app = document.getElementById('porteriaVisitaApp');
    if (!app) return;

    const REGISTRAR_URL = app.dataset.registrarUrl || '/porteria/registrar/';
    const DATOS_URL = app.dataset.datosUrl;
    const SELECTED_VISIT_TYPE = app.dataset.tipoVisita;
    const SELECTED_VISIT_ID = parseInt(app.dataset.visitaId || '0', 10);

    const POLLING_MS = 30000;

    const docInput = document.getElementById('porteriaDocInput');
    const btnRegistrar = document.getElementById('btnRegistrar');
    const btnCamara = document.getElementById('btnCamara');

    const qrModalOverlay = document.getElementById('qrModalOverlay');
    const btnCerrarQR = document.getElementById('btnCerrarQR');
    const qrReaderContainer = document.getElementById('qrReaderContainer');

    const feedback = document.getElementById('porteriaFeedback');
    const feedbackIcon = document.getElementById('feedbackIcon');
    const feedbackName = document.getElementById('feedbackName');
    const feedbackCat = document.getElementById('feedbackCategory');
    const feedbackType = document.getElementById('feedbackType');

    const tablaIngresosBody = document.getElementById('tablaIngresosBody');
    const tablaSalidasBody = document.getElementById('tablaSalidasBody');
    const tablaAsistentesBody = document.getElementById('tablaAsistentesBody');
    const personasEl = document.getElementById('personasEnMina');
    const entradasEl = document.getElementById('entradasHoy');
    const salidasEl = document.getElementById('salidasHoy');
    const clockEl = document.getElementById('porteriaClock');

    if (!docInput || !DATOS_URL || !SELECTED_VISIT_TYPE || !SELECTED_VISIT_ID) return;

    let html5QrCode = null;
    let isOpeningCamera = false;
    let isClosingCamera = false;
    let isProcessingQr = false;

    function getCookie(name) {
        const parts = ('; ' + document.cookie).split('; ' + name + '=');
        if (parts.length === 2) return parts.pop().split(';').shift();
        return '';
    }

    function escapeHTML(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function actualizarReloj() {
        if (!clockEl) return;
        const now = new Date();
        clockEl.textContent = now.toLocaleTimeString('es-CO', { hour12: false });
    }

    function mostrarFeedback(data) {
        feedback.style.display = 'block';
        feedback.className = 'porteria-feedback';

        if (data.tipo === 'ENTRADA') {
            feedback.classList.add('feedback-entrada');
            feedbackIcon.innerHTML = '<i class="ri-login-box-line"></i>';
            feedbackType.textContent = '↓ ENTRADA';
        } else {
            feedback.classList.add('feedback-salida');
            feedbackIcon.innerHTML = '<i class="ri-logout-box-line"></i>';
            feedbackType.textContent = '↑ SALIDA';
        }

        feedbackName.textContent = data.nombre_completo;
        feedbackCat.textContent = data.categoria;

        feedback.style.animation = 'none';
        feedback.offsetHeight;
        feedback.style.animation = '';

        setTimeout(() => {
            feedback.style.display = 'none';
        }, 6000);
    }

    function mostrarFeedbackError(msg) {
        feedback.style.display = 'block';
        feedback.className = 'porteria-feedback feedback-error';
        feedbackIcon.innerHTML = '<i class="ri-close-circle-line"></i>';
        feedbackName.textContent = msg;
        feedbackCat.textContent = '';
        feedbackType.textContent = 'ERROR';

        feedback.style.animation = 'none';
        feedback.offsetHeight;
        feedback.style.animation = '';

        setTimeout(() => {
            feedback.style.display = 'none';
        }, 6000);
    }

    function extraerDocumentoQR(decodedText) {
        if (!decodedText) return '';

        if (decodedText.includes('|')) {
            const parts = decodedText.split('|');
            if (parts.length >= 3 && parts[2].trim()) {
                return parts[2].trim();
            }
        }

        const soloDocumento = decodedText.match(/\b\d{5,}\b/);
        if (soloDocumento) {
            return soloDocumento[0].trim();
        }

        return decodedText.trim();
    }

    async function registrar(manualDoc, qrData = '') {
        const doc = manualDoc || docInput.value.trim();
        if (!doc) {
            if (!manualDoc) docInput.focus();
            return;
        }

        docInput.disabled = true;
        btnRegistrar.disabled = true;
        btnCamara.disabled = true;
        const originalBtnHTML = btnRegistrar.innerHTML;
        btnRegistrar.innerHTML = '<span class="scanner-loading"></span>';

        try {
            const resp = await fetch(REGISTRAR_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({
                    documento: doc,
                    qr_data: qrData,
                    selected_visit_type: SELECTED_VISIT_TYPE,
                    selected_visit_id: SELECTED_VISIT_ID,
                }),
            });

            const data = await resp.json();
            if (data.success) {
                mostrarFeedback(data.data);
                await cargarDatosVisita();
            } else {
                mostrarFeedbackError(data.error || 'Documento no autorizado para esta visita.');
            }
        } catch (err) {
            mostrarFeedbackError('Error de conexión con el servidor.');
            console.error(err);
        } finally {
            if (!manualDoc) docInput.value = '';
            docInput.disabled = false;
            btnRegistrar.disabled = false;
            btnCamara.disabled = false;
            btnRegistrar.innerHTML = originalBtnHTML;
            docInput.focus();
        }
    }

    async function abrirCamara() {
        if (isOpeningCamera || !qrModalOverlay || !qrReaderContainer) return;
        if (typeof Html5Qrcode === 'undefined') {
            mostrarFeedbackError('No se cargó la librería de cámara QR.');
            return;
        }

        if (html5QrCode && html5QrCode.isScanning) return;

        isOpeningCamera = true;
        isProcessingQr = false;
        qrModalOverlay.style.display = 'flex';

        if (!html5QrCode) {
            html5QrCode = new Html5Qrcode('qrReaderContainer');
        }

        const config = { fps: 10, qrbox: { width: 250, height: 250 } };

        try {
            await html5QrCode.start(
                { facingMode: 'environment' },
                config,
                onScanSuccess,
                () => { }
            );
        } catch (err) {
            try {
                const cameras = await Html5Qrcode.getCameras();
                if (!cameras || cameras.length === 0) {
                    throw err;
                }

                await html5QrCode.start(
                    { deviceId: { exact: cameras[0].id } },
                    config,
                    onScanSuccess,
                    () => { }
                );
            } catch (fallbackErr) {
                console.error('Error iniciando cámara:', fallbackErr);
                mostrarFeedbackError('No se pudo acceder a la cámara. Verifique permisos del navegador.');
                await cerrarCamara();
            }
        } finally {
            isOpeningCamera = false;
        }
    }

    async function cerrarCamara() {
        if (isClosingCamera) return;
        isClosingCamera = true;

        try {
            if (html5QrCode && html5QrCode.isScanning) {
                await html5QrCode.stop();
                await html5QrCode.clear();
            }
        } catch (err) {
            console.error('Error deteniendo cámara:', err);
        } finally {
            if (qrModalOverlay) {
                qrModalOverlay.style.display = 'none';
            }
            isClosingCamera = false;
        }
    }

    async function onScanSuccess(decodedText) {
        if (isProcessingQr) return;
        isProcessingQr = true;

        const documento = extraerDocumentoQR(decodedText);
        await cerrarCamara();
        registrar(documento, decodedText);
    }

    async function cargarDatosVisita() {
        try {
            const resp = await fetch(DATOS_URL);
            const data = await resp.json();

            if (!data.success) {
                mostrarFeedbackError(data.error || 'No fue posible cargar los datos de la visita.');
                return;
            }

            if (personasEl) personasEl.textContent = data.personas_en_mina || 0;
            if (entradasEl) entradasEl.textContent = data.entradas_hoy || 0;
            if (salidasEl) salidasEl.textContent = data.salidas_hoy || 0;

            const asistentes = data.asistentes_aprobados || [];
            if (asistentes.length === 0) {
                tablaAsistentesBody.innerHTML = `
          <tr class="empty-row">
            <td colspan="2"><i class="ri-inbox-line"></i> Sin asistentes aprobados</td>
          </tr>`;
            } else {
                tablaAsistentesBody.innerHTML = asistentes.map((a) => `
          <tr>
            <td>${escapeHTML(a.documento)}</td>
            <td>${escapeHTML(a.nombre_completo)}</td>
          </tr>`).join('');
            }

                        const personasDentro = data.personas_dentro || [];
                        if (personasDentro.length === 0) {
                                tablaIngresosBody.innerHTML = `
                    <tr class="empty-row">
                        <td colspan="5"><i class="ri-inbox-line"></i> Sin personas dentro en esta visita</td>
                    </tr>`;
                        } else {
                                tablaIngresosBody.innerHTML = personasDentro.map((p, idx) => `
                    <tr class="${idx === 0 ? 'row-new' : ''}">
                        <td><strong>${idx + 1}</strong></td>
                        <td><strong>${escapeHTML(p.hora)}</strong></td>
                        <td>${escapeHTML(p.documento)}</td>
                        <td>${escapeHTML(p.nombre_completo)}</td>
                        <td>${escapeHTML(p.categoria)}</td>
                    </tr>`).join('');
                        }

                        const personasFuera = data.personas_fuera || [];
                        if (personasFuera.length === 0) {
                                tablaSalidasBody.innerHTML = `
                    <tr class="empty-row">
                        <td colspan="5"><i class="ri-inbox-line"></i> Sin personas fuera en esta visita</td>
                    </tr>`;
                        } else {
                                tablaSalidasBody.innerHTML = personasFuera.map((p, idx) => `
                    <tr class="${idx === 0 ? 'row-new' : ''}">
                        <td><strong>${idx + 1}</strong></td>
                        <td><strong>${escapeHTML(p.hora)}</strong></td>
                        <td>${escapeHTML(p.documento)}</td>
                        <td>${escapeHTML(p.nombre_completo)}</td>
                        <td>${escapeHTML(p.categoria)}</td>
                    </tr>`).join('');
                        }
        } catch (err) {
            console.error('Error cargando datos de visita:', err);
        }
    }

    btnRegistrar.addEventListener('click', () => registrar());
    btnCamara.addEventListener('click', abrirCamara);

    if (btnCerrarQR) {
        btnCerrarQR.addEventListener('click', cerrarCamara);
    }

    if (qrModalOverlay) {
        qrModalOverlay.addEventListener('click', (e) => {
            if (e.target === qrModalOverlay) cerrarCamara();
        });
    }

    docInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            registrar();
        }
    });

    document.addEventListener('click', function (e) {
        if (!e.target.closest('input, button, a, select, textarea, .qr-modal')) {
            docInput.focus();
        }
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && qrModalOverlay && qrModalOverlay.style.display === 'flex') {
            cerrarCamara();
        }
    });

    window.addEventListener('beforeunload', function () {
        if (html5QrCode && html5QrCode.isScanning) {
            html5QrCode.stop().catch(() => { });
        }
    });

    actualizarReloj();
    setInterval(actualizarReloj, 1000);
    cargarDatosVisita();
    setInterval(cargarDatosVisita, POLLING_MS);
})();
