
(function () {
    'use strict';

    const VISITAS_URL = '/porteria/visitas-hoy/';
    const POLLING_MS = 30000;

    const tablaVisitasHoyBody = document.getElementById('tablaVisitasHoyBody');

    if (!tablaVisitasHoyBody) return;

    function escapeHTML(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    async function cargarVisitasHoy() {
        try {
            const resp = await fetch(VISITAS_URL);
            const data = await resp.json();

            if (!data.success) return;

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

    cargarVisitasHoy();
    setInterval(cargarVisitasHoy, POLLING_MS);
})();
