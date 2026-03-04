if (typeof window.getCsrfToken !== 'function') {
  window.getCsrfToken = function () {
    const match = document.cookie.match(/(^|;)\s*csrftoken\s*=\s*([^;]+)/);
    return match ? match.pop() : '';
  };
}

if (typeof window.addCsrfToFormData !== 'function') {
  window.addCsrfToFormData = function (formData) {
    const token = window.getCsrfToken();
    if (token) {
      formData.append('csrfmiddlewaretoken', token);
    }
  };
}

function mostrarDocumentosPorEstado(filtro) {
  const inlineContainer = document.getElementById('contenedorInlineDocs');
  const tablaContainer = document.getElementById('contenedorTablaVisitas');
  const contenido = document.getElementById('contenidoInlineDocs');
  const titulo = document.getElementById('tituloInlineDocs');
  const subtitulo = document.getElementById('subtituloInlineDocs');
  const statsDiv = document.getElementById('statsInlineDocs');

  if (!inlineContainer || !tablaContainer || !contenido || !titulo || !subtitulo || !statsDiv) return;

  const configs = {
    'revision': {
      titulo: '🔍 Documentos Pendientes de Revisión',
      subtitulo: 'Archivos que aún necesitan ser revisados',
      queryParams: 'estado_asistente=pendiente_documentos',
    },
    'enviados': {
      titulo: '📄 Documentos Enviados',
      subtitulo: 'Todos los archivos que han sido enviados por los asistentes',
      queryParams: '',
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

  const tipoParam = window.tipoVisitaActual ? `&tipo=${window.tipoVisitaActual}` : '';
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
            fecha: d.visita_fecha,
            asistentes: []
          };
        }
        visitasMap[key].asistentes.push(d);
      });

      let html = '';
      Object.values(visitasMap).forEach(visita => {
        const visitaBadge = window.getEstadoBadge ? window.getEstadoBadge(visita.estado) : visita.estado;
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
                </div>
              </div>
              <div style="padding:12px 18px;">`;

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
                  </div>`;
          }

          if (a.documentos_subidos && a.documentos_subidos.length > 0) {
            a.documentos_subidos.forEach(ds => {
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
  const inline = document.getElementById('contenedorInlineDocs');
  const tabla = document.getElementById('contenedorTablaVisitas');
  const filtro = document.getElementById('filtroEstadoVisita');

  if (inline) inline.style.display = 'none';
  if (tabla) tabla.style.display = '';
  if (filtro) filtro.value = 'todos';

  if (typeof window.cargarVisitas === 'function') {
    window.cargarVisitas();
  }
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
  window.addCsrfToFormData(formData);

  fetch(`/gestion/api/asistentes/${tipo}/${asistenteId}/aprobar/`, {
    method: 'POST',
    body: formData
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        mAlert(data.message, 'success');
        if (typeof window.cargarVisitas === 'function') window.cargarVisitas();
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

  if (obs === '') {
    mAlert('Debe proporcionar observaciones al rechazar documentos.', 'warning');
    return;
  }
  if (obs === null || obs.trim() === '') return;

  const formData = new FormData();
  formData.append('observaciones', obs);
  window.addCsrfToFormData(formData);

  fetch(`/gestion/api/asistentes/${tipo}/${asistenteId}/rechazar/`, {
    method: 'POST',
    body: formData
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        mAlert(data.message, 'success');
        if (typeof window.cargarVisitas === 'function') window.cargarVisitas();
        mostrarDocumentosPorEstado(filtroActual);
      } else {
        mAlert('Error: ' + data.error, 'error');
      }
    })
    .catch(() => mAlert('Error de conexión.', 'error'));
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
  if (url.startsWith('/')) absoluteUrl = window.location.origin + url;

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
  window.addCsrfToFormData(formData);

  fetch(`/documentos/api/revisar-asistente/${docSubidoId}/`, {
    method: 'POST',
    body: formData
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        mAlert(data.message, 'success');
        cerrarModalVisualizarDoc();
        if (window.detalleVisitaActual && typeof window.verDetalleVisita === 'function') {
          window.verDetalleVisita(window.detalleVisitaActual.tipo, window.detalleVisitaActual.id);
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

function revisarDocumento(tipo, asistente_id, accion, observaciones = '') {
  const formData = new FormData();
  formData.append('observaciones', observaciones);
  window.addCsrfToFormData(formData);

  fetch(`/gestion/api/asistentes/${tipo}/${asistente_id}/${accion}/`, {
    method: 'POST',
    body: formData
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        mAlert(data.message, 'success');
        if (window.detalleVisitaActual && typeof window.verDetalleVisita === 'function') {
          window.verDetalleVisita(window.detalleVisitaActual.tipo, window.detalleVisitaActual.id);
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
  window.addCsrfToFormData(formData);

  fetch(`/gestion/api/asistentes/${tipo}/${asistenteId}/aprobar/`, {
    method: 'POST',
    body: formData
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        mAlert(data.message, 'success');
        if (typeof window.cargarVisitas === 'function') window.cargarVisitas();
        if (window.detalleVisitaActual && typeof window.verDetalleVisita === 'function') {
          window.verDetalleVisita(window.detalleVisitaActual.tipo, window.detalleVisitaActual.id);
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
    window.addCsrfToFormData(formData);

    fetch(`/gestion/api/asistentes/${tipo}/${asistenteId}/rechazar/`, {
      method: 'POST',
      body: formData
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          mAlert(data.message, 'success');
          if (typeof window.cargarVisitas === 'function') window.cargarVisitas();
          if (window.detalleVisitaActual && typeof window.verDetalleVisita === 'function') {
            window.verDetalleVisita(window.detalleVisitaActual.tipo, window.detalleVisitaActual.id);
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
  const modalDoc = document.getElementById('modalVisualizarDoc');
  if (modalDoc) {
    modalDoc.addEventListener('click', function (e) {
      if (e.target === this) cerrarModalVisualizarDoc();
    });
  }
});

window.__docsVisitasFns = {
  mostrarDocumentosPorEstado,
  volverAVisitas,
  aprobarDocDesdeListado,
  rechazarDocDesdeListado,
  visualizarDocumento,
  revisarDocumentoIndividual,
  mostrarErrorDoc,
  cerrarModalVisualizarDoc,
  revisarDocumento,
  abrirModalRechazoDoc,
  aprobarDocRevision,
  rechazarDocRevision,
};
