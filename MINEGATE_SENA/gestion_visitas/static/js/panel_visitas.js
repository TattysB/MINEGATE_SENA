function getCsrfToken() {
  const match = document.cookie.match(/(^|;)\s*csrftoken\s*=\s*([^;]+)/);
  return match ? match.pop() : '';
}

function addCsrfToFormData(formData) {
  const token = getCsrfToken();
  if (token) {
    formData.append('csrfmiddlewaretoken', token);
  }
}

let tipoVisitaActual = 'internas';

function cambiarTabVisita(tipo) {
  tipoVisitaActual = tipo;
  document.querySelectorAll('.tab-visita').forEach(tab => {
    if (tab.getAttribute('data-tipo') === tipo) {
      tab.style.background = '#8b5cf6';
      tab.style.color = 'white';
      tab.classList.add('active');
    } else {
      tab.style.background = '#e5e7eb';
      tab.style.color = '#374151';
      tab.classList.remove('active');
    }
  });
  cargarVisitas();
}

function cargarVisitas() {
  const estadoEl = document.getElementById('filtroEstadoVisita');
  const buscarEl = document.getElementById('buscarVisita');
  const tbody = document.getElementById('cuerpoTablaVisitas');

  if (!estadoEl || !buscarEl || !tbody) return;

  const estado = estadoEl.value;
  const buscar = buscarEl.value;

  tbody.innerHTML = `<tr><td colspan="8" style="padding: 40px; text-align: center; color: #6b7280;">
      <i class="ri-loader-4-line" style="font-size: 30px; animation: spin 1s linear infinite;"></i>
      <p>Cargando visitas...</p>
    </td></tr>`;

  fetch(`/gestion/api/visitas/?tipo=${tipoVisitaActual}&estado=${estado}&buscar=${encodeURIComponent(buscar)}`)
    .then(response => response.json())
    .then(data => {
      document.getElementById('statPendientes').textContent = data.stats.pendientes;
      document.getElementById('statAprobadas').textContent = data.stats.aprobadas_total;
      document.getElementById('statRechazadas').textContent = data.stats.rechazadas;

      const docsPend = data.stats.docs_pendientes_revision || 0;
      const visitasEnRev = data.stats.en_revision || 0;

      document.getElementById('statEnRevision').textContent = docsPend;
      document.getElementById('statEnRevisionArchivos').textContent = visitasEnRev > 0 ? `📋 ${visitasEnRev} visita(s)` : '';

      const docsEnviados = data.stats.documentos_enviados || 0;
      const enRevision = data.stats.en_revision || 0;
      const badgeRev = document.getElementById('badgeEnRevision');
      const alertaDocs = document.getElementById('alertaDocsPendientes');
      if (enRevision > 0) {
        badgeRev.textContent = enRevision;
        badgeRev.style.display = 'block';
      } else {
        badgeRev.style.display = 'none';
      }

      if (docsPend > 0 || docsEnviados > 0) {
        alertaDocs.style.display = 'flex';
        let textoAlerta = '';
        if (docsPend > 0 && docsEnviados > 0) {
          textoAlerta = `Hay ${docsPend} documento(s) de asistentes pendientes de aprobación y ${docsEnviados} visita(s) con documentos enviados.`;
        } else if (docsPend > 0) {
          textoAlerta = `Hay ${docsPend} documento(s) de asistentes pendientes de aprobación.`;
        } else {
          textoAlerta = `Hay ${docsEnviados} visita(s) con documentos enviados que requieren tu revisión.`;
        }
        document.getElementById('alertaDocsTexto').textContent = textoAlerta;
      } else {
        alertaDocs.style.display = 'none';
      }

      const sidebarBadge = document.getElementById('sidebarBadgeDocs');
      const totalNotif = docsPend + docsEnviados;
      if (totalNotif > 0) {
        sidebarBadge.textContent = totalNotif;
        sidebarBadge.style.display = 'block';
      } else {
        sidebarBadge.style.display = 'none';
      }

      if (data.visitas.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="padding: 40px; text-align: center; color: #6b7280;">
            <i class="ri-inbox-line" style="font-size: 40px;"></i>
            <p>No hay visitas para mostrar</p>
          </td></tr>`;
        return;
      }

      let html = '';
      data.visitas.forEach(v => {
        const estadoBadge = getEstadoBadge(v.estado);
        html += `<tr style="border-bottom: 1px solid #e5e7eb;">
            <td style="padding: 12px 15px;">#${v.id}</td>
            <td style="padding: 12px 15px;">${v.tipo === 'interna' ? '📋 Interna' : '🏢 Externa'}</td>
            <td style="padding: 12px 15px;">
              <div style="font-weight: 500;">${v.responsable}</div>
              <div style="font-size: 12px; color: #6b7280;">${v.correo}</div>
            </td>
            <td style="padding: 12px 15px;">${v.institucion}</td>
            <td style="padding: 12px 15px;">${v.fecha_visita}</td>
            <td style="padding: 12px 15px; text-align: center;">${v.cantidad}</td>
            <td style="padding: 12px 15px;">${estadoBadge}</td>
            <td style="padding: 12px 15px; text-align: center;">
              ${getAccionesVisita(v)}
            </td>
          </tr>`;
      });
      tbody.innerHTML = html;
    })
    .catch(() => {
      tbody.innerHTML = `<tr><td colspan="8" style="padding: 40px; text-align: center; color: #ef4444;">
          <i class="ri-error-warning-line" style="font-size: 40px;"></i>
          <p>Error al cargar las visitas</p>
        </td></tr>`;
    });
}

function getEstadoBadge(estado) {
  const badges = {
    'enviada_coordinacion': '<span style="background:#ede9fe;color:#5b21b6;padding:4px 10px;border-radius:20px;font-size:11px;">🕒 Pendiente coordinación</span>',
    'pendiente': '<span style="background:#fef3c7;color:#92400e;padding:4px 10px;border-radius:20px;font-size:11px;">⏳ Pendiente</span>',
    'aprobada_inicial': '<span style="background:#bbf7d0;color:#166534;padding:4px 10px;border-radius:20px;font-size:11px;">✅ Aprobada Inicial</span>',
    'documentos_enviados': '<span style="background:#dbeafe;color:#1e40af;padding:4px 10px;border-radius:20px;font-size:11px;">📄 Docs Enviados</span>',
    'en_revision_documentos': '<span style="background:#fef3c7;color:#92400e;padding:4px 10px;border-radius:20px;font-size:11px;">🔍 En Revisión</span>',
    'confirmada': '<span style="background:#d1fae5;color:#065f46;padding:4px 10px;border-radius:20px;font-size:11px;">✅✅ Confirmada</span>',
    'rechazada': '<span style="background:#fee2e2;color:#991b1b;padding:4px 10px;border-radius:20px;font-size:11px;">❌ Rechazada</span>',
  };
  return badges[estado] || estado;
}

function getEstadoDocumentoBadge(estado) {
  const badges = {
    'pendiente_documentos': '<span style="background:#fef3c7;color:#92400e;padding:3px 8px;border-radius:15px;font-size:10px;">⏳ Pendiente</span>',
    'documentos_aprobados': '<span style="background:#d1fae5;color:#065f46;padding:3px 8px;border-radius:15px;font-size:10px;">✅ Aprobados</span>',
    'documentos_rechazados': '<span style="background:#fee2e2;color:#991b1b;padding:3px 8px;border-radius:15px;font-size:10px;">❌ Rechazados</span>',
  };
  return badges[estado] || estado;
}

function getAccionesVisita(v) {
  let acciones = `<button onclick="verDetalleVisita('${v.tipo}', ${v.id})" style="background:#6b7280;color:white;border:none;padding:5px 10px;border-radius:5px;cursor:pointer;margin:2px;font-size:11px;">👁️ Ver</button>`;

  if (v.estado === 'enviada_coordinacion') {
    acciones += `<span style="display:inline-block;background:#ede9fe;color:#5b21b6;padding:5px 10px;border-radius:5px;margin:2px;font-size:11px;">🕒 Esperando coordinación</span>`;
    return acciones;
  }

  if (v.estado === 'pendiente') {
    acciones += `<button onclick="accionVisita('${v.tipo}', ${v.id}, 'aprobar')" style="background:#10b981;color:white;border:none;padding:5px 10px;border-radius:5px;cursor:pointer;margin:2px;font-size:11px;">✅ Aprobar</button>`;
    acciones += `<button onclick="accionVisita('${v.tipo}', ${v.id}, 'rechazar')" style="background:#ef4444;color:white;border:none;padding:5px 10px;border-radius:5px;cursor:pointer;margin:2px;font-size:11px;">❌</button>`;
  }

  if (v.estado === 'documentos_enviados') {
    acciones += `<button onclick="verDetalleVisita('${v.tipo}', ${v.id})" style="background:#f59e0b;color:white;border:none;padding:5px 10px;border-radius:5px;cursor:pointer;margin:2px;font-size:11px;font-weight:600;">📄 Revisar Docs</button>`;
    acciones += `<button onclick="accionVisita('${v.tipo}', ${v.id}, 'iniciar_revision')" style="background:#3b82f6;color:white;border:none;padding:5px 10px;border-radius:5px;cursor:pointer;margin:2px;font-size:11px;">🔍 Finalizar Revisión</button>`;
  }

  if (v.estado === 'en_revision_documentos') {
    acciones += `<button onclick="verDetalleVisita('${v.tipo}', ${v.id})" style="background:#f59e0b;color:white;border:none;padding:5px 10px;border-radius:5px;cursor:pointer;margin:2px;font-size:11px;font-weight:600;">📄 Revisar Docs</button>`;

    if (v.puede_confirmar) {
      acciones += `<button onclick="accionVisita('${v.tipo}', ${v.id}, 'confirmar_visita')" style="background:#10b981;color:white;border:none;padding:5px 10px;border-radius:5px;cursor:pointer;margin:2px;font-size:11px;">✅✅ Confirmar</button>`;
    } else if (v.tiene_rechazos) {
      acciones += `<button onclick="accionVisita('${v.tipo}', ${v.id}, 'rechazar')" style="background:#ef4444;color:white;border:none;padding:5px 10px;border-radius:5px;cursor:pointer;margin:2px;font-size:11px;">❌ Rechazar por Documentos</button>`;
    } else {
      acciones += `<button onclick="mAlert('No se puede confirmar la visita aún. Asegúrese de que todos los asistentes tengan sus documentos aprobados.', 'warning')" style="background:#10b981;color:white;border:none;padding:5px 10px;border-radius:5px;cursor:pointer;margin:2px;font-size:11px;opacity:0.5;" title="Documentos pendientes de aprobación">⚠️ Confirmar</button>`;
    }
  }

  return acciones;
}

function filtrarVisitas() {
  const val = document.getElementById('filtroEstadoVisita').value;
  filtrarPorEstado(val);
}

function mostrarVisitasAprobadas() {
  const tbody = document.getElementById('cuerpoTablaVisitas');

  tbody.innerHTML = `<tr><td colspan="8" style="padding: 40px; text-align: center; color: #6b7280;">
      <i class="ri-loader-4-line" style="font-size: 30px; animation: spin 1s linear infinite;"></i>
      <p>Cargando visitas aprobadas...</p>
    </td></tr>`;

  fetch(`/gestion/api/visitas-aprobadas/?tipo=${tipoVisitaActual}`)
    .then(response => response.json())
    .then(data => {
      const visitas = data.visitas || [];

      if (visitas.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="padding: 40px; text-align: center; color: #6b7280;">
            <i class="ri-inbox-line" style="font-size: 40px;"></i>
            <p>No hay visitas aprobadas</p>
          </td></tr>`;
        return;
      }

      let html = '';
      visitas.forEach(v => {
        const estadoBadge = getEstadoBadge(v.estado);
        html += `<tr style="border-bottom: 1px solid #e5e7eb;">
            <td style="padding: 12px 15px;">#${v.id}</td>
            <td style="padding: 12px 15px;">${v.tipo_display}</td>
            <td style="padding: 12px 15px;">
              <div style="font-weight: 500;">${v.responsable}</div>
              <div style="font-size: 12px; color: #6b7280;">${v.correo || 'N/A'}</div>
            </td>
            <td style="padding: 12px 15px;">${v.institucion}</td>
            <td style="padding: 12px 15px;">${v.fecha_visita || 'N/A'}</td>
            <td style="padding: 12px 15px; text-align: center;">${v.cantidad || 0}</td>
            <td style="padding: 12px 15px;">${estadoBadge}</td>
            <td style="padding: 12px 15px; text-align: center;">
              <button onclick="verDetalleVisita('${v.tipo}', ${v.id})" 
                      style="background:#3b82f6;color:white;border:none;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px;">
                Ver detalles
              </button>
            </td>
          </tr>`;
      });
      tbody.innerHTML = html;
    })
    .catch(() => {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 20px; color: #ef4444;">
          <i class="ri-alert-line" style="font-size: 24px;"></i>
          <p style="font-size: 13px; color: #6b7280;">Error al cargar las visitas aprobadas</p>
        </td></tr>`;
    });
}

function filtrarPorEstado(estado) {
  document.getElementById('filtroEstadoVisita').value = estado;
  cargarVisitas();

  if (estado === 'en_revision_documentos') {
    mostrarDocumentosPorEstado('revision');
  } else if (estado === 'documentos_enviados') {
    mostrarDocumentosPorEstado('enviados');
  } else {
    document.getElementById('contenedorInlineDocs').style.display = 'none';
    document.getElementById('contenedorTablaVisitas').style.display = '';
  }
}

function mostrarDocumentosPorEstado(filtro) {
  const inlineContainer = document.getElementById('contenedorInlineDocs');
  const tablaContainer = document.getElementById('contenedorTablaVisitas');
  const contenido = document.getElementById('contenidoInlineDocs');
  const titulo = document.getElementById('tituloInlineDocs');
  const subtitulo = document.getElementById('subtituloInlineDocs');
  const statsDiv = document.getElementById('statsInlineDocs');

  const configs = {
    'revision': {
      titulo: '🔍 Documentos Pendientes de Revisión',
      subtitulo: 'Archivos que aún necesitan ser revisados',
      color: '#f59e0b',
      queryParams: 'estado_asistente=pendiente_documentos',
      filtroLocal: null
    },
    'enviados': {
      titulo: '📄 Documentos Enviados',
      subtitulo: 'Todos los archivos que han sido enviados por los asistentes',
      color: '#3b82f6',
      queryParams: '',
      filtroLocal: null
    },

  };

  const cfg = configs[filtro];
  if (!cfg) return;

  titulo.textContent = cfg.titulo;
  subtitulo.textContent = 'Cargando...';
  statsDiv.innerHTML = '';
  contenido.innerHTML = `
      <div style="text-align:center;padding:40px;color:#6b7280;">
        <i class="ri-loader-4-line" style="font-size:40px;animation:spin 1s linear infinite;"></i>
        <p>Cargando documentos...</p>
      </div>`;

  tablaContainer.style.display = 'none';
  inlineContainer.style.display = 'block';
  window._filtroDocsActual = filtro;

  const tipoParam = tipoVisitaActual ? `&tipo=${tipoVisitaActual}` : '';
  fetch(`/gestion/api/documentos-revision/?${cfg.queryParams}${tipoParam}`)
    .then(r => r.json())
    .then(data => {
      const docs = data.documentos || [];

      const pendientes = docs.filter(d => d.estado === 'pendiente_documentos').length;
      const aprobados = docs.filter(d => d.estado === 'documentos_aprobados').length;
      const rechazados = docs.filter(d => d.estado === 'documentos_rechazados').length;

      statsDiv.innerHTML = `
          <span style="background:#fef3c7;color:#92400e;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600;">⏳ ${pendientes} Pendientes</span>
          <span style="background:#d1fae5;color:#065f46;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600;">✅ ${aprobados} Aprobados</span>
          <span style="background:#fee2e2;color:#991b1b;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600;">❌ ${rechazados} Rechazados</span>
        `;
      subtitulo.textContent = `${docs.length} asistente(s) con documentos encontrados`;

      if (docs.length === 0) {
        contenido.innerHTML = `
            <div style="text-align:center;padding:50px;color:#9ca3af;">
              <i class="ri-inbox-line" style="font-size:50px;margin-bottom:10px;display:block;"></i>
              <p style="font-size:16px;font-weight:500;margin-bottom:4px;">No se encontraron documentos</p>
              <p style="font-size:13px;">No hay archivos que coincidan con este filtro.</p>
            </div>`;
        return;
      }

      const visitasMap = {};
      docs.forEach(d => {
        const key = `${d.visita_tipo}_${d.visita_id}`;
        if (!visitasMap[key]) {
          visitasMap[key] = {
            visita_id: d.visita_id,
            tipo: d.visita_tipo,
            responsable: d.visita_responsable,
            programa: d.visita_programa,
            estado: d.visita_estado,
            estado_display: d.visita_estado_display,
            fecha: d.visita_fecha,
            asistentes: []
          };
        }
        visitasMap[key].asistentes.push(d);
      });

      let html = '';
      Object.values(visitasMap).forEach(visita => {
        const visitaBadge = getEstadoBadge(visita.estado);
        const tipoIcon = visita.tipo === 'interna' ? '📋' : '🏢';

        html += `
            <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:12px;margin-bottom:16px;overflow:hidden;">
              <div style="background:linear-gradient(135deg,#f3f4f6,#e5e7eb);padding:14px 18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                <div>
                  <span style="font-weight:700;font-size:14px;color:#1f2937;">${tipoIcon} Visita #${visita.visita_id}</span>
                  <span style="margin-left:8px;color:#6b7280;font-size:13px;">${visita.responsable}</span>
                  <span style="margin-left:6px;color:#9ca3af;font-size:12px;">• ${visita.programa}</span>
                </div>
                <div style="display:flex;gap:6px;align-items:center;">
                  ${visitaBadge}
                  <span style="color:#9ca3af;font-size:11px;">📅 ${visita.fecha}</span>
                  ${filtro !== 'revision' && filtro !== 'confirmados' && filtro !== 'enviados' ? `<button onclick="verDetalleVisita('${visita.tipo}', ${visita.visita_id})" 
                          style="background:#6b7280;color:white;border:none;padding:4px 10px;border-radius:5px;cursor:pointer;font-size:11px;font-weight:500;">
                    👁️ Ver Detalle
                  </button>` : ''}
                </div>
              </div>
              <div style="padding:12px 18px;">`;

        // Extraer y mostrar los documentos finales UNA SOLA VEZ (al inicio, antes de los asistentes)
        const categorias_finales = ['📝 ATS', '🤸🏻‍♂️ Charla de Seguridad y Calestenia', '📜 Formato Inducción y Reinducción'];
        let documentos_finales_visita = [];

        // Obtener documentos finales del primer asistente que los tenga
        for (const asistente of visita.asistentes) {
          if (asistente.documentos_subidos && asistente.documentos_subidos.length > 0) {
            documentos_finales_visita = asistente.documentos_subidos.filter(ds =>
              categorias_finales.some(cat => ds.categoria && ds.categoria.includes(cat))
            );
            if (documentos_finales_visita.length > 0) break;
          }
        }

        // Mostrar documentos finales de la visita (una sola vez)
        if (documentos_finales_visita.length > 0) {
          html += `
            <div style="padding:10px 14px;margin:6px 0;background:#f0fdf4;border-radius:8px;border:1px solid #bbf7d0;border-left:4px solid #22c55e;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
              <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                <i class="ri-file-text-line" style="color:#22c55e;font-size:16px;"></i>
                <strong style="font-size:13px;color:#166534;">Archivos Finales - ${visita.responsable}</strong>
                <span style="background:#bbf7d0;color:#166534;padding:2px 8px;border-radius:12px;font-size:10px;font-weight:600;">${visita.asistentes.length} asistente(s)</span>
              </div>
              <div style="display:flex;flex-direction:column;gap:6px;width:100%;">`;

          documentos_finales_visita.forEach(ds => {
            let badgeDoc = '';
            if (ds.estado === 'aprobado') {
              badgeDoc = '<span style="background:#d1fae5;color:#065f46;font-size:9px;padding:1px 5px;border-radius:4px;margin-left:4px;">Aprobado</span>';
            } else if (ds.estado === 'rechazado') {
              badgeDoc = '<span style="background:#fee2e2;color:#991b1b;font-size:9px;padding:1px 5px;border-radius:4px;margin-left:4px;">Rechazado</span>';
            }

            html += `
              <div style="display:flex;justify-content:space-between;align-items:center;width:100%;gap:10px;">
                <div style="display:flex;gap:4px;align-items:center;">
                  <button onclick="visualizarDocumento('${ds.url}', '${ds.titulo} - ${visita.responsable}', {id: ${ds.id}, estado: '${ds.estado}'})" 
                          style="background:#059669;color:white;padding:5px 12px;border-radius:6px;border:none;cursor:pointer;font-size:11px;display:inline-flex;align-items:center;gap:4px;font-weight:500;">
                    <i class="ri-eye-line"></i> 📋 ${ds.titulo}
                  </button>
                  <a href="${ds.download_url || ds.url}" download style="background:#6b7280;color:white;padding:5px 8px;border-radius:6px;text-decoration:none;font-size:11px;display:inline-flex;align-items:center;" title="Descargar">
                    <i class="ri-download-line"></i>
                  </a>
                </div>
                ${badgeDoc}
              </div>`;
          });

          html += `
              </div>
            </div>`;
        }

        visita.asistentes.forEach(a => {
          let aBadge = '';
          let borderLeft = '#d1d5db';
          if (a.estado === 'pendiente_documentos') {
            aBadge = '<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:12px;font-size:10px;font-weight:600;">⏳ Pendiente</span>';
            borderLeft = '#f59e0b';
          } else if (a.estado === 'documentos_aprobados') {
            aBadge = '<span style="background:#d1fae5;color:#065f46;padding:2px 8px;border-radius:12px;font-size:10px;font-weight:600;">✅ Aprobado</span>';
            borderLeft = '#10b981';
          } else if (a.estado === 'documentos_rechazados') {
            aBadge = '<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:12px;font-size:10px;font-weight:600;">❌ Rechazado</span>';
            borderLeft = '#ef4444';
          }

          let botonesDoc = '';
          if (a.documento_adicional) {
            botonesDoc += `
                  <div style="display:flex;justify-content:space-between;align-items:center;width:100%;gap:10px;">
                    <div style="display:flex;gap:4px;align-items:center;">
                      <button onclick="visualizarDocumento('${a.documento_adicional}', 'Doc. Adicional - ${a.nombre_completo}', {estado: '${a.estado === 'documentos_aprobados' ? 'aprobado' : 'pendiente'}'})" 
                              style="background:#8b5cf6;color:white;padding:5px 12px;border-radius:6px;border:none;cursor:pointer;font-size:11px;display:inline-flex;align-items:center;gap:4px;font-weight:500;">
                        <i class="ri-eye-line"></i> 📎 Doc. Adicional
                      </button>
                      <a href="${a.documento_adicional}" download style="background:#6b7280;color:white;padding:5px 8px;border-radius:6px;text-decoration:none;font-size:11px;display:inline-flex;align-items:center;" title="Descargar">
                        <i class="ri-download-line"></i>
                      </a>
                    </div>
                    ${a.estado === 'documentos_aprobados' ? '<span style="background:#d1fae5;color:#065f46;font-size:10px;padding:2px 8px;border-radius:6px;font-weight:600;">Aprobado</span>' : (a.estado === 'documentos_rechazados' ? '<span style="background:#fee2e2;color:#991b1b;font-size:10px;padding:2px 8px;border-radius:6px;font-weight:600;">Rechazado</span>' : '')}
                  </div>`;
          }
          if (a.documentos_subidos && a.documentos_subidos.length > 0) {
            // Filtrar SOLO documentos que NO sean los archivos finales (para evitar duplicados)
            const categorias_finales = ['📝 ATS', '🤸🏻‍♂️ Charla de Seguridad y Calestenia', '📜 Formato Inducción y Reinducción'];
            const documentos_personales = a.documentos_subidos.filter(ds =>
              !categorias_finales.some(cat => ds.categoria && ds.categoria.includes(cat))
            );

            // Mostrar solo documentos personales del asistente (no los finales)
            documentos_personales.forEach(ds => {
              let badgeDoc = '';
              if (ds.estado === 'aprobado') {
                badgeDoc = '<span style="background:#d1fae5;color:#065f46;font-size:9px;padding:1px 5px;border-radius:4px;margin-left:4px;">Aprobado</span>';
              } else if (ds.estado === 'rechazado') {
                badgeDoc = '<span style="background:#fee2e2;color:#991b1b;font-size:9px;padding:1px 5px;border-radius:4px;margin-left:4px;">Rechazado</span>';
              }

              botonesDoc += `
                  <div style="display:flex;justify-content:space-between;align-items:center;width:100%;gap:10px;">
                    <div style="display:flex;gap:4px;align-items:center;">
                      <button onclick="visualizarDocumento('${ds.url}', '${ds.titulo} - ${a.nombre_completo}', {id: ${ds.id}, estado: '${ds.estado}'})" 
                              style="background:#059669;color:white;padding:5px 12px;border-radius:6px;border:none;cursor:pointer;font-size:11px;display:inline-flex;align-items:center;gap:4px;font-weight:500;">
                        <i class="ri-eye-line"></i> 📋 ${ds.titulo}
                      </button>
                      <a href="${ds.download_url || ds.url}" download style="background:#6b7280;color:white;padding:5px 8px;border-radius:6px;text-decoration:none;font-size:11px;display:inline-flex;align-items:center;" title="Descargar">
                        <i class="ri-download-line"></i>
                      </a>
                    </div>
                    ${badgeDoc}
                  </div>`;
            });
          }

          let accionesHtml = '';
          if (a.estado === 'pendiente_documentos') {
            accionesHtml = `
                <div style="display:flex;gap:6px;margin-left:auto;">
                  <button onclick="event.stopPropagation();aprobarDocDesdeListado('${a.visita_tipo}', ${a.asistente_id}, '${filtro}')" 
                          style="background:linear-gradient(135deg,#10b981,#059669);color:white;border:none;padding:5px 14px;border-radius:6px;cursor:pointer;font-size:11px;font-weight:600;display:inline-flex;align-items:center;gap:4px;">
                    <i class="ri-check-line"></i> Aprobar
                  </button>
                  <button onclick="event.stopPropagation();rechazarDocDesdeListado('${a.visita_tipo}', ${a.asistente_id}, '${a.nombre_completo.replace(/'/g, "\\'")}', '${filtro}')" 
                          style="background:linear-gradient(135deg,#ef4444,#dc2626);color:white;border:none;padding:5px 14px;border-radius:6px;cursor:pointer;font-size:11px;font-weight:600;display:inline-flex;align-items:center;gap:4px;">
                    <i class="ri-close-line"></i> Rechazar
                  </button>
                </div>`;
          }

          let obsHtml = '';
          if (a.observaciones_revision) {
            obsHtml = `<div style="margin-top:6px;padding:6px 10px;background:#fef3c7;border-radius:5px;font-size:11px;color:#92400e;border:1px solid #fcd34d;">📝 ${a.observaciones_revision}</div>`;
          }

          html += `
              <div style="padding:10px 14px;margin:6px 0;background:white;border-radius:8px;border:1px solid #e5e7eb;border-left:4px solid ${borderLeft};box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <div style="display:flex;align-items:center;gap:8px;justify-content:space-between;flex-wrap:wrap;">
                  <div style="display:flex;align-items:center;gap:8px;">
                    <i class="ri-user-line" style="color:#8b5cf6;"></i>
                    <strong style="font-size:13px;">${a.nombre_completo}</strong>
                    <span style="color:#9ca3af;font-size:11px;">🪪 ${a.tipo_documento}: ${a.numero_documento}</span>
                    ${aBadge}
                  </div>
                  ${accionesHtml}
                </div>
                <div style="display:flex;flex-direction:column;gap:6px;width:100%;margin-top:8px;">
                  ${botonesDoc}
                </div>
                ${obsHtml}
              </div>`;
        });

        html += `</div></div>`;
      });

      contenido.innerHTML = html;
    })
    .catch(() => {
      contenido.innerHTML = `
          <div style="text-align:center;padding:50px;color:#ef4444;">
            <i class="ri-error-warning-line" style="font-size:50px;margin-bottom:10px;display:block;"></i>
            <p style="font-size:16px;font-weight:500;">Error al cargar documentos</p>
            <p style="font-size:13px;color:#6b7280;">Verifique su conexión e intente de nuevo.</p>
          </div>`;
    });
}

function volverAVisitas() {
  document.getElementById('contenedorInlineDocs').style.display = 'none';
  document.getElementById('contenedorTablaVisitas').style.display = '';
  document.getElementById('filtroEstadoVisita').value = 'todos';
  cargarVisitas();
}

async function aprobarDocDesdeListado(tipo, asistenteId, filtroActual) {
  const ok = await mConfirm('¿Aprobar los documentos de este asistente?', {
    title: 'Aprobar Documentos',
    icon: '<i class="ri-check-double-line"></i>',
    iconClass: 'cm-success',
    confirmText: 'Sí, aprobar',
    confirmClass: 'cm-btn-success'
  });
  if (!ok) return;

  const formData = new FormData();
  formData.append('observaciones', '');
  addCsrfToFormData(formData);

  fetch(`/gestion/api/asistentes/${tipo}/${asistenteId}/aprobar/`, {
    method: 'POST',
    body: formData
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        mAlert(data.message, 'success');
        cargarVisitas();
        mostrarDocumentosPorEstado(filtroActual);
      } else {
        mAlert('Error: ' + data.error, 'error');
      }
    })
    .catch(() => mAlert('Error de conexión.', 'error'));
}

async function rechazarDocDesdeListado(tipo, asistenteId, nombre, filtroActual) {
  const obs = await mPrompt('Ingrese las observaciones del rechazo para <strong>' + nombre + '</strong>:', {
    title: 'Rechazar Documentos',
    icon: '<i class="ri-close-circle-line"></i>',
    iconClass: 'cm-error',
    placeholder: 'Motivo del rechazo...',
    confirmText: 'Rechazar',
    confirmClass: 'cm-btn-danger'
  });
  if (obs !== null && obs.trim() !== '') {
    const formData = new FormData();
    formData.append('observaciones', obs);
    addCsrfToFormData(formData);

    fetch(`/gestion/api/asistentes/${tipo}/${asistenteId}/rechazar/`, {
      method: 'POST',
      body: formData
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          mAlert(data.message, 'success');
          cargarVisitas();
          mostrarDocumentosPorEstado(filtroActual);
        } else {
          mAlert('Error: ' + data.error, 'error');
        }
      })
      .catch(() => mAlert('Error de conexión.', 'error'));
  } else if (obs === '') {
    mAlert('Debe proporcionar observaciones al rechazar documentos.', 'warning');
  }
}

function visualizarDocumento(url, titulo, extraOptions = null) {
  document.getElementById('tituloVisualizarDoc').textContent = '📄 ' + titulo;
  document.getElementById('descargarDocLink').href = url;
  document.getElementById('abrirNuevaTab').href = url;

  const footer = document.getElementById('footerAccionesDoc');
  const btnAprobar = document.getElementById('btnAprobarIndividual');
  const btnRechazar = document.getElementById('btnRechazarIndividual');

  if (extraOptions && extraOptions.id) {
    footer.style.display = 'flex';
    if (extraOptions.estado && extraOptions.estado !== 'pendiente') {
      btnAprobar.style.setProperty('display', 'none', 'important');
      btnRechazar.style.setProperty('display', 'none', 'important');

      let statusBadge = document.getElementById('statusBadgeViewer');
      if (!statusBadge) {
        statusBadge = document.createElement('span');
        statusBadge.id = 'statusBadgeViewer';
        footer.appendChild(statusBadge);
      }
      statusBadge.style.display = 'inline-block';
      if (extraOptions.estado === 'aprobado') {
        statusBadge.innerHTML = '<i class="ri-checkbox-circle-line"></i> DOCUMENTO APROBADO';
        statusBadge.style.cssText = 'background:#10b981;color:white;padding:8px 20px;border-radius:8px;font-weight:700;font-size:14px;display:flex;align-items:center;gap:8px;';
      } else {
        statusBadge.innerHTML = '<i class="ri-close-circle-line"></i> DOCUMENTO RECHAZADO';
        statusBadge.style.cssText = 'background:#ef4444;color:white;padding:8px 20px;border-radius:8px;font-weight:700;font-size:14px;display:flex;align-items:center;gap:8px;';
      }
    } else {
      btnAprobar.style.setProperty('display', 'flex', 'important');
      btnRechazar.style.setProperty('display', 'flex', 'important');
      const statusBadge = document.getElementById('statusBadgeViewer');
      if (statusBadge) statusBadge.style.setProperty('display', 'none', 'important');

      btnAprobar.onclick = () => revisarDocumentoIndividual(extraOptions.id, 'aprobado');
      btnRechazar.onclick = () => revisarDocumentoIndividual(extraOptions.id, 'rechazado');
    }
  } else {
    footer.style.display = 'none';
  }

  document.getElementById('modalVisualizarDoc').style.display = 'block';

  const contenedor = document.getElementById('contenedorVisualizarDoc');
  const loading = document.getElementById('docLoadingIndicator');
  loading.style.display = 'block';

  Array.from(contenedor.children).forEach(child => {
    if (child.id !== 'docLoadingIndicator') child.remove();
  });

  let absoluteUrl = url;
  if (url.startsWith('/')) {
    absoluteUrl = window.location.origin + url;
  }

  const iframe = document.createElement('iframe');
  iframe.src = absoluteUrl;
  iframe.id = 'docIframe';
  iframe.style.cssText = 'width:100%;height:100%;border:none;background:white;';

  let loadSuccess = false;
  iframe.onload = () => {
    loadSuccess = true;
    loading.style.display = 'none';
  };

  iframe.onerror = () => {
    loading.style.display = 'none';
    mostrarErrorDoc(contenedor, absoluteUrl);
  };
  contenedor.appendChild(iframe);

  setTimeout(() => {
    if (!loadSuccess && loading.style.display !== 'none') {
      loading.style.display = 'none';
      mostrarErrorDoc(contenedor, absoluteUrl);
    }
  }, 4000);
}

async function revisarDocumentoIndividual(docSubidoId, estado) {
  let observaciones = '';
  if (estado === 'rechazado') {
    observaciones = await mPrompt('Ingrese el motivo del rechazo:', {
      title: 'Rechazar Documento',
      icon: '<i class="ri-close-circle-line"></i>',
      iconClass: 'cm-error',
      confirmText: 'Rechazar',
      confirmClass: 'cm-btn-danger'
    });
    if (observaciones === null) return;
    if (observaciones.trim() === '') {
      mAlert('Debe proporcionar un motivo.', 'warning');
      return;
    }
  }

  const formData = new FormData();
  formData.append('estado', estado);
  formData.append('observaciones', observaciones);
  addCsrfToFormData(formData);

  fetch(`/documentos/api/revisar-asistente/${docSubidoId}/`, {
    method: 'POST',
    body: formData
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        mAlert(data.message, 'success');
        cerrarModalVisualizarDoc();
        if (window.detalleVisitaActual) {
          verDetalleVisita(window.detalleVisitaActual.tipo, window.detalleVisitaActual.id);
        }
      } else {
        mAlert('Error: ' + (data.error || 'No se pudo actualizar el estado'), 'error');
      }
    })
    .catch(() => mAlert('Error de conexión.', 'error'));
}

function mostrarErrorDoc(contenedor, url) {
  Array.from(contenedor.children).forEach(child => {
    if (child.id !== 'docLoadingIndicator') child.remove();
  });
  const div = document.createElement('div');
  div.style.cssText = 'text-align:center;padding:40px;color:#ef4444;';
  div.innerHTML = `
      <i class="ri-error-warning-line" style="font-size:50px;margin-bottom:10px;"></i>
      <p style="font-size:15px;font-weight:500;">No se pudo cargar el documento</p>
      <p style="font-size:13px;color:#6b7280;margin-bottom:15px;">El archivo puede no existir o el formato no es compatible.</p>
      <a href="${url}" target="_blank" style="background:#3b82f6;color:white;padding:10px 24px;border-radius:6px;text-decoration:none;font-size:14px;"><i class="ri-download-line"></i> Abrir en nueva pestaña</a>
    `;
  contenedor.appendChild(div);
}

function cerrarModalVisualizarDoc() {
  document.getElementById('modalVisualizarDoc').style.display = 'none';
  const contenedor = document.getElementById('contenedorVisualizarDoc');
  Array.from(contenedor.children).forEach(child => {
    if (child.id !== 'docLoadingIndicator') child.remove();
  });
}

function verDetalleVisita(tipo, id) {
  const modal = document.getElementById('modalDetalleVisita');
  const contenido = document.getElementById('contenidoDetalleVisita');
  document.getElementById('detalleVisitaId').textContent = id;
  contenido.innerHTML = '<p style="text-align:center;padding:20px;"><i class="ri-loader-4-line" style="animation:spin 1s linear infinite;"></i> Cargando...</p>';
  modal.style.display = 'block';

  fetch(`/gestion/api/visitas/${tipo}/${id}/`)
    .then(response => response.json())
    .then(data => {
      // Extraer documentos finales una sola vez (del primer asistente que los tenga)
      const categorias_finales = ['📝 ATS', '🤸🏻‍♂️ Charla de Seguridad y Calestenia', '📜 Formato Inducción y Reinducción'];
      let documentos_finales = [];

      for (const asistente of data.asistentes) {
        if (asistente.documentos_subidos && asistente.documentos_subidos.length > 0) {
          documentos_finales = asistente.documentos_subidos.filter(ds =>
            categorias_finales.some(cat => ds.categoria && ds.categoria.includes(cat))
          );
          if (documentos_finales.length > 0) break;
        }
      }

      // Construir HTML de archivos finales
      let archivosFinalesHtml = '';
      if (documentos_finales.length > 0) {
        archivosFinalesHtml = `
          <div style="background:#f0fdf4;padding:16px;border-radius:10px;border:1px solid #bbf7d0;border-left:4px solid #22c55e;margin-bottom:20px;">
            <h4 style="color:#166534;margin:0 0 12px 0;display:flex;align-items:center;gap:8px;">
              <i class="ri-file-text-line"></i> 📁 Archivos Finales - ${data.responsable}
            </h4>
            <div style="display:flex;flex-direction:column;gap:8px;">`;

        documentos_finales.forEach(ds => {
          let badgeDoc = '';
          if (ds.estado === 'aprobado') {
            badgeDoc = '<span style="background:#d1fae5;color:#065f46;font-size:11px;padding:3px 10px;border-radius:6px;font-weight:600;">Aprobado</span>';
          } else if (ds.estado === 'rechazado') {
            badgeDoc = '<span style="background:#fee2e2;color:#991b1b;font-size:11px;padding:3px 10px;border-radius:6px;font-weight:600;">Rechazado</span>';
          } else {
            badgeDoc = '<span style="background:#fef3c7;color:#92400e;font-size:11px;padding:3px 10px;border-radius:6px;font-weight:600;">Pendiente</span>';
          }

          archivosFinalesHtml += `
              <div style="display:flex;justify-content:space-between;align-items:center;background:white;padding:10px;border-radius:6px;border:1px solid #d1faf0;">
                <div style="display:flex;gap:6px;align-items:center;">
                  <button onclick="visualizarDocumento('${ds.url}', '${ds.titulo} - ${data.responsable}', {id: ${ds.id}, estado: '${ds.estado}'})" 
                          style="background:#059669;color:white;padding:7px 14px;border-radius:6px;border:none;cursor:pointer;font-size:12px;display:inline-flex;align-items:center;gap:5px;font-weight:500;">
                    <i class="ri-eye-line"></i> 📋 ${ds.titulo}
                  </button>
                  <a href="${ds.download_url || ds.url}" download style="background:#6b7280;color:white;padding:7px 10px;border-radius:6px;text-decoration:none;font-size:12px;display:inline-flex;align-items:center;" title="Descargar">
                    <i class="ri-download-line"></i>
                  </a>
                </div>
                ${badgeDoc}
              </div>`;
        });

        archivosFinalesHtml += `
            </div>
          </div>`;
      }

      let asistentesHtml = '';
      if (data.asistentes.length > 0) {
        asistentesHtml = data.asistentes.map(a => {
          let botonesDoc = '';
          let tieneDocs = false;
          if (a.documento_identidad) {
            tieneDocs = true;
            botonesDoc += `
                  <div style="display:flex;justify-content:space-between;align-items:center;width:100%;gap:10px;">
                    <div style="display:flex;gap:4px;align-items:center;">
                      <button onclick="visualizarDocumento('${a.documento_identidad}', 'Documento de Identidad - ${a.nombre_completo}', {estado: '${a.estado === 'documentos_aprobados' ? 'aprobado' : 'pendiente'}'})" 
                              style="background:#3b82f6;color:white;padding:7px 14px;border-radius:6px;border:none;cursor:pointer;font-size:12px;display:inline-flex;align-items:center;gap:5px;font-weight:500;">
                        <i class="ri-eye-line"></i> 🪪 Doc. Identidad
                      </button>
                      <a href="${a.documento_identidad}" download style="background:#6b7280;color:white;padding:7px 10px;border-radius:6px;text-decoration:none;font-size:12px;display:inline-flex;align-items:center;" title="Descargar">
                        <i class="ri-download-line"></i>
                      </a>
                    </div>
                    ${a.estado === 'documentos_aprobados' ? '<span style="background:#d1fae5;color:#065f46;font-size:11px;padding:3px 10px;border-radius:6px;font-weight:600;">Aprobado</span>' : (a.estado === 'documentos_rechazados' ? '<span style="background:#fee2e2;color:#991b1b;font-size:11px;padding:3px 10px;border-radius:6px;font-weight:600;">Rechazado</span>' : '')}
                  </div>`;
          }
          if (a.documento_adicional) {
            tieneDocs = true;
            botonesDoc += `
                  <div style="display:flex;justify-content:space-between;align-items:center;width:100%;gap:10px;">
                    <div style="display:flex;gap:4px;align-items:center;">
                      <button onclick="visualizarDocumento('${a.documento_adicional}', 'Documento Adicional - ${a.nombre_completo}', {estado: '${a.estado === 'documentos_aprobados' ? 'aprobado' : 'pendiente'}'})" 
                              style="background:#8b5cf6;color:white;padding:7px 14px;border-radius:6px;border:none;cursor:pointer;font-size:12px;display:inline-flex;align-items:center;gap:5px;font-weight:500;">
                        <i class="ri-eye-line"></i> 📎 Ver Doc. Adicional
                      </button>
                      <a href="${a.documento_adicional}" download style="background:#6b7280;color:white;padding:7px 10px;border-radius:6px;text-decoration:none;font-size:12px;display:inline-flex;align-items:center;" title="Descargar">
                        <i class="ri-download-line"></i>
                      </a>
                    </div>
                    ${a.estado === 'documentos_aprobados' ? '<span style="background:#d1fae5;color:#065f46;font-size:11px;padding:3px 10px;border-radius:6px;font-weight:600;">Aprobado</span>' : (a.estado === 'documentos_rechazados' ? '<span style="background:#fee2e2;color:#991b1b;font-size:11px;padding:3px 10px;border-radius:6px;font-weight:600;">Rechazado</span>' : '')}
                  </div>`;
          }
          if (a.documentos_subidos && a.documentos_subidos.length > 0) {
            // Filtrar SOLO documentos que NO sean los archivos finales
            const categorias_finales = ['📝 ATS', '🤸🏻‍♂️ Charla de Seguridad y Calestenia', '📜 Formato Inducción y Reinducción'];
            const documentos_personales = a.documentos_subidos.filter(ds =>
              !categorias_finales.some(cat => ds.categoria && ds.categoria.includes(cat))
            );

            if (documentos_personales.length > 0) {
              tieneDocs = true;
            }

            documentos_personales.forEach(ds => {
              let badgeDoc = '';
              if (ds.estado === 'aprobado') {
                badgeDoc = '<span style="background:#d1fae5;color:#065f46;font-size:9px;padding:1px 5px;border-radius:4px;margin-left:4px;">Aprobado</span>';
              } else if (ds.estado === 'rechazado') {
                badgeDoc = '<span style="background:#fee2e2;color:#991b1b;font-size:9px;padding:1px 5px;border-radius:4px;margin-left:4px;">Rechazado</span>';
              }

              botonesDoc += `
                  <div style="display:flex;justify-content:space-between;align-items:center;width:100%;gap:10px;">
                    <div style="display:flex;gap:4px;align-items:center;">
                      <button onclick="visualizarDocumento('${ds.url}', '${ds.titulo} - ${a.nombre_completo}', {id: ${ds.id}, estado: '${ds.estado}'})" 
                              style="background:#059669;color:white;padding:7px 14px;border-radius:6px;border:none;cursor:pointer;font-size:12px;display:inline-flex;align-items:center;gap:5px;font-weight:500;">
                        <i class="ri-eye-line"></i> 📋 ${ds.titulo}
                      </button>
                      <a href="${ds.download_url || ds.url}" download style="background:#6b7280;color:white;padding:7px 10px;border-radius:6px;text-decoration:none;font-size:12px;display:inline-flex;align-items:center;" title="Descargar">
                        <i class="ri-download-line"></i>
                      </a>
                    </div>
                    ${badgeDoc}
                  </div>
                  ${ds.observaciones_revision ? `<div style="font-size:10px;color:#991b1b;font-style:italic;margin-left:4px;margin-top:-2px;margin-bottom:6px;">❌ ${ds.observaciones_revision}</div>` : ''}`;
            });
          }

          if (!tieneDocs) {
            botonesDoc = `<span style="color:#9ca3af;font-size:12px;font-style:italic;">📭 Sin documentos subidos aún</span>`;
          }

          let estadoBadge = '';
          let borderColor = '#e5e7eb';
          if (a.estado === 'pendiente_documentos') {
            borderColor = '#f59e0b';
            estadoBadge = '<span style="background:#fef3c7;color:#92400e;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:500;">⏳ Pendiente</span>';
          } else if (a.estado === 'documentos_aprobados') {
            borderColor = '#10b981';
            estadoBadge = '<span style="background:#d1fae5;color:#065f46;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:500;">✅ Aprobado</span>';
          } else if (a.estado === 'documentos_rechazados') {
            borderColor = '#ef4444';
            estadoBadge = '<span style="background:#fee2e2;color:#991b1b;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:500;">❌ Rechazado</span>';
          }

          let accionesDocHtml = '';
          if (a.estado === 'pendiente_documentos' && tieneDocs) {
            let btnAprobarMask = '';
            const hasRechazos = a.tiene_rechazos || a.documentos_subidos.some(ds => ds.estado === 'rechazado');
            const hasAprobaciones = a.tiene_aprobaciones || a.documentos_subidos.some(ds => ds.estado === 'aprobado');
            const allAprobados = a.todos_aprobados || (tieneDocs && a.documentos_subidos.every(ds => ds.estado === 'aprobado'));

            if (hasRechazos) {
              btnAprobarMask = `
                <button onclick="mAlert('No se puede aprobar masivamente porque existen documentos rechazados. El asistente debe corregir los archivos o debe marcarlos todos individualmente.', 'warning')" 
                        style="background:#9ca3af;color:white;border:none;padding:8px 18px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;display:inline-flex;align-items:center;gap:5px;opacity:0.7;">
                  <i class="ri-forbid-line"></i> Rechazos detectados
                </button>`;
            } else if (!hasAprobaciones) {
              btnAprobarMask = `
                <button onclick="mAlert('Debe revisar y aprobar al menos un documento individualmente antes de poder aprobar todos masivamente.', 'info')" 
                        style="background:#6b7280;color:white;border:none;padding:8px 18px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;display:inline-flex;align-items:center;gap:5px;opacity:0.7;">
                  <i class="ri-information-line"></i> Revisar primero
                </button>`;
            } else {
              const btnText = allAprobados ? 'Aprobación Final' : 'Aprobar Documentos';
              btnAprobarMask = `
                <button onclick="event.stopPropagation();aprobarDocRevision('${tipo}', ${a.id})" 
                        style="background:linear-gradient(135deg,#10b981,#059669);color:white;border:none;padding:8px 18px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;display:inline-flex;align-items:center;gap:5px;transition:all .2s;box-shadow:0 2px 6px rgba(16,185,129,0.3);">
                  <i class="ri-check-double-line"></i> ${btnText}
                </button>`;
            }

            accionesDocHtml = `
                <div style="display:flex;gap:8px;margin-top:12px;padding-top:12px;border-top:1px dashed #d1d5db;align-items:center;">
                  <span style="font-size:12px;font-weight:600;color:#374151;">Acción:</span>
                  ${btnAprobarMask}
                  <button onclick="event.stopPropagation();rechazarDocRevision('${tipo}', ${a.id}, '${a.nombre_completo.replace(/'/g, "\\'")}')" 
                          style="background:linear-gradient(135deg,#ef4444,#dc2626);color:white;border:none;padding:8px 18px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;display:inline-flex;align-items:center;gap:5px;transition:all .2s;box-shadow:0 2px 6px rgba(239,68,68,0.3);">
                    <i class="ri-close-line"></i> Rechazar Todo
                  </button>
                </div>`;
          }

          let obsRevHtml = '';
          if (a.observaciones_revision) {
            obsRevHtml = `<div style="margin-top:10px;padding:10px;background:#fef3c7;border-radius:6px;font-size:12px;color:#92400e;border:1px solid #fcd34d;">📝 <strong>Observaciones:</strong> ${a.observaciones_revision}</div>`;
          }

          return `
              <div style="padding:14px;background:#f9fafb;margin:8px 0;border-radius:10px;border:1px solid ${borderColor};border-left:4px solid ${borderColor};box-shadow:0 1px 4px rgba(0,0,0,0.04);">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                  <div>
                    <div style="display:flex;align-items:center;gap:8px;">
                      <i class="ri-user-line" style="color:#8b5cf6;"></i>
                      <strong style="font-size:14px;">${a.nombre_completo}</strong>
                      ${estadoBadge}
                    </div>
                    <div style="color:#6b7280;font-size:12px;padding-left:24px;">🪪 ${a.tipo_documento}: ${a.numero_documento}</div>
                    <div style="display:flex;gap:14px;padding-left:24px;margin-top:4px;flex-wrap:wrap;">
                      ${a.correo ? `<span style="color:#6b7280;font-size:12px;">✉️ ${a.correo}</span>` : ''}
                      ${a.telefono ? `<span style="color:#6b7280;font-size:12px;">📞 ${a.telefono}</span>` : ''}
                    </div>
                  </div>
                </div>
                <div style="display:flex;flex-direction:column;gap:8px;align-items:flex-start;width:100%;margin-top:8px;">
                  ${botonesDoc}
                </div>
                ${accionesDocHtml}
                ${obsRevHtml}
              </div>`;
        }).join('');
      }

      let html = `
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;background:#f9fafb;padding:14px;border-radius:10px;">
            <div><strong>Responsable:</strong> ${data.responsable}</div>
            <div><strong>Estado:</strong> ${getEstadoBadge(data.estado)}</div>
            <div><strong>${tipo === 'interna' ? 'Programa' : 'Institución'}:</strong> ${data.programa || data.institucion || 'N/A'}</div>
            <div><strong>Fecha:</strong> ${data.fecha_solicitud}</div>
          </div>
          
          ${archivosFinalesHtml}
          
          <h4 style="color:#374151;border-bottom:2px solid #8b5cf6;padding-bottom:8px;margin-bottom:8px;display:flex;align-items:center;gap:8px;">
            👥 Asistentes Registrados
            <span style="background:#dbeafe;color:#1e40af;padding:2px 10px;border-radius:12px;font-size:13px;">${data.asistentes.length} asistente(s)</span>
          </h4>
          
          ${data.asistentes.length > 0
          ? `<div style="max-height:450px;overflow-y:auto;">${asistentesHtml}</div>`
          : `<div style="text-align:center;padding:30px;color:#9ca3af;background:#f9fafb;border-radius:8px;border:1px solid #e5e7eb;">
                <i class="ri-user-add-line" style="font-size:36px;margin-bottom:6px;"></i>
                <p style="margin:0;">No hay asistentes registrados aún</p>
              </div>`
        }
        `;
      contenido.innerHTML = html;

      window.detalleVisitaActual = data;
    })
    .catch(() => {
      contenido.innerHTML = '<p style="color:#ef4444;text-align:center;">Error al cargar el detalle</p>';
    });
}

function revisarDocumento(tipo, asistente_id, accion, observaciones = '') {
  const formData = new FormData();
  formData.append('observaciones', observaciones);
  addCsrfToFormData(formData);

  fetch(`/gestion/api/asistentes/${tipo}/${asistente_id}/${accion}/`, {
    method: 'POST',
    body: formData
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        mAlert(data.message, 'success');
        if (window.detalleVisitaActual) {
          verDetalleVisita(window.detalleVisitaActual.tipo, window.detalleVisitaActual.id);
        }
      } else {
        mAlert('Error: ' + data.error, 'error');
      }
    })
    .catch(() => {
      mAlert('Error de conexión. Verifique su red e intente de nuevo.', 'error');
    });
}

async function abrirModalRechazoDoc(tipo, asistente_id, nombre) {
  const obs = await mPrompt(`Ingrese las observaciones del rechazo para <strong>${nombre}</strong>:`, {
    title: 'Rechazar Documentos',
    icon: '<i class="ri-close-circle-line"></i>',
    iconClass: 'cm-error',
    placeholder: 'Motivo del rechazo...',
    confirmText: 'Rechazar',
    confirmClass: 'cm-btn-danger'
  });
  if (obs !== null && obs.trim() !== '') {
    revisarDocumento(tipo, asistente_id, 'rechazar', obs);
  } else if (obs === '') {
    mAlert('Debe proporcionar observaciones al rechazar documentos.', 'warning');
  }
}

function cerrarModalDetalle() {
  document.getElementById('modalDetalleVisita').style.display = 'none';
}

async function accionVisita(tipo, id, accion) {
  let observaciones = '';
  if (accion === 'rechazar') {
    observaciones = await mPrompt('Ingrese el motivo del rechazo de esta visita:', {
      title: 'Rechazar Visita',
      icon: '<i class="ri-close-circle-line"></i>',
      iconClass: 'cm-error',
      confirmText: 'Rechazar',
      confirmClass: 'cm-btn-danger',
      placeholder: 'Escriba el motivo aquí...'
    });
    if (observaciones === null) return;
    if (observaciones.trim() === '') {
      mAlert('Debe proporcionar un motivo para rechazar la visita.', 'warning');
      return;
    }
  }
  if (accion === 'aprobar') {
    const ok = await mConfirm('¿Estás seguro de <strong>aprobar</strong> esta visita?', {
      title: 'Aprobar Visita',
      icon: '<i class="ri-check-line"></i>',
      iconClass: 'cm-success',
      confirmText: 'Sí, aprobar',
      confirmClass: 'cm-btn-success'
    });
    if (!ok) return;
  }
  if (accion === 'iniciar_revision') {
    const ok = await mConfirm('¿Desea finalizar la revisión de esta visita?', {
      title: 'Finalizar Revisión',
      icon: '<i class="ri-search-eye-line"></i>',
      iconClass: 'cm-info',
      confirmText: 'Finalizar',
      confirmClass: 'cm-btn-primary'
    });
    if (!ok) return;
  }
  if (accion === 'confirmar_visita') {
    const ok = await mConfirm('¿Confirmar esta visita? Todos los documentos deben estar aprobados.', {
      title: 'Confirmar Visita',
      icon: '<i class="ri-checkbox-circle-line"></i>',
      iconClass: 'cm-success',
      confirmText: 'Sí, confirmar',
      confirmClass: 'cm-btn-success'
    });
    if (!ok) return;
  }

  const formData = new FormData();
  formData.append('observaciones', observaciones);

  fetch(`/gestion/api/visitas/${tipo}/${id}/${accion}/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCsrfToken()
    },
    body: formData
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        mAlert(data.message, 'success');
        if (accion === 'aprobar') {
          filtrarPorEstado('aprobadas');
        } else {
          cargarVisitas();
        }
      } else {
        mAlert('Error: ' + data.error, 'error');
      }
    })
    .catch(() => {
      mAlert('Error de conexión. Verifique su red e intente de nuevo.', 'error');
    });
}

async function aprobarDocRevision(tipo, asistenteId) {
  const ok = await mConfirm('¿Aprobar los documentos de este asistente?', {
    title: 'Aprobar Documentos',
    icon: '<i class="ri-check-double-line"></i>',
    iconClass: 'cm-success',
    confirmText: 'Sí, aprobar',
    confirmClass: 'cm-btn-success'
  });
  if (!ok) return;

  const formData = new FormData();
  formData.append('observaciones', '');
  addCsrfToFormData(formData);

  fetch(`/gestion/api/asistentes/${tipo}/${asistenteId}/aprobar/`, {
    method: 'POST',
    body: formData
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        mAlert(data.message, 'success');
        cargarVisitas();
        if (window.detalleVisitaActual) {
          verDetalleVisita(window.detalleVisitaActual.tipo, window.detalleVisitaActual.id);
        }
      } else {
        mAlert('Error: ' + data.error, 'error');
      }
    })
    .catch(() => mAlert('Error de conexión. Verifique su red e intente de nuevo.', 'error'));
}

async function rechazarDocRevision(tipo, asistenteId, nombre) {
  const obs = await mPrompt('Ingrese las observaciones del rechazo para <strong>' + nombre + '</strong>:', {
    title: 'Rechazar Documentos',
    icon: '<i class="ri-close-circle-line"></i>',
    iconClass: 'cm-error',
    placeholder: 'Motivo del rechazo...',
    confirmText: 'Rechazar',
    confirmClass: 'cm-btn-danger'
  });
  if (obs !== null && obs.trim() !== '') {
    const formData = new FormData();
    formData.append('observaciones', obs);
    addCsrfToFormData(formData);

    fetch(`/gestion/api/asistentes/${tipo}/${asistenteId}/rechazar/`, {
      method: 'POST',
      body: formData
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          mAlert(data.message, 'success');
          cargarVisitas();
          if (window.detalleVisitaActual) {
            verDetalleVisita(window.detalleVisitaActual.tipo, window.detalleVisitaActual.id);
          }
        } else {
          mAlert('Error: ' + data.error, 'error');
        }
      })
      .catch(() => mAlert('Error de conexión. Verifique su red e intente de nuevo.', 'error'));
  } else if (obs === '') {
    mAlert('Debe proporcionar observaciones al rechazar documentos.', 'warning');
  }
}

document.addEventListener('DOMContentLoaded', function () {
  const modalDetalle = document.getElementById('modalDetalleVisita');
  const modalDoc = document.getElementById('modalVisualizarDoc');

  if (modalDetalle) {
    modalDetalle.addEventListener('click', function (e) {
      if (e.target === this) cerrarModalDetalle();
    });
  }

  if (modalDoc) {
    modalDoc.addEventListener('click', function (e) {
      if (e.target === this) cerrarModalVisualizarDoc();
    });
  }
});
