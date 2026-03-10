/**
 * Selector de visitas para control de acceso
 */
(function () {
    'use strict';

    const VISITAS_URL = '/porteria/visitas-hoy/';
    const POLLING_MS = 30000;

    const tablaVisitasHoyBody = document.getElementById('tablaVisitasHoyBody');
    const visitasInternasEl = document.getElementById('visitasInternasHoy');
    const visitasExternasEl = document.getElementById('visitasExternasHoy');
    const visitasTotalEl = document.getElementById('visitasTotalHoy');
    const clockEl = document.getElementById('porteriaClock');
    const dateEl = document.getElementById('porteriaDate');

    if (!tablaVisitasHoyBody) return;

    function escapeHTML(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function actualizarReloj() {
        if (!clockEl || !dateEl) return;

        const now = new Date();
        clockEl.textContent = now.toLocaleTimeString('es-CO', { hour12: false });

        const dias = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
        const meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
        dateEl.textContent = `${dias[now.getDay()]}, ${now.getDate()} ${meses[now.getMonth()]} ${now.getFullYear()}`;
    }

    async function cargarVisitasHoy() {
        try {
            const resp = await fetch(VISITAS_URL);
            const data = await resp.json();

            if (!data.success) return;

            const totales = data.totales || {};
            if (visitasInternasEl) visitasInternasEl.textContent = totales.internas || 0;
            if (visitasExternasEl) visitasExternasEl.textContent = totales.externas || 0;
            if (visitasTotalEl) visitasTotalEl.textContent = totales.total || 0;

            const visitas = data.visitas || [];
            if (visitas.length === 0) {
                tablaVisitasHoyBody.innerHTML = `
          <tr class="empty-row">
            <td colspan="6">
              <i class="ri-calendar-line"></i> Sin visitas confirmadas para hoy
            </td>
          </tr>`;
                return;
            }

            tablaVisitasHoyBody.innerHTML = visitas.map((v) => `
        <tr>
          <td><span class="badge-${escapeHTML(v.tipo)}">${escapeHTML(v.tipo_label)}</span></td>
          <td>${escapeHTML(v.nombre)}</td>
          <td>${escapeHTML(v.responsable)}</td>
          <td>${escapeHTML(v.horario)}</td>
          <td><strong>${escapeHTML(v.asistentes_aprobados)}</strong></td>
          <td><a class="btn-open-visita" href="${escapeHTML(v.url_porteria)}">Abrir control</a></td>
        </tr>`).join('');
        } catch (err) {
            console.error('Error cargando visitas de hoy:', err);
        }
    }

    actualizarReloj();
    setInterval(actualizarReloj, 1000);

    cargarVisitasHoy();
    setInterval(cargarVisitasHoy, POLLING_MS);
})();
