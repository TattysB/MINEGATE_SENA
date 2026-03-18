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

let _docxPreviewLoaderPromiseVisitas = null;

function _loadScriptOnceVisitas(src) {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      if (existing.getAttribute('data-loaded') === 'true') { resolve(); return; }
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error(`No se pudo cargar ${src}`)), { once: true });
      return;
    }
    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.onload = () => { script.setAttribute('data-loaded', 'true'); resolve(); };
    script.onerror = () => reject(new Error(`No se pudo cargar ${src}`));
    document.head.appendChild(script);
  });
}

function _ensureDocxPreviewReadyVisitas() {
  if (window.docx && window.JSZip) return Promise.resolve();
  if (_docxPreviewLoaderPromiseVisitas) return _docxPreviewLoaderPromiseVisitas;
  _docxPreviewLoaderPromiseVisitas = _loadScriptOnceVisitas('https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js')
    .then(() => _loadScriptOnceVisitas('https://cdn.jsdelivr.net/npm/docx-preview@0.3.3/dist/docx-preview.min.js'))
    .finally(() => { if (!(window.docx && window.JSZip)) _docxPreviewLoaderPromiseVisitas = null; });
  return _docxPreviewLoaderPromiseVisitas;
}

function _extraerNombreDesdeContentDispositionVisitas(contentDisposition) {
  if (!contentDisposition) return '';

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match && utf8Match[1]) {
    try {
      return decodeURIComponent(utf8Match[1]).replace(/['"]/g, '').trim();
    } catch (error) {
      return utf8Match[1].replace(/['"]/g, '').trim();
    }
  }

  const basicMatch = contentDisposition.match(/filename=\"?([^\";]+)\"?/i);
  return basicMatch && basicMatch[1] ? basicMatch[1].trim() : '';
}

function _inferirExtensionDesdeMimeVisitas(contentType) {
  if (!contentType) return '';
  const mime = contentType.toLowerCase();
  if (mime.includes('wordprocessingml.document')) return 'docx';
  if (mime.includes('application/pdf')) return 'pdf';
  if (mime.includes('image/jpeg')) return 'jpg';
  if (mime.includes('image/png')) return 'png';
  if (mime.includes('image/gif')) return 'gif';
  if (mime.includes('image/webp')) return 'webp';
  if (mime.includes('image/bmp')) return 'bmp';
  if (mime.includes('image/svg+xml')) return 'svg';
  return '';
}

let tipoVisitaActual = 'internas';

function esUsuarioSst() {
  return Boolean(window.panelPermisos && window.panelPermisos.soloSst);
}

function cambiarTabVisita(tipo) {
  tipoVisitaActual = tipo;
  document.querySelectorAll('.tab-visita').forEach(tab => {
    if (tab.getAttribute('data-tipo') === tipo) {
      tab.style.background = '#059669';
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

  tbody.innerHTML = `<tr><td colspan="8" class="docs-cargando">
      <i class="ri-loader-4-line"></i>
      <p>Cargando visitas...</p>
    </td></tr>`;

  fetch(`/gestion/visitas/?tipo=${tipoVisitaActual}&estado=${estado}&buscar=${encodeURIComponent(buscar)}`)
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
        tbody.innerHTML = `<tr><td colspan="8" class="docs-vacio">
            <i class="ri-inbox-line"></i>
            <p>No hay visitas para mostrar</p>
          </td></tr>`;
        return;
      }

      let html = '';
      data.visitas.forEach(v => {
        const estadoBadge = getEstadoBadge(v.estado);
        html += `<tr class="docs-fila gv-fila">
            <td class="gv-celda-id">#${v.id}</td>
            <td>
              <span class="gv-tipo-badge ${v.tipo === 'interna' ? 'interna' : 'externa'}">
                ${v.tipo === 'interna' ? '📋 Interna' : '🏢 Externa'}
              </span>
            </td>
            <td>
              <div class="gv-responsable">${v.responsable}</div>
              <div class="docs-celda-texto">${v.correo}</div>
            </td>
            <td class="docs-celda-texto">${v.institucion}</td>
            <td class="docs-celda-texto">${v.fecha_visita}</td>
            <td class="gv-celda-cantidad">${v.cantidad}</td>
            <td>${estadoBadge}</td>
            <td class="docs-celda-acciones gv-celda-acciones">
              ${getAccionesVisita(v)}
            </td>
          </tr>`;
      });
      tbody.innerHTML = html;
    })
    .catch(() => {
      tbody.innerHTML = `<tr><td colspan="8" class="docs-error">
          <i class="ri-error-warning-line" style="font-size: 40px;"></i>
          <p>Error al cargar las visitas</p>
        </td></tr>`;
    });
}

function getEstadoBadge(estado) {
  const badges = {
    'enviada_coordinacion': '<span class="gv-estado-pill gv-estado-enviada"><i class="ri-time-line"></i> Pendiente coordinación</span>',
    'pendiente': '<span class="gv-estado-pill gv-estado-pendiente"><i class="ri-hourglass-line"></i> Pendiente</span>',
    'aprobada_inicial': '<span class="gv-estado-pill gv-estado-aprobada"><i class="ri-check-double-line"></i> Aprobada inicial</span>',
    'documentos_enviados': '<span class="gv-estado-pill gv-estado-docs"><i class="ri-file-upload-line"></i> Docs enviados</span>',
    'en_revision_documentos': '<span class="gv-estado-pill gv-estado-revision"><i class="ri-search-eye-line"></i> En revisión</span>',
    'reprogramacion_solicitada': '<span class="gv-estado-pill gv-estado-reprogramacion"><i class="ri-calendar-2-line"></i> Reprogramación solicitada</span>',
    'confirmada': '<span class="gv-estado-pill gv-estado-confirmada"><i class="ri-verified-badge-line"></i> Confirmada</span>',
    'rechazada': '<span class="gv-estado-pill gv-estado-rechazada"><i class="ri-close-circle-line"></i> Rechazada</span>',
  };
  return badges[estado] || `<span class="gv-estado-pill">${estado}</span>`;
}

function puedeSolicitarReprogramacionAdmin(estado) {
  return ['pendiente', 'aprobada_inicial', 'documentos_enviados', 'en_revision_documentos'].includes(estado);
}

function puedeDevolverCorreccion(estado, tieneRechazos) {
  return Boolean(tieneRechazos) && ['documentos_enviados', 'en_revision_documentos'].includes(estado);
}

function getEstadoDocumentoBadge(estado) {
  const badges = {
    'pendiente_documentos': '<span style="background:#fef3c7;color:#92400e;padding:3px 8px;border-radius:15px;font-size:10px;">⏳ Pendiente</span>',
    'documentos_aprobados': '<span style="background:#d1fae5;color:#065f46;padding:3px 8px;border-radius:15px;font-size:10px;">✅ Aprobados</span>',
    'documentos_rechazados': '<span style="background:#fee2e2;color:#991b1b;padding:3px 8px;border-radius:15px;font-size:10px;">⚠️ Pendiente corrección</span>',
  };
  return badges[estado] || estado;
}

function getBadgeRevisionDocumento(ds, opts = {}) {
  const fontSize = opts.fontSize || '9px';
  const padding = opts.padding || '1px 5px';
  const borderRadius = opts.borderRadius || '4px';
  const marginLeft = opts.marginLeft || '4px';
  const badges = [];

  if (ds.estado === 'aprobado') {
    badges.push(`<span style="background:#d1fae5;color:#065f46;font-size:${fontSize};padding:${padding};border-radius:${borderRadius};margin-left:${marginLeft};">Aprobado</span>`);
  } else if (ds.estado === 'rechazado') {
    badges.push(`<span style="background:#fee2e2;color:#991b1b;font-size:${fontSize};padding:${padding};border-radius:${borderRadius};margin-left:${marginLeft};">Rechazado</span>`);
  }

  if (ds.es_reenvio) {
    const versiones = parseInt(ds.versiones_envio || 2, 10);
    badges.push(`<span style="background:#e0f2fe;color:#075985;font-size:${fontSize};padding:${padding};border-radius:${borderRadius};margin-left:${marginLeft};" title="Documento reenviado ${versiones} veces">🔁 Reenvío</span>`);
  }

  return badges.join('');
}

function normalizarCategoriaTexto(value) {
  return String(value || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

function esCategoriaArchivoFinal(categoria) {
  const cat = normalizarCategoriaTexto(categoria);
  if (cat.includes('ats')) return true;
  if (cat.includes('induccion y reinduccion')) return true;
  return cat.includes('charla de seguridad') && (cat.includes('calestenia') || cat.includes('calistenia'));
}

function getAccionesVisita(v) {
  const acciones = [
    `<button type="button" onclick="verDetalleVisita('${v.tipo}', ${v.id})" class="docs-btn-accion docs-btn-ver gv-btn-base">
      <i class="ri-eye-line"></i> Ver
    </button>`
  ];

  if (esUsuarioSst()) {
    if (v.estado === 'documentos_enviados' || v.estado === 'en_revision_documentos') {
      acciones.push(`<button type="button" onclick="verDetalleVisita('${v.tipo}', ${v.id})" class="docs-btn-accion gv-btn-docs">
        <i class="ri-file-search-line"></i> Revisar docs
      </button>`);
    } else {
      acciones.push('<span class="gv-pill-info gv-pill-espera"><i class="ri-lock-line"></i> Solo revisión documental</span>');
    }
    return `<div class="docs-acciones gv-acciones">${acciones.join('')}</div>`;
  }

  if (v.estado === 'enviada_coordinacion') {
    acciones.push('<span class="gv-pill-info gv-pill-espera"><i class="ri-time-line"></i> Esperando coordinación</span>');
    return `<div class="docs-acciones gv-acciones">${acciones.join('')}</div>`;
  }

  if (v.estado === 'pendiente') {
    acciones.push(`<button type="button" onclick="accionVisita('${v.tipo}', ${v.id}, 'aprobar')" class="docs-btn-accion gv-btn-approve">
      <i class="ri-check-line"></i> Aprobar
    </button>`);
    acciones.push(`<button type="button" onclick="accionVisita('${v.tipo}', ${v.id}, 'rechazar')" class="docs-btn-accion gv-btn-reject" title="Rechazar visita">
      <i class="ri-close-line"></i>
    </button>`);
  }

  if (puedeSolicitarReprogramacionAdmin(v.estado)) {
    acciones.push(`<button type="button" onclick="solicitarReprogramacionVisita('${v.tipo}', ${v.id})" class="docs-btn-accion gv-btn-reschedule">
      <i class="ri-calendar-schedule-line"></i> Reprogramar
    </button>`);
  }

  if (v.estado === 'documentos_enviados') {
    acciones.push(`<button type="button" onclick="verDetalleVisita('${v.tipo}', ${v.id})" class="docs-btn-accion gv-btn-docs">
      <i class="ri-file-search-line"></i> Revisar docs
    </button>`);
    acciones.push(`<button type="button" onclick="accionVisita('${v.tipo}', ${v.id}, 'iniciar_revision')" class="docs-btn-accion gv-btn-review">
      <i class="ri-search-line"></i> Iniciar revisión
    </button>`);
  }

  if (v.estado === 'en_revision_documentos') {
    acciones.push(`<button type="button" onclick="verDetalleVisita('${v.tipo}', ${v.id})" class="docs-btn-accion gv-btn-docs">
      <i class="ri-file-search-line"></i> Revisar docs
    </button>`);

    if (v.puede_confirmar) {
      acciones.push(`<button type="button" onclick="accionVisita('${v.tipo}', ${v.id}, 'confirmar_visita')" class="docs-btn-accion gv-btn-confirm">
        <i class="ri-verified-badge-line"></i> Confirmar
      </button>`);
    } else if (v.tiene_rechazos) {
      acciones.push('<span class="gv-pill-info gv-pill-warning"><i class="ri-error-warning-line"></i> Pendiente corrección</span>');
    } else {
      acciones.push(`<button type="button" onclick="mAlert('No se puede confirmar la visita aún. Asegúrese de que todos los asistentes tengan sus documentos aprobados.', 'warning')" class="docs-btn-accion gv-btn-confirm gv-btn-disabled" title="Documentos pendientes de aprobación">
        <i class="ri-alert-line"></i> Confirmar
      </button>`);
    }
  }

  return `<div class="docs-acciones gv-acciones">${acciones.join('')}</div>`;
}

function filtrarVisitas() {
  const val = document.getElementById('filtroEstadoVisita').value;
  filtrarPorEstado(val);
}

function mostrarVisitasAprobadas() {
  const tbody = document.getElementById('cuerpoTablaVisitas');

  tbody.innerHTML = `<tr><td colspan="8" class="docs-cargando">
      <i class="ri-loader-4-line"></i>
      <p>Cargando visitas aprobadas...</p>
    </td></tr>`;

  fetch(`/gestion/visitas-aprobadas/?tipo=${tipoVisitaActual}`)
    .then(response => response.json())
    .then(data => {
      const visitas = data.visitas || [];

      if (visitas.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="docs-vacio">
            <i class="ri-inbox-line"></i>
            <p>No hay visitas aprobadas</p>
          </td></tr>`;
        return;
      }

      let html = '';
      visitas.forEach(v => {
        const estadoBadge = getEstadoBadge(v.estado);
        html += `<tr class="docs-fila gv-fila">
            <td class="gv-celda-id">#${v.id}</td>
            <td>
              <span class="gv-tipo-badge ${v.tipo === 'interna' ? 'interna' : 'externa'}">${v.tipo_display}</span>
            </td>
            <td>
              <div class="gv-responsable">${v.responsable}</div>
              <div class="docs-celda-texto">${v.correo || 'N/A'}</div>
            </td>
            <td class="docs-celda-texto">${v.institucion}</td>
            <td class="docs-celda-texto">${v.fecha_visita || 'N/A'}</td>
            <td class="gv-celda-cantidad">${v.cantidad || 0}</td>
            <td>${estadoBadge}</td>
            <td class="docs-celda-acciones gv-celda-acciones">
              <button type="button" onclick="verDetalleVisita('${v.tipo}', ${v.id})" class="docs-btn-accion docs-btn-ver gv-btn-base">
                <i class="ri-eye-line"></i> Ver detalles
              </button>
            </td>
          </tr>`;
      });
      tbody.innerHTML = html;
    })
    .catch(() => {
      tbody.innerHTML = `<tr><td colspan="8" class="docs-error" style="padding:20px;">
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
      subtitulo: 'Archivos pendientes de revisión o corrección',
      color: '#f59e0b',
      queryParams: 'estado_asistente=revision_activa',
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
  fetch(`/gestion/documentos-revision/?${cfg.queryParams}${tipoParam}`)
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

        // Extraer y mostrar documentos finales de toda la visita (ultima version por categoria+titulo)
        const finalesPorClave = {};
        visita.asistentes.forEach(asistente => {
          (asistente.documentos_subidos || []).forEach(ds => {
            if (!esCategoriaArchivoFinal(ds.categoria)) return;
            const clave = `${(ds.categoria || '').trim()}::${(ds.titulo || '').trim()}`;
            if (!finalesPorClave[clave] || Number(ds.id) > Number(finalesPorClave[clave].id)) {
              finalesPorClave[clave] = ds;
            }
          });
        });
        let documentos_finales_visita = Object.values(finalesPorClave);
        documentos_finales_visita.sort((a, b) => {
          const catCmp = String(a.categoria || '').localeCompare(String(b.categoria || ''));
          if (catCmp !== 0) return catCmp;
          return String(a.titulo || '').localeCompare(String(b.titulo || ''));
        });

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
            const badgeDoc = getBadgeRevisionDocumento(ds);
            const observacionFinal = ds.estado === 'rechazado' && ds.observaciones_revision
              ? `<div style="margin-top:4px;padding:6px 10px;background:#fff7ed;border:1px solid #fdba74;border-radius:6px;color:#9a3412;font-size:11px;display:flex;align-items:flex-start;gap:5px;"><i class="ri-error-warning-line" style="flex-shrink:0;"></i><span>${ds.observaciones_revision}</span></div>`
              : '';

            html += `
              <div>
                <div style="display:flex;justify-content:space-between;align-items:center;width:100%;gap:10px;">
                  <div style="display:flex;gap:4px;align-items:center;">
                        <button onclick="visualizarDocumento('${ds.url}', '${ds.titulo} - ${visita.responsable}', {id: ${ds.id}, estado: '${ds.estado}', nombre_archivo: '${(ds.nombre_archivo || '').replace(/'/g, '')}'})" 
                            style="background:linear-gradient(135deg,#059669,#047857);color:white;padding:5px 12px;border-radius:6px;border:none;cursor:pointer;font-size:11px;display:inline-flex;align-items:center;gap:4px;font-weight:600;">
                      <i class="ri-file-text-line"></i> ${ds.titulo}
                    </button>
                    <a href="${ds.download_url || ds.url}" download style="background:#f3f4f6;color:#374151;padding:5px 8px;border-radius:6px;text-decoration:none;font-size:11px;display:inline-flex;align-items:center;border:1px solid #e5e7eb;" title="Descargar">
                      <i class="ri-download-2-line"></i>
                    </a>
                  </div>
                  ${badgeDoc}
                </div>
                ${observacionFinal}
              </div>`;
          });

          const documentosFinalesRechazados = documentos_finales_visita.filter(ds => ds.estado === 'rechazado');
          if (documentosFinalesRechazados.length > 0) {
            const nombresDocsRechazados = documentosFinalesRechazados.map(ds => ds.titulo).join(', ');
            html += `
              <div style="margin-top:8px;display:flex;align-items:center;flex-wrap:wrap;gap:6px;padding:6px 10px;background:#fff7ed;border:1px solid #fca5a5;border-radius:6px;border-left:3px solid #ef4444;">
                <i class="ri-alert-fill" style="color:#ef4444;font-size:13px;"></i>
                <span style="color:#9a3412;font-size:12px;font-weight:600;">Archivo final rechazado: ${nombresDocsRechazados}</span>
              </div>`;
          }

          html += `
              </div>
            </div>`;
        }

        visita.asistentes.forEach(a => {
          // Si solo falló un archivo final (ATS/inducción/charla), no marcar al asistente como rechazado.
          const documentosSubidosAsistente = a.documentos_subidos || [];
          const documentosPersonalesAsistente = documentosSubidosAsistente.filter(ds =>
            !esCategoriaArchivoFinal(ds.categoria)
          );
          const tieneRechazosPersonales = a.estado === 'documentos_rechazados' &&
            documentosPersonalesAsistente.some(ds => ds.estado === 'rechazado');

          let aBadge = '';
          let borderLeft = '#d1d5db';
          if (a.estado === 'pendiente_documentos') {
            aBadge = '<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:12px;font-size:10px;font-weight:600;">⏳ Pendiente</span>';
            borderLeft = '#f59e0b';
          } else if (a.estado === 'documentos_aprobados') {
            aBadge = '<span style="background:#d1fae5;color:#065f46;padding:2px 8px;border-radius:12px;font-size:10px;font-weight:600;">✅ Aprobado</span>';
            borderLeft = '#10b981';
          } else if (tieneRechazosPersonales) {
            aBadge = '<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:12px;font-size:10px;font-weight:600;">⚠️ Pendiente corrección</span>';
            borderLeft = '#ef4444';
          } else if (a.estado === 'documentos_rechazados') {
            aBadge = '<span style="background:#e2e8f0;color:#334155;padding:2px 8px;border-radius:12px;font-size:10px;font-weight:600;">ℹ️ Sin novedad personal</span>';
            borderLeft = '#94a3b8';
          }

          let botonesDoc = '';
          if (a.documento_adicional) {
            botonesDoc += `
                  <div style="display:flex;justify-content:space-between;align-items:center;width:100%;gap:10px;">
                    <div style="display:flex;gap:4px;align-items:center;">
                            <button onclick="visualizarDocumento('${a.documento_adicional}', 'Doc. Adicional - ${a.nombre_completo}', {estado: '${a.estado === 'documentos_aprobados' ? 'aprobado' : 'pendiente'}', nombre_archivo: '${(a.documento_adicional_nombre || '').replace(/'/g, '')}'})" 
                              style="background:linear-gradient(135deg,#10b981,#059669);color:white;padding:5px 12px;border-radius:6px;border:none;cursor:pointer;font-size:11px;display:inline-flex;align-items:center;gap:4px;font-weight:600;">
                        <i class="ri-file-copy-2-line"></i> Doc. Adicional
                      </button>
                      <a href="${a.documento_adicional}" download style="background:#f3f4f6;color:#374151;padding:5px 8px;border-radius:6px;text-decoration:none;font-size:11px;display:inline-flex;align-items:center;border:1px solid #e5e7eb;" title="Descargar">
                        <i class="ri-download-2-line"></i>
                      </a>
                    </div>
                    ${a.estado === 'documentos_aprobados' ? '<span style="background:#d1fae5;color:#065f46;font-size:11px;padding:3px 10px;border-radius:6px;font-weight:600;">Aprobado</span>' : (tieneRechazosPersonales ? '<span style="background:#fee2e2;color:#991b1b;font-size:11px;padding:3px 10px;border-radius:6px;font-weight:600;">Pendiente corrección</span>' : '')}
                  </div>`;
          }
          if (a.documentos_subidos && a.documentos_subidos.length > 0) {
            // Filtrar SOLO documentos que NO sean los archivos finales (para evitar duplicados)
            const documentos_personales = a.documentos_subidos.filter(ds =>
              !esCategoriaArchivoFinal(ds.categoria)
            );

            // Mostrar solo documentos personales del asistente (no los finales)
            documentos_personales.forEach(ds => {
              const badgeDoc = getBadgeRevisionDocumento(ds);

              botonesDoc += `
                  <div style="display:flex;justify-content:space-between;align-items:center;width:100%;gap:10px;">
                    <div style="display:flex;gap:4px;align-items:center;">
                            <button onclick="visualizarDocumento('${ds.url}', '${ds.titulo} - ${a.nombre_completo}', {id: ${ds.id}, estado: '${ds.estado}', nombre_archivo: '${(ds.nombre_archivo || '').replace(/'/g, '')}'})" 
                              style="background:linear-gradient(135deg,#059669,#047857);color:white;padding:5px 12px;border-radius:6px;border:none;cursor:pointer;font-size:11px;display:inline-flex;align-items:center;gap:4px;font-weight:600;">
                        <i class="ri-file-text-line"></i> ${ds.titulo}
                      </button>
                      <a href="${ds.download_url || ds.url}" download style="background:#f3f4f6;color:#374151;padding:5px 8px;border-radius:6px;text-decoration:none;font-size:11px;display:inline-flex;align-items:center;border:1px solid #e5e7eb;" title="Descargar">
                        <i class="ri-download-2-line"></i>
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
                  <button onclick="event.stopPropagation();rechazarDocDesdeListado('${a.visita_tipo}', ${a.asistente_id}, '${a.nombre_completo.replace(/'/g, "\\\'")}', '${filtro}')" 
                          style="background:linear-gradient(135deg,#ef4444,#dc2626);color:white;border:none;padding:5px 14px;border-radius:6px;cursor:pointer;font-size:11px;font-weight:600;display:inline-flex;align-items:center;gap:4px;">
                    <i class="ri-close-line"></i> Rechazar
                  </button>
                </div>`;
          }

          let obsHtml = '';
          if (a.observaciones_revision && tieneRechazosPersonales) {
            obsHtml = `<div style="margin-top:6px;padding:6px 10px;background:#fef3c7;border-radius:5px;font-size:11px;color:#92400e;border:1px solid #fcd34d;display:flex;align-items:flex-start;gap:5px;"><i class="ri-sticky-note-2-line"></i><span>${a.observaciones_revision}</span></div>`;
          }

          let advertenciaCorreccionHtml = '';
          if (tieneRechazosPersonales) {
            advertenciaCorreccionHtml = `<div style="margin-top:6px;padding:8px 10px;background:#fff7ed;border-radius:6px;font-size:11px;color:#9a3412;border:1px solid #fdba74;display:flex;align-items:flex-start;gap:6px;">
              <i class="ri-alert-fill" style="flex-shrink:0;margin-top:1px;"></i><span>Este aprendiz tiene documentos rechazados. Solicita al instructor actualizar y volver a subir los archivos.</span>
            </div>`;
          }

          html += `
              <div style="padding:10px 14px;margin:6px 0;background:white;border-radius:8px;border:1px solid #e5e7eb;border-left:4px solid ${borderLeft};box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <div style="display:flex;align-items:center;gap:8px;justify-content:space-between;flex-wrap:wrap;">
                  <div style="display:flex;align-items:center;gap:8px;">
                    <i class="ri-user-line" style="color:#8b5cf6;"></i>
                    <strong style="font-size:13px;">${a.nombre_completo}</strong>
                    <span style="color:#9ca3af;font-size:11px;display:inline-flex;align-items:center;gap:3px;"><i class="ri-id-card-line"></i> ${a.tipo_documento}: ${a.numero_documento}</span>
                    ${aBadge}
                  </div>
                  ${accionesHtml}
                </div>
                <div style="display:flex;flex-direction:column;gap:6px;width:100%;margin-top:8px;">
                  ${botonesDoc}
                </div>
                ${advertenciaCorreccionHtml}
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

  fetch(`/gestion/asistentes/${tipo}/${asistenteId}/aprobar/`, {
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

    fetch(`/gestion/asistentes/${tipo}/${asistenteId}/rechazar/`, {
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

async function visualizarDocumento(url, titulo, extraOptions = null) {
  document.getElementById('tituloVisualizarDoc').textContent = '📄 ' + titulo;
  document.getElementById('descargarDocLink').href = url;
  document.getElementById('abrirNuevaTab').href = url;

  const footer = document.getElementById('footerAccionesDoc');
  const btnAprobar = document.getElementById('btnAprobarIndividual');
  const btnRechazar = document.getElementById('btnRechazarIndividual');

  if (extraOptions && (extraOptions.id || extraOptions.mode === 'autorizacion_padres')) {
    footer.style.display = 'flex';
    const estadoDocumento = extraOptions.estado || 'pendiente';

    if (estadoDocumento === 'aprobado' || estadoDocumento === 'rechazado') {
      btnAprobar.style.setProperty('display', 'none', 'important');
      btnRechazar.style.setProperty('display', 'none', 'important');

      let statusBadge = document.getElementById('statusBadgeViewer');
      if (!statusBadge) {
        statusBadge = document.createElement('span');
        statusBadge.id = 'statusBadgeViewer';
        footer.appendChild(statusBadge);
      }
      statusBadge.style.display = 'inline-block';
      if (estadoDocumento === 'aprobado') {
        statusBadge.innerHTML = '<i class="ri-checkbox-circle-line"></i> DOCUMENTO APROBADO';
        statusBadge.style.cssText = 'background:#10b981;color:white;padding:8px 20px;border-radius:8px;font-weight:700;font-size:14px;display:flex;align-items:center;gap:8px;';
      } else {
        statusBadge.innerHTML = '<i class="ri-close-circle-line"></i> DOCUMENTO RECHAZADO (esperando corrección)';
        statusBadge.style.cssText = 'background:#dc2626;color:white;padding:8px 20px;border-radius:8px;font-weight:700;font-size:14px;display:flex;align-items:center;gap:8px;';
      }
    } else {
      btnAprobar.style.setProperty('display', 'flex', 'important');
      btnRechazar.style.setProperty('display', 'flex', 'important');
      const statusBadge = document.getElementById('statusBadgeViewer');
      if (statusBadge) statusBadge.style.setProperty('display', 'none', 'important');

      if (extraOptions.mode === 'autorizacion_padres') {
        btnAprobar.onclick = () => revisarAutorizacionPadresEnModal(extraOptions.tipo, extraOptions.asistenteId, 'aprobar', extraOptions.nombre || '');
        btnRechazar.onclick = () => revisarAutorizacionPadresEnModal(extraOptions.tipo, extraOptions.asistenteId, 'rechazar', extraOptions.nombre || '');
      } else {
        btnAprobar.onclick = () => revisarDocumentoIndividual(extraOptions.id, 'aprobado');
        btnRechazar.onclick = () => revisarDocumentoIndividual(extraOptions.id, 'rechazado');
      }
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

  // Detectar extensión del archivo
  let nombreArchivo = (extraOptions && extraOptions.nombre_archivo)
    ? extraOptions.nombre_archivo
    : url.split('/').pop().split('?')[0];
  let extension = nombreArchivo.includes('.') ? nombreArchivo.split('.').pop().toLowerCase() : '';

  if (!extension) {
    try {
      const headResponse = await fetch(absoluteUrl, {
        method: 'HEAD',
        credentials: 'same-origin'
      });

      if (headResponse.ok) {
        const disposition = headResponse.headers.get('Content-Disposition') || '';
        const nombreDesdeHeader = _extraerNombreDesdeContentDispositionVisitas(disposition);
        if (nombreDesdeHeader) {
          nombreArchivo = nombreDesdeHeader;
          if (nombreArchivo.includes('.')) {
            extension = nombreArchivo.split('.').pop().toLowerCase();
          }
        }

        if (!extension) {
          extension = _inferirExtensionDesdeMimeVisitas(headResponse.headers.get('Content-Type') || '');
        }
      }
    } catch (error) {
      console.warn('No se pudo inferir la extensión del documento:', error);
    }
  }

  const esDocx = extension === 'docx';

  if (esDocx) {
    const docxContainer = document.createElement('div');
    docxContainer.id = 'docxPreviewContainerVisitas';
    docxContainer.style.cssText = 'width:100%;height:100%;overflow:auto;background:#fff;padding:20px;';
    contenedor.appendChild(docxContainer);

    _ensureDocxPreviewReadyVisitas()
      .then(() => fetch(absoluteUrl, { credentials: 'same-origin' }))
      .then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.arrayBuffer();
      })
      .then(arrayBuffer => {
        loading.style.display = 'none';
        return window.docx.renderAsync(arrayBuffer, docxContainer, null, {
          inWrapper: true, breakPages: true, ignoreWidth: false, ignoreHeight: false,
        });
      })
      .catch(err => {
        console.error('Error previsualizando DOCX:', err);
        loading.style.display = 'none';
        docxContainer.innerHTML = `
          <div style="text-align:center;padding:50px;color:#6b7280;">
            <i class="ri-file-word-line" style="font-size:64px;color:#9ca3af;display:block;margin-bottom:20px;"></i>
            <p style="font-size:16px;color:#374151;margin-bottom:6px;font-weight:500;">No se pudo mostrar el archivo Word</p>
            <p style="font-size:13px;margin-bottom:24px;">Intente descargarlo para abrirlo en Microsoft Word.</p>
            <a href="${url}" target="_blank"
              style="background:#6b7280;color:white;padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:600;display:inline-flex;align-items:center;gap:8px;">
              <i class="ri-external-link-line"></i> Abrir en nueva pestaña
            </a>
          </div>`;
      });
    return;
  }

  const tiposVisualizables = ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'];
  if (!tiposVisualizables.includes(extension) && extension) {
    loading.style.display = 'none';
    const div = document.createElement('div');
    div.style.cssText = 'text-align:center;padding:50px;color:#6b7280;';
    div.innerHTML = `
      <i class="ri-file-text-line" style="font-size:64px;color:#9ca3af;display:block;margin-bottom:20px;"></i>
      <p style="font-size:16px;color:#374151;margin-bottom:6px;font-weight:500;">Vista previa no disponible</p>
      <p style="font-size:13px;margin-bottom:24px;">Los archivos <strong>.${extension.toUpperCase()}</strong> no se pueden mostrar directamente en el navegador.</p>
      <a href="${url}" target="_blank"
         style="background:#6b7280;color:white;padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:600;display:inline-flex;align-items:center;gap:8px;">
        <i class="ri-external-link-line"></i> Abrir en nueva pestaña
      </a>`;
    contenedor.appendChild(div);
    return;
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

async function revisarAutorizacionPadresEnModal(tipo, asistenteId, accion, nombre = '') {
  let observaciones = '';
  if (accion === 'rechazar') {
    observaciones = await mPrompt('Ingrese las observaciones del rechazo para <strong>' + nombre + '</strong>:', {
      title: 'Rechazar Documento',
      icon: '<i class="ri-close-circle-line"></i>',
      iconClass: 'cm-error',
      placeholder: 'Motivo del rechazo...',
      confirmText: 'Rechazar',
      confirmClass: 'cm-btn-danger'
    });
    if (observaciones === null) return;
    if (observaciones.trim() === '') {
      mAlert('Debe proporcionar observaciones al rechazar la autorización.', 'warning');
      return;
    }
  }

  const formData = new FormData();
  formData.append('observaciones', observaciones);
  addCsrfToFormData(formData);

  fetch(`/gestion/api/autorizacion-padres/${tipo}/${asistenteId}/${accion}/`, {
    method: 'POST',
    body: formData
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        mAlert(data.message, 'success');
        cerrarModalVisualizarDoc();
        cargarVisitas();
        if (window.detalleVisitaActual) {
          verDetalleVisita(window.detalleVisitaActual.tipo, window.detalleVisitaActual.id);
        }
      } else {
        mAlert('Error: ' + (data.error || 'No se pudo actualizar el estado'), 'error');
      }
    })
    .catch(() => mAlert('Error de conexión.', 'error'));
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
        cargarVisitas();
        if (window._filtroDocsActual) {
          mostrarDocumentosPorEstado(window._filtroDocsActual);
        }
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
  contenido.innerHTML = '<div style="text-align:center;padding:40px 20px;"><i class="ri-loader-4-line" style="font-size:36px;color:#22c55e;animation:spin 1s linear infinite;"></i><p style="color:#6b7280;margin-top:10px;font-size:14px;">Cargando detalle...</p></div>';
  modal.style.display = 'block';

  fetch(`/gestion/visitas/${tipo}/${id}/`)
    .then(response => response.json())
    .then(data => {
      // Extraer documentos finales de toda la visita (ultima version por categoria+titulo)
      const finalesPorClave = {};
      data.asistentes.forEach(asistente => {
        (asistente.documentos_subidos || []).forEach(ds => {
          if (!esCategoriaArchivoFinal(ds.categoria)) return;
          const clave = `${(ds.categoria || '').trim()}::${(ds.titulo || '').trim()}`;
          if (!finalesPorClave[clave] || Number(ds.id) > Number(finalesPorClave[clave].id)) {
            finalesPorClave[clave] = ds;
          }
        });
      });
      let documentos_finales = Object.values(finalesPorClave);
      documentos_finales.sort((a, b) => {
        const catCmp = String(a.categoria || '').localeCompare(String(b.categoria || ''));
        if (catCmp !== 0) return catCmp;
        return String(a.titulo || '').localeCompare(String(b.titulo || ''));
      });

      // Construir HTML de archivos finales
      let archivosFinalesHtml = '';
      if (documentos_finales.length > 0) {
        archivosFinalesHtml = `
          <div style="background:linear-gradient(135deg,#ecfdf5,#dcfce7);padding:18px;border-radius:12px;border:1px solid #86efac;border-left:5px solid #22c55e;margin-bottom:20px;box-shadow:0 2px 8px rgba(34,197,94,0.12);">
            <h4 style="color:#065f46;margin:0 0 14px 0;display:flex;align-items:center;gap:8px;font-size:14px;font-weight:700;">
              <span style="background:#22c55e;color:white;border-radius:7px;width:28px;height:28px;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;"><i class="ri-folder-open-fill" style="font-size:14px;"></i></span>
              Archivos Finales &mdash; ${data.responsable}
            </h4>
            <div style="display:flex;flex-direction:column;gap:8px;">`;

        documentos_finales.forEach(ds => {
          let badgeDoc = getBadgeRevisionDocumento(ds, {
            fontSize: '11px',
            padding: '3px 10px',
            borderRadius: '6px',
            marginLeft: '0px'
          });
          const observacionFinal = ds.estado === 'rechazado' && ds.observaciones_revision
            ? `<div style="margin-top:6px;padding:8px 10px;background:#fff7ed;border:1px solid #fdba74;border-radius:6px;color:#9a3412;font-size:11px;display:flex;align-items:flex-start;gap:6px;"><i class="ri-error-warning-line" style="flex-shrink:0;margin-top:1px;"></i><span>${ds.observaciones_revision}</span></div>`
            : '';
          if (!badgeDoc) {
            badgeDoc = '<span style="background:#fef3c7;color:#92400e;font-size:11px;padding:3px 10px;border-radius:6px;font-weight:600;">Pendiente</span>';
          }

          archivosFinalesHtml += `
              <div style="background:white;padding:10px 12px;border-radius:8px;border:1px solid #d1fae5;box-shadow:0 1px 3px rgba(0,0,0,0.04);transition:box-shadow .2s;">
                <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
                  <div style="display:flex;gap:6px;align-items:center;">
                        <button onclick="visualizarDocumento('${ds.url}', '${ds.titulo} - ${data.responsable}', {id: ${ds.id}, estado: '${ds.estado}', nombre_archivo: '${(ds.nombre_archivo || '').replace(/'/g, '')}'})" 
                            style="background:linear-gradient(135deg,#22c55e,#16a34a);color:white;padding:7px 14px;border-radius:7px;border:none;cursor:pointer;font-size:12px;display:inline-flex;align-items:center;gap:6px;font-weight:600;box-shadow:0 2px 5px rgba(34,197,94,0.28);">
                      <i class="ri-file-text-line"></i> ${ds.titulo}
                    </button>
                    <a href="${ds.download_url || ds.url}" download style="background:#f3f4f6;color:#374151;padding:7px 10px;border-radius:7px;text-decoration:none;font-size:12px;display:inline-flex;align-items:center;border:1px solid #e5e7eb;" title="Descargar">
                      <i class="ri-download-2-line"></i>
                    </a>
                  </div>
                  ${badgeDoc}
                </div>
                ${observacionFinal}
              </div>`;
        });

        const finalesRechazados = documentos_finales.filter(ds => ds.estado === 'rechazado');
        if (finalesRechazados.length > 0) {
          const nombresFinales = finalesRechazados.map(ds => ds.titulo).join(', ');
          archivosFinalesHtml += `
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;background:#fff7ed;border:1px solid #fca5a5;color:#9a3412;padding:10px 14px;border-radius:8px;border-left:4px solid #ef4444;">
              <i class="ri-alert-fill" style="color:#ef4444;font-size:15px;flex-shrink:0;"></i>
              <span style="font-size:12px;font-weight:600;">Archivo final rechazado: ${nombresFinales}</span>
            </div>`;
        }

        archivosFinalesHtml += `
            </div>
          </div>`;
      }

      let asistentesHtml = '';
      if (data.asistentes.length > 0) {
        asistentesHtml = data.asistentes.map(a => {
          const documentosSubidosAsistente = a.documentos_subidos || [];
          const documentosPersonalesAsistente = documentosSubidosAsistente.filter(ds =>
            !esCategoriaArchivoFinal(ds.categoria)
          );
          const tieneRechazosPersonales = a.estado === 'documentos_rechazados' &&
            documentosPersonalesAsistente.some(ds => ds.estado === 'rechazado');

          let botonesDoc = '';
          let tieneDocs = false;
          if (a.documento_identidad) {
            tieneDocs = true;
            botonesDoc += `
                  <div style="display:flex;justify-content:space-between;align-items:center;width:100%;gap:10px;">
                    <div style="display:flex;gap:4px;align-items:center;">
                            <button onclick="visualizarDocumento('${a.documento_identidad}', 'Documento de Identidad - ${a.nombre_completo}', {estado: '${a.estado === 'documentos_aprobados' ? 'aprobado' : 'pendiente'}', nombre_archivo: '${(a.documento_identidad_nombre || '').replace(/'/g, '')}'})" 
                              style="background:linear-gradient(135deg,#3b82f6,#2563eb);color:white;padding:7px 14px;border-radius:7px;border:none;cursor:pointer;font-size:12px;display:inline-flex;align-items:center;gap:6px;font-weight:600;box-shadow:0 2px 5px rgba(59,130,246,0.25);">
                        <i class="ri-id-card-line"></i> Doc. Identidad
                      </button>
                      <a href="${a.documento_identidad}" download style="background:#f3f4f6;color:#374151;padding:7px 10px;border-radius:7px;text-decoration:none;font-size:12px;display:inline-flex;align-items:center;border:1px solid #e5e7eb;" title="Descargar">
                        <i class="ri-download-2-line"></i>
                      </a>
                    </div>
                    ${a.estado === 'documentos_aprobados' ? '<span style="background:#d1fae5;color:#065f46;font-size:11px;padding:3px 10px;border-radius:6px;font-weight:600;">Aprobado</span>' : (tieneRechazosPersonales ? '<span style="background:#fee2e2;color:#991b1b;font-size:11px;padding:3px 10px;border-radius:6px;font-weight:600;">Pendiente corrección</span>' : '')}
                  </div>`;
          }
          if (a.documento_adicional) {
            tieneDocs = true;
            botonesDoc += `
                  <div style="display:flex;justify-content:space-between;align-items:center;width:100%;gap:10px;">
                    <div style="display:flex;gap:4px;align-items:center;">
                            <button onclick="visualizarDocumento('${a.documento_adicional}', 'Documento Adicional - ${a.nombre_completo}', {estado: '${a.estado === 'documentos_aprobados' ? 'aprobado' : 'pendiente'}', nombre_archivo: '${(a.documento_adicional_nombre || '').replace(/'/g, '')}'})" 
                              style="background:linear-gradient(135deg,#22c55e,#16a34a);color:white;padding:7px 14px;border-radius:7px;border:none;cursor:pointer;font-size:12px;display:inline-flex;align-items:center;gap:6px;font-weight:600;box-shadow:0 2px 5px rgba(34,197,94,0.28);">
                        <i class="ri-file-copy-2-line"></i> Doc. Adicional
                      </button>
                      <a href="${a.documento_adicional}" download style="background:#f3f4f6;color:#374151;padding:7px 10px;border-radius:7px;text-decoration:none;font-size:12px;display:inline-flex;align-items:center;border:1px solid #e5e7eb;" title="Descargar">
                        <i class="ri-download-2-line"></i>
                      </a>
                    </div>
                    ${a.estado === 'documentos_aprobados' ? '<span style="background:#d1fae5;color:#065f46;font-size:11px;padding:3px 10px;border-radius:6px;font-weight:600;">Aprobado</span>' : (tieneRechazosPersonales ? '<span style="background:#fee2e2;color:#991b1b;font-size:11px;padding:3px 10px;border-radius:6px;font-weight:600;">Pendiente corrección</span>' : '')}
                  </div>`;
          }
          if (a.formato_autorizacion_padres) {
            tieneDocs = true;
            let estadoAutPadres = a.estado_autorizacion_padres || 'pendiente';
            let badgeAutPadres = '';

            if (estadoAutPadres === 'aprobado') {
              badgeAutPadres = '<span style="background:#d1fae5;color:#065f46;font-size:10px;padding:2px 8px;border-radius:6px;font-weight:600;margin-left:8px;">Aprobado</span>';
            } else if (estadoAutPadres === 'rechazado') {
              badgeAutPadres = '<span style="background:#fee2e2;color:#991b1b;font-size:10px;padding:2px 8px;border-radius:6px;font-weight:600;margin-left:8px;">Rechazado</span>';
            }

            botonesDoc += `
                  <div style="background:#fef3c7;padding:8px;border-radius:6px;border:2px solid #f59e0b;margin-bottom:6px;width:100%;box-sizing:border-box;">
                    <div style="display:flex;justify-content:space-between;align-items:center;width:100%;gap:10px;">
                      <div style="display:flex;gap:4px;align-items:center;">
                        <button onclick="visualizarDocumento('${a.formato_autorizacion_padres}', 'Formato Autorización Padres - ${a.nombre_completo}', {mode: 'autorizacion_padres', tipo: '${tipo}', asistenteId: ${a.id}, nombre: '${a.nombre_completo.replace(/'/g, "\\'")}', estado: '${estadoAutPadres}', nombre_archivo: '${(a.formato_autorizacion_padres_nombre || '').replace(/'/g, '')}'})" 
                                style="background:linear-gradient(135deg,#f59e0b,#d97706);color:white;padding:7px 14px;border-radius:7px;border:none;cursor:pointer;font-size:12px;display:inline-flex;align-items:center;gap:6px;font-weight:600;box-shadow:0 2px 5px rgba(245,158,11,0.25);">
                          <i class="ri-parent-line"></i> Autorización Padres
                        </button>
                        <a href="${a.formato_autorizacion_padres}" download style="background:#f3f4f6;color:#374151;padding:7px 10px;border-radius:7px;text-decoration:none;font-size:12px;display:inline-flex;align-items:center;border:1px solid #e5e7eb;" title="Descargar">
                          <i class="ri-download-2-line"></i>
                        </a>
                      </div>
                      <div style="display:flex;align-items:center;gap:6px;margin-left:auto;">
                        <span style="background:#fef3c7;color:#78350f;font-size:10px;padding:3px 8px;border-radius:6px;font-weight:600;display:inline-flex;align-items:center;gap:4px;border:1px solid #fcd34d;"><i class="ri-user-heart-line"></i> Menor</span>
                        ${badgeAutPadres}
                      </div>
                    </div>
                    ${a.observaciones_autorizacion_padres ? `<div style="font-size:11px;color:#991b1b;margin-top:6px;display:flex;align-items:flex-start;gap:5px;"><i class="ri-close-circle-fill" style="flex-shrink:0;margin-top:1px;"></i><span>${a.observaciones_autorizacion_padres}</span></div>` : ''}
                  </div>`;
          }
          if (a.documentos_subidos && a.documentos_subidos.length > 0) {
            // Filtrar SOLO documentos que NO sean los archivos finales
            const documentos_personales = a.documentos_subidos.filter(ds =>
              !esCategoriaArchivoFinal(ds.categoria)
            );

            if (documentos_personales.length > 0) {
              tieneDocs = true;
            }

            documentos_personales.forEach(ds => {
              const badgeDoc = getBadgeRevisionDocumento(ds);

              botonesDoc += `
                  <div style="display:flex;justify-content:space-between;align-items:center;width:100%;gap:10px;">
                    <div style="display:flex;gap:4px;align-items:center;">
                            <button onclick="visualizarDocumento('${ds.url}', '${ds.titulo} - ${a.nombre_completo}', {id: ${ds.id}, estado: '${ds.estado}', nombre_archivo: '${(ds.nombre_archivo || '').replace(/'/g, '')}'})" 
                              style="background:linear-gradient(135deg,#22c55e,#16a34a);color:white;padding:7px 14px;border-radius:7px;border:none;cursor:pointer;font-size:12px;display:inline-flex;align-items:center;gap:6px;font-weight:600;box-shadow:0 2px 5px rgba(34,197,94,0.28);">
                        <i class="ri-file-text-line"></i> ${ds.titulo}
                      </button>
                      <a href="${ds.download_url || ds.url}" download style="background:#f3f4f6;color:#374151;padding:7px 10px;border-radius:7px;text-decoration:none;font-size:12px;display:inline-flex;align-items:center;border:1px solid #e5e7eb;" title="Descargar">
                        <i class="ri-download-2-line"></i>
                      </a>
                    </div>
                    ${badgeDoc}
                  </div>
                  ${ds.observaciones_revision ? `<div style="font-size:11px;color:#991b1b;margin-left:4px;margin-top:4px;margin-bottom:2px;display:flex;align-items:flex-start;gap:5px;"><i class="ri-close-circle-fill" style="flex-shrink:0;margin-top:1px;"></i><span>${ds.observaciones_revision}</span></div>` : ''}`;
            });
          }

          if (!tieneDocs) {
            botonesDoc = `<span style="color:#9ca3af;font-size:12px;display:inline-flex;align-items:center;gap:5px;"><i class="ri-inbox-2-line" style="font-size:14px;"></i> Sin documentos subidos aún</span>`;
          }

          let estadoBadge = '';
          let borderColor = '#e5e7eb';
          if (a.estado === 'pendiente_documentos') {
            borderColor = '#f59e0b';
            estadoBadge = '<span style="background:#fef3c7;color:#92400e;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:500;">⏳ Pendiente</span>';
          } else if (a.estado === 'documentos_aprobados') {
            borderColor = '#22c55e';
            estadoBadge = '<span style="background:#d1fae5;color:#065f46;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:500;">✅ Aprobado</span>';
          } else if (tieneRechazosPersonales) {
            borderColor = '#ef4444';
            estadoBadge = '<span style="background:#fee2e2;color:#991b1b;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:500;">⚠️ Pendiente corrección</span>';
          } else if (a.estado === 'documentos_rechazados') {
            borderColor = '#94a3b8';
            estadoBadge = '<span style="background:#e2e8f0;color:#334155;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:500;">ℹ️ Sin novedad personal</span>';
          }

          let accionesDocHtml = '';
          if (a.estado === 'pendiente_documentos' && tieneDocs) {
            let btnAprobarMask = '';

            // Verificar rechazos (incluyendo autorización de padres si existe)
            let hasRechazos = a.tiene_rechazos || a.documentos_subidos.some(ds => ds.estado === 'rechazado');
            if (a.formato_autorizacion_padres && a.estado_autorizacion_padres === 'rechazado') {
              hasRechazos = true;
            }

            // Verificar si todos están aprobados
            let allAprobados = a.todos_aprobados || (tieneDocs && a.documentos_subidos.every(ds => ds.estado === 'aprobado'));

            // Si tiene autorización de padres, debe estar aprobada también
            if (a.formato_autorizacion_padres) {
              if (a.estado_autorizacion_padres !== 'aprobado') {
                allAprobados = false;
              }
            }

            if (hasRechazos) {
              btnAprobarMask = `
                <button onclick="mAlert('No se puede aprobar masivamente porque existen documentos rechazados. El asistente debe corregir los archivos o debe marcarlos todos individualmente.', 'warning')" 
                        style="background:#9ca3af;color:white;border:none;padding:8px 18px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;display:inline-flex;align-items:center;gap:5px;opacity:0.7;">
                  <i class="ri-forbid-line"></i> Rechazos detectados
                </button>`;
            } else if (!allAprobados) {
              btnAprobarMask = `
                <button onclick="mAlert('Debe aprobar individualmente todos los archivos antes de realizar la aprobación final.', 'info')" 
                        style="background:#6b7280;color:white;border:none;padding:8px 18px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;display:inline-flex;align-items:center;gap:5px;opacity:0.7;">
                  <i class="ri-information-line"></i> Pendiente aprobar todo
                </button>`;
            } else {
              btnAprobarMask = `
                <button onclick="event.stopPropagation();aprobarDocRevision('${tipo}', ${a.id})" 
                        style="background:linear-gradient(135deg,#22c55e,#16a34a);color:white;border:none;padding:8px 18px;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;display:inline-flex;align-items:center;gap:5px;transition:all .2s;box-shadow:0 2px 6px rgba(34,197,94,0.32);">
                  <i class="ri-check-double-line"></i> Aprobación Final
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
          } else if (tieneRechazosPersonales) {
            accionesDocHtml = `
                <div style="display:flex;gap:8px;margin-top:12px;padding-top:12px;border-top:1px dashed #d1d5db;align-items:center;flex-wrap:wrap;">
                  <span style="font-size:12px;font-weight:600;color:#9a3412;background:#fff7ed;border:1px solid #fdba74;border-radius:6px;padding:6px 10px;display:inline-flex;align-items:center;gap:6px;"><i class="ri-alert-fill"></i> Requiere actualización de documentos</span>
                </div>`;
          }

          let obsRevHtml = '';
          if (a.observaciones_revision && tieneRechazosPersonales) {
            obsRevHtml = `<div style="margin-top:10px;padding:10px 12px;background:#fef3c7;border-radius:8px;font-size:12px;color:#92400e;border:1px solid #fcd34d;display:flex;align-items:flex-start;gap:7px;"><i class="ri-sticky-note-2-line" style="flex-shrink:0;font-size:14px;margin-top:1px;"></i><span><strong>Observaciones:</strong> ${a.observaciones_revision}</span></div>`;
          }

          return `
              <div style="padding:16px;background:#f9fafb;margin:8px 0;border-radius:12px;border:1px solid ${borderColor};border-left:4px solid ${borderColor};box-shadow:0 2px 8px rgba(0,0,0,0.05);">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                  <div>
                    <div style="display:flex;align-items:center;gap:8px;">
                      <i class="ri-user-line" style="color:#22c55e;"></i>
                      <strong style="font-size:14px;">${a.nombre_completo}</strong>
                      ${estadoBadge}
                    </div>
                    <div style="color:#6b7280;font-size:12px;padding-left:24px;display:flex;align-items:center;gap:4px;"><i class="ri-id-card-line" style="color:#22c55e;"></i> ${a.tipo_documento}: ${a.numero_documento}</div>
                    <div style="display:flex;gap:14px;padding-left:24px;margin-top:4px;flex-wrap:wrap;">
                      ${a.correo ? `<span style="color:#6b7280;font-size:12px;display:inline-flex;align-items:center;gap:4px;"><i class="ri-mail-line" style="color:#22c55e;"></i> ${a.correo}</span>` : ''}
                      ${a.telefono ? `<span style="color:#6b7280;font-size:12px;display:inline-flex;align-items:center;gap:4px;"><i class="ri-phone-line" style="color:#22c55e;"></i> ${a.telefono}</span>` : ''}
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
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:18px;background:linear-gradient(135deg,#f8fafc,#f1f5f9);padding:16px;border-radius:12px;border:1px solid #e2e8f0;">
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="background:#22c55e;color:white;border-radius:6px;width:24px;height:24px;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;"><i class="ri-user-3-line" style="font-size:13px;"></i></span>
              <div><span style="font-size:11px;color:#6b7280;display:block;">Responsable</span><strong style="font-size:13px;color:#111827;">${data.responsable}</strong></div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="background:#22c55e;color:white;border-radius:6px;width:24px;height:24px;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;"><i class="ri-checkbox-circle-line" style="font-size:13px;"></i></span>
              <div><span style="font-size:11px;color:#6b7280;display:block;">Estado</span>${getEstadoBadge(data.estado)}</div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="background:#22c55e;color:white;border-radius:6px;width:24px;height:24px;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;"><i class="ri-building-4-line" style="font-size:13px;"></i></span>
              <div><span style="font-size:11px;color:#6b7280;display:block;">${tipo === 'interna' ? 'Programa' : 'Institución'}</span><strong style="font-size:13px;color:#111827;">${data.programa || data.institucion || 'N/A'}</strong></div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="background:#22c55e;color:white;border-radius:6px;width:24px;height:24px;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;"><i class="ri-calendar-2-line" style="font-size:13px;"></i></span>
              <div><span style="font-size:11px;color:#6b7280;display:block;">Fecha de la visita</span><strong style="font-size:13px;color:#111827;">${data.fecha_visita || data.fecha_solicitud}</strong></div>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="background:#22c55e;color:white;border-radius:6px;width:24px;height:24px;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;"><i class="ri-time-line" style="font-size:13px;"></i></span>
              <div><span style="font-size:11px;color:#6b7280;display:block;">Registrada</span><strong style="font-size:13px;color:#111827;">${data.fecha_registro || data.fecha_solicitud}</strong></div>
            </div>
          </div>
          
          ${archivosFinalesHtml}
          
          <h4 style="color:#374151;border-bottom:2px solid #22c55e;padding-bottom:10px;margin-bottom:12px;display:flex;align-items:center;gap:8px;">
            <span style="background:#22c55e;color:white;border-radius:7px;width:28px;height:28px;display:inline-flex;align-items:center;justify-content:center;"><i class="ri-group-line" style="font-size:14px;"></i></span>
            Asistentes Registrados
            <span style="background:#bbf7d0;color:#166534;padding:3px 12px;border-radius:12px;font-size:12px;font-weight:600;border:1px solid #4ade80;">${data.asistentes.length} asistente(s)</span>
          </h4>
          
          ${data.asistentes.length > 0
          ? `<div style="max-height:460px;overflow-y:auto;padding-right:2px;">${asistentesHtml}</div>`
          : `<div style="text-align:center;padding:36px;color:#9ca3af;background:#f9fafb;border-radius:12px;border:2px dashed #e5e7eb;">
                <i class="ri-user-add-line" style="font-size:40px;margin-bottom:8px;display:block;"></i>
                <p style="margin:0;font-size:14px;">No hay asistentes registrados aún</p>
              </div>`
        }
        `;
      contenido.innerHTML = html;

      window.detalleVisitaActual = data;
    })
    .catch(() => {
      contenido.innerHTML = '<div style="text-align:center;padding:30px;color:#ef4444;"><i class="ri-error-warning-line" style="font-size:30px;"></i><p>Error al cargar el detalle</p></div>';
    });
}

function revisarDocumento(tipo, asistente_id, accion, observaciones = '') {
  const formData = new FormData();
  formData.append('observaciones', observaciones);
  addCsrfToFormData(formData);

  fetch(`/gestion/asistentes/${tipo}/${asistente_id}/${accion}/`, {
    method: 'POST',
    body: formData
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        mAlert(data.message, 'success');
        cargarVisitas();
        if (window._filtroDocsActual) {
          mostrarDocumentosPorEstado(window._filtroDocsActual);
        }
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
  if (esUsuarioSst()) {
    mAlert('Tu rol SST solo puede revisar documentos.', 'warning');
    return;
  }

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
  if (accion === 'devolver_correccion') {
    const ok = await mConfirm('¿Devolver esta visita al instructor para que actualice documentos rechazados?', {
      title: 'Devolver a Corrección',
      icon: '<i class="ri-arrow-go-back-line"></i>',
      iconClass: 'cm-warning',
      confirmText: 'Sí, devolver',
      confirmClass: 'cm-btn-warning'
    });
    if (!ok) return;
  }

  const formData = new FormData();
  formData.append('observaciones', observaciones);

  fetch(`/gestion/visitas/${tipo}/${id}/${accion}/`, {
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

async function solicitarReprogramacionVisita(tipo, id) {
  if (esUsuarioSst()) {
    mAlert('Tu rol SST no tiene permitido solicitar reprogramaciones.', 'warning');
    return;
  }

  const motivo = await mPrompt('Indique el motivo para solicitar reprogramación al instructor:', {
    title: 'Solicitar Reprogramación',
    icon: '<i class="ri-calendar-event-line"></i>',
    iconClass: 'cm-warning',
    placeholder: 'Ejemplo: conflicto de agenda, capacidad, mantenimiento... ',
    confirmText: 'Solicitar',
    confirmClass: 'cm-btn-warning'
  });

  if (motivo === null) return;
  if (!motivo.trim()) {
    mAlert('Debe ingresar un motivo para solicitar la reprogramación.', 'warning');
    return;
  }

  const formData = new FormData();
  formData.append('motivo', motivo.trim());
  addCsrfToFormData(formData);

  fetch(`/gestion/reprogramacion/solicitar/${tipo}/${id}/`, {
    method: 'POST',
    body: formData
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        mAlert(data.message, 'success');
        cargarVisitas();
        if (window._filtroDocsActual) {
          mostrarDocumentosPorEstado(window._filtroDocsActual);
        }
        if (window.detalleVisitaActual) {
          verDetalleVisita(window.detalleVisitaActual.tipo, window.detalleVisitaActual.id);
        }
      } else {
        mAlert('Error: ' + (data.message || data.error || 'No se pudo solicitar la reprogramación'), 'error');
      }
    })
    .catch(() => mAlert('Error de conexión. Verifique su red e intente de nuevo.', 'error'));
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

  fetch(`/gestion/asistentes/${tipo}/${asistenteId}/aprobar/`, {
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

  async function aprobarAutorizacionPadres(tipo, asistenteId) {
    const ok = await mConfirm('¿Aprobar la Autorización de Padres de Familia de este asistente?', {
      title: 'Aprobar Autorización',
      icon: '<i class="ri-check-double-line"></i>',
      iconClass: 'cm-success',
      confirmText: 'Sí, aprobar',
      confirmClass: 'cm-btn-success'
    });
    if (!ok) return;

    const formData = new FormData();
    formData.append('observaciones', '');
    addCsrfToFormData(formData);

    fetch(`/gestion/api/autorizacion-padres/${tipo}/${asistenteId}/aprobar/`, {
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

  async function rechazarAutorizacionPadres(tipo, asistenteId, nombre) {
    const obs = await mPrompt('Ingrese las observaciones del rechazo de la Autorización de Padres para <strong>' + nombre + '</strong>:', {
      title: 'Rechazar Autorización',
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

      fetch(`/gestion/api/autorizacion-padres/${tipo}/${asistenteId}/rechazar/`, {
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
      mAlert('Debe proporcionar observaciones al rechazar la autorización.', 'warning');
    }
  }
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

    fetch(`/gestion/asistentes/${tipo}/${asistenteId}/rechazar/`, {
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
