let archivosPendientesLista = [];

console.log("✓ gestion_documentos.js CARGADO CORRECTAMENTE");

// ==============================
// Modal personalizado (reemplaza alert/confirm)
// ==============================
function _crearModalBase() {
    // Si ya existe, reutilizar
    var existente = document.getElementById('modalDocsCustom');
    if (existente) existente.remove();

    var overlay = document.createElement('div');
    overlay.id = 'modalDocsCustom';
    overlay.className = 'docs-modal-overlay';

    var card = document.createElement('div');
    card.className = 'docs-modal-card';
    card.id = 'modalDocsCard';

    overlay.appendChild(card);
    document.body.appendChild(overlay);

    // Animación de entrada
    requestAnimationFrame(function () {
        overlay.classList.add('visible');
        card.classList.add('visible');
    });

    return { overlay: overlay, card: card };
}

function _cerrarModal(overlay) {
    var card = document.getElementById('modalDocsCard');
    if (card) {
        card.classList.remove('visible');
    }
    overlay.classList.remove('visible');
    setTimeout(function () {
        if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
    }, 250);
}

/**
 * Modal de alerta personalizado (reemplaza alert)
 * @param {string} mensaje - Texto a mostrar
 * @param {string} tipo - 'success' | 'error' | 'warning' | 'info'
 */
function mostrarAlerta(mensaje, tipo) {
    tipo = tipo || 'info';
    var modal = _crearModalBase();

    var iconos = {
        success: { icon: 'fa-check-circle', color: '#10b981', bg: '#d1fae5' },
        error: { icon: 'fa-times-circle', color: '#ef4444', bg: '#fee2e2' },
        warning: { icon: 'fa-exclamation-triangle', color: '#f59e0b', bg: '#fef3c7' },
        info: { icon: 'fa-info-circle', color: '#3b82f6', bg: '#dbeafe' }
    };
    var cfg = iconos[tipo] || iconos.info;

    modal.card.innerHTML =
        '<div style="text-align:center;">' +
        '<div class="docs-modal-icono docs-modal-' + tipo + '">' +
        '<i class="fas ' + cfg.icon + '"></i>' +
        '</div>' +
        '<div class="docs-modal-mensaje">' + mensaje.replace(/\n/g, '<br>') + '</div>' +
        '<button id="btnModalAceptar" class="docs-modal-btn docs-modal-btn-confirm docs-modal-btn-' + tipo + '">' +
        'Aceptar' +
        '</button>' +
        '</div>';

    var btn = document.getElementById('btnModalAceptar');
    btn.onclick = function () { _cerrarModal(modal.overlay); };
    modal.overlay.onclick = function (e) { if (e.target === modal.overlay) _cerrarModal(modal.overlay); };
}

/**
 * Modal de confirmación personalizado (reemplaza confirm)
 * @param {string} titulo - Título del modal
 * @param {string} mensaje - Texto descriptivo
 * @param {function} onConfirmar - Callback si confirma
 * @param {string} tipo - 'danger' | 'warning' | 'info'
 */
function mostrarConfirmacion(titulo, mensaje, onConfirmar, tipo) {
    tipo = tipo || 'danger';
    var modal = _crearModalBase();

    var estilos = {
        danger: { icon: 'fa-trash-alt', color: '#ef4444', bg: '#fee2e2', grad: '#dc2626' },
        warning: { icon: 'fa-exclamation-triangle', color: '#f59e0b', bg: '#fef3c7', grad: '#d97706' },
        info: { icon: 'fa-question-circle', color: '#3b82f6', bg: '#dbeafe', grad: '#2563eb' }
    };
    var cfg = estilos[tipo] || estilos.danger;

    modal.card.innerHTML =
        '<div style="text-align:center;">' +
        '<div class="docs-modal-icono docs-modal-' + (tipo === 'danger' ? 'error' : tipo) + '">' +
        '<i class="fas ' + cfg.icon + '"></i>' +
        '</div>' +
        '<h3 class="docs-modal-titulo">' + titulo + '</h3>' +
        '<p class="docs-modal-desc">' + mensaje + '</p>' +
        '<div class="docs-modal-botones">' +
        '<button id="btnModalCancelar" class="docs-modal-btn docs-modal-btn-cancel">' +
        'Cancelar' +
        '</button>' +
        '<button id="btnModalConfirmar" class="docs-modal-btn docs-modal-btn-confirm docs-modal-btn-' + tipo + '">' +
        (tipo === 'danger' ? '<i class="fas fa-trash me-1"></i> Eliminar' : 'Confirmar') +
        '</button>' +
        '</div>' +
        '</div>';

    var btnCancelar = document.getElementById('btnModalCancelar');
    var btnConfirmar = document.getElementById('btnModalConfirmar');

    btnCancelar.onclick = function () { _cerrarModal(modal.overlay); };

    btnConfirmar.onclick = function () {
        _cerrarModal(modal.overlay);
        if (typeof onConfirmar === 'function') onConfirmar();
    };

    modal.overlay.onclick = function (e) { if (e.target === modal.overlay) _cerrarModal(modal.overlay); };
}

// Obtener CSRF token desde la cookie
function getCsrfToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let c of cookies) {
        c = c.trim();
        if (c.startsWith(name + '=')) {
            return c.substring(name.length + 1);
        }
    }
    // Fallback: buscar en el meta tag o input hidden
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (input) return input.value;
    return '';
}

// Iconos según extensión
function getIconoDocumento(ext) {
    const iconos = {
        '.pdf': '<i class="fas fa-file-pdf docs-icono-pdf"></i>',
        '.doc': '<i class="fas fa-file-word docs-icono-word"></i>',
        '.docx': '<i class="fas fa-file-word docs-icono-word"></i>',
        '.xls': '<i class="fas fa-file-excel docs-icono-excel"></i>',
        '.xlsx': '<i class="fas fa-file-excel docs-icono-excel"></i>',
        '.ppt': '<i class="fas fa-file-powerpoint docs-icono-ppt"></i>',
        '.pptx': '<i class="fas fa-file-powerpoint docs-icono-ppt"></i>',
        '.jpg': '<i class="fas fa-file-image docs-icono-img"></i>',
        '.jpeg': '<i class="fas fa-file-image docs-icono-img"></i>',
        '.png': '<i class="fas fa-file-image docs-icono-img"></i>',
        '.txt': '<i class="fas fa-file-alt docs-icono-txt"></i>',
    };
    return iconos[ext] || '<i class="fas fa-file docs-icono-default"></i>';
}

function getCategoriaBadge(categoria, display) {
    const config = {
        'EPP Necesarios': { clase: 'docs-badge-epp', icono: 'fas fa-hard-hat' },
        'Formato Inducción y Reinducción': { clase: 'docs-badge-induccion', icono: 'fas fa-file-signature' },
        'ATS': { clase: 'docs-badge-ats', icono: 'fas fa-clipboard-check' },
        'Formato Auto Reporte Condiciones de Salud': { clase: 'docs-badge-salud', icono: 'fas fa-heartbeat' },
        'Charla de Seguridad y Calestenia': { clase: 'docs-badge-charla', icono: 'fas fa-shield-alt' },
        'Formato Autorización Padres de Familia': { clase: 'docs-badge-padres', icono: 'fas fa-users' },
    };
    const c = config[categoria] || { clase: 'docs-badge-otro', icono: 'fas fa-tag' };
    var texto = display || categoria;
    return '<span class="docs-badge ' + c.clase + '" title="' + texto + '"><i class="' + c.icono + '"></i> ' + texto + '</span>';
}

function formatearTamaño(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// Filtrar por categoría (chips)
function filtrarCategoria(btn) {
    // Quitar active de todos los chips
    document.querySelectorAll('.docs-cat-chip').forEach(function (c) { c.classList.remove('active'); });
    // Activar el seleccionado
    btn.classList.add('active');
    // Guardar valor en el hidden input
    document.getElementById('filtroCategoria').value = btn.getAttribute('data-cat');
    cargarDocumentos();
}

// Cargar documentos desde la API
function cargarDocumentos() {
    console.log(">>> cargarDocumentos() INICIADO");
    var filtroElem = document.getElementById('filtroCategoria');
    var buscarElem = document.getElementById('buscarDocumento');
    var tbody = document.getElementById('cuerpoTablaDocumentos');
    var tablaContenedor = document.querySelector('.docs-tabla-contenedor');

    if (!filtroElem || !buscarElem || !tbody) {
        console.error("❌ Elementos no encontrados:", { filtroElem, buscarElem, tbody });
        return;
    }

    var categoria = filtroElem.value || '';
    var buscar = buscarElem.value || '';

    console.log("Filtros aplicados:", { categoria, buscar });

    // Saltico visual al recargar
    if (tablaContenedor) {
        tablaContenedor.classList.remove('docs-tabla-refresh');
        void tablaContenedor.offsetWidth;
        tablaContenedor.classList.add('docs-tabla-refresh');
    }

    var url = '/documentos/api/listar/?';
    if (categoria) url += 'categoria=' + encodeURIComponent(categoria) + '&';
    if (buscar) url += 'buscar=' + encodeURIComponent(buscar) + '&';

    console.log("Llamando API:", url);

    fetch(url)
        .then(function (r) {
            console.log("API Response status:", r.status);
            if (!r.ok) throw new Error('Error ' + r.status);
            return r.json();
        })
        .then(function (data) {
            console.log("✓ Datos recibidos del API:", data);
            var contadorElem = document.getElementById('contadorDocs');
            if (contadorElem) {
                contadorElem.textContent = data.total + ' documento(s)';
            }

            if (data.documentos.length === 0) {
                console.log("Sin documentos para mostrar");
                tbody.innerHTML =
                    '<tr>' +
                    '<td colspan="6" class="docs-vacio">' +
                    '<i class="fas fa-folder-open"></i>' +
                    '<p>No hay documentos' + (categoria ? ' en esta categoría' : '') + '.</p>' +
                    '<p class="docs-vacio-sub">Sube archivos usando la zona de carga de arriba.</p>' +
                    '</td></tr>';
            } else {
                console.log("Renderizando " + data.documentos.length + " documentos");
                tbody.innerHTML = data.documentos.map(function (doc) {
                    console.log("Documento:", { id: doc.id, titulo: doc.titulo, archivo_url: doc.archivo_url });
                    return '<tr class="docs-fila">' +
                        '<td class="docs-tabla td">' +
                        '<div class="docs-celda-archivo">' +
                        getIconoDocumento(doc.extension) +
                        '<div>' +
                        '<div class="docs-archivo-titulo">' + doc.titulo + '</div>' +
                        '<div class="docs-archivo-subtitulo">' + doc.nombre_archivo + '</div>' +
                        '</div></div></td>' +
                        '<td class="docs-tabla td">' + getCategoriaBadge(doc.categoria, doc.categoria_display) + '</td>' +
                        '<td class="docs-tabla td docs-celda-texto">' + doc.subido_por + '</td>' +
                        '<td class="docs-tabla td docs-celda-texto">' + doc.fecha_subida + '</td>' +
                        '<td class="docs-tabla td docs-celda-texto">' + doc.tamaño + '</td>' +
                        '<td class="docs-tabla td docs-celda-acciones">' +
                        '<div class="docs-acciones">' +
                        '<button class="docs-btn-accion docs-btn-ver" data-url="' + doc.archivo_url + '" data-nombre="' + doc.nombre_archivo + '" onclick="verDocumentoSafe(this)" title="Ver">' +
                        '<i class="fas fa-eye"></i> Ver</button>' +
                        '<a href="' + doc.archivo_url + '" download class="docs-btn-accion docs-btn-descargar" title="Descargar">' +
                        '<i class="fas fa-download"></i> Bajar</a>' +
                        '<button class="docs-btn-accion docs-btn-eliminar" data-id="' + doc.id + '" data-titulo="' + doc.titulo + '" onclick="eliminarDocumentoSafe(this)" title="Eliminar">' +
                        '<i class="fas fa-trash"></i> Eliminar</button>' +
                        '</div></td></tr>';
                }).join('');
                console.log(">>> Tabla renderizada con éxito");
            }
        })
        .catch(function (err) {
            console.error("❌ Error en cargarDocumentos:", err);
            tbody.innerHTML = '<tr><td colspan="6" class="docs-error">Error al cargar documentos: ' + err.message + '</td></tr>';
        });
}

// Drag & Drop
function handleDropDocumentos(e) {
    e.preventDefault();
    var zona = document.getElementById('zonaSubida');
    zona.style.borderColor = '#3b82f6';
    zona.classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) {
        prepararArchivosDocumentos(e.dataTransfer.files);
    }
}

// Categorías disponibles
var CATEGORIAS_DOCUMENTO = [
    { value: 'EPP Necesarios', label: '\ud83d\udc77\ud83c\udffb\u200d\u2642\ufe0f EPP Necesarios', keywords: ['epp', 'casco', 'guante', 'botas', 'gafa', 'chaleco', 'proteccion'] },
    { value: 'Formato Inducción y Reinducción', label: '📜 Formato Inducción y Reinducción', keywords: ['inducci', 'reinducci', 'induccion', 'reinduccion'] },
    { value: 'ATS', label: '\ud83d\udcdd ATS', keywords: ['ats', 'analisis de trabajo', 'analisis trabajo'] },
    { value: 'Formato Auto Reporte Condiciones de Salud', label: '\ud83d\udc69\ud83c\udffb\u200d\u2695\ufe0f Formato Auto Reporte', keywords: ['auto reporte', 'autoreporte', 'condiciones de salud', 'salud'] },
    { value: 'Charla de Seguridad y Calestenia', label: '\ud83e\udd38\ud83c\udffb\u200d\u2642\ufe0f Charla de Seguridad', keywords: ['charla', 'calestenia', 'calistenia'] },
    { value: 'Formato Autorización Padres de Familia', label: '\ud83d\udccb Autorización Padres', keywords: ['autorizaci', 'padres', 'familia', 'menor'] }
];

// Auto-detectar categoría según el nombre del archivo
function detectarCategoria(nombreArchivo) {
    var nombre = nombreArchivo.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    for (var c = 0; c < CATEGORIAS_DOCUMENTO.length; c++) {
        var cat = CATEGORIAS_DOCUMENTO[c];
        for (var k = 0; k < cat.keywords.length; k++) {
            var kw = cat.keywords[k].normalize('NFD').replace(/[\u0300-\u036f]/g, '');
            if (nombre.indexOf(kw) !== -1) return cat.value;
        }
    }
    return CATEGORIAS_DOCUMENTO[0].value; // Default: EPP Necesarios
}

// Generar HTML de <select> de categorías con una seleccionada
function generarSelectCategoria(index, seleccionada) {
    var html = '<select id="catArchivo_' + index + '" class="docs-archivo-cat select">';
    for (var c = 0; c < CATEGORIAS_DOCUMENTO.length; c++) {
        var cat = CATEGORIAS_DOCUMENTO[c];
        html += '<option value="' + cat.value + '"' + (cat.value === seleccionada ? ' selected' : '') + '>' + cat.label + '</option>';
    }
    html += '</select>';
    return html;
}

// Preparar archivos para subir
function prepararArchivosDocumentos(files) {
    archivosPendientesLista = Array.from(files);
    var contenedor = document.getElementById('archivosPendientes');
    var lista = document.getElementById('listaArchivosPendientes');

    if (!contenedor || !lista) {
        console.error("Elementos de archivos pendientes no encontrados");
        mostrarAlerta("Error: No se encontraron elementos de la interfaz", "error");
        return;
    }

    if (archivosPendientesLista.length === 0) {
        contenedor.style.display = 'none';
        return;
    }

    contenedor.style.display = 'block';
    var html = '';
    for (var i = 0; i < archivosPendientesLista.length; i++) {
        var f = archivosPendientesLista[i];
        var ext = '.' + f.name.split('.').pop().toLowerCase();
        var catDetectada = detectarCategoria(f.name);
        html += '<div class="docs-archivo-item">' +
            getIconoDocumento(ext) +
            '<div class="docs-archivo-info">' +
            '<div class="docs-archivo-nombre">' + f.name + '</div>' +
            '<div class="docs-archivo-size">' + formatearTamaño(f.size) + '</div>' +
            '</div>' +
            '<div class="docs-archivo-cat">' +
            '<span><i class="fas fa-tag"></i></span>' +
            generarSelectCategoria(i, catDetectada) +
            '</div>' +
            '<button onclick="quitarArchivoPendiente(' + i + ')" class="docs-btn-quitar" title="Quitar">' +
            '<i class="fas fa-times-circle"></i></button></div>';
    }
    lista.innerHTML = html;
    console.log("Archivos preparados:", archivosPendientesLista.length);
}

function quitarArchivoPendiente(index) {
    archivosPendientesLista.splice(index, 1);
    prepararArchivosDocumentos(archivosPendientesLista);
    document.getElementById('inputArchivosDocumentos').value = '';
}

function cancelarSubida() {
    archivosPendientesLista = [];
    document.getElementById('archivosPendientes').style.display = 'none';
    document.getElementById('inputArchivosDocumentos').value = '';
}

// Subir archivos
function subirArchivosDocumentos() {
    if (archivosPendientesLista.length === 0) {
        mostrarAlerta('Selecciona archivos para subir', 'warning');
        return;
    }

    var formData = new FormData();
    for (var i = 0; i < archivosPendientesLista.length; i++) {
        formData.append('archivos', archivosPendientesLista[i]);
        var selectCat = document.getElementById('catArchivo_' + i);
        var cat = selectCat ? selectCat.value : CATEGORIAS_DOCUMENTO[0].value;
        formData.append('categorias', cat);
    }
    formData.append('csrfmiddlewaretoken', getCsrfToken());

    var btnSubir = document.getElementById('btnSubirDocs');
    var progreso = document.getElementById('progresoSubida');

    if (!btnSubir || !progreso) {
        mostrarAlerta('Error: Interfaz incompleta', 'error');
        return;
    }

    btnSubir.disabled = true;
    btnSubir.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Subiendo...';
    progreso.style.display = 'block';

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/documentos/api/subir/');

    xhr.upload.addEventListener('progress', function (e) {
        if (e.lengthComputable) {
            var pct = Math.round((e.loaded / e.total) * 100);
            var barra = document.getElementById('barraProgreso');
            var texto = document.getElementById('textoProgreso');
            if (barra) barra.style.width = pct + '%';
            if (texto) texto.textContent = 'Subiendo... ' + pct + '%';
        }
    });

    xhr.onload = function () {
        btnSubir.disabled = false;
        btnSubir.innerHTML = '<i class="fas fa-upload"></i> Subir archivos';
        progreso.style.display = 'none';
        var barra = document.getElementById('barraProgreso');
        if (barra) barra.style.width = '0%';

        if (xhr.status === 200) {
            try {
                var data = JSON.parse(xhr.responseText);
                if (data.success) {
                    var msg = '✓ ' + data.creados + ' archivo(s) subido(s) correctamente.';
                    if (data.errores && data.errores.length > 0) {
                        msg += '\n\nErrores:\n' + data.errores.join('\n');
                        mostrarAlerta(msg, 'warning');
                    } else {
                        mostrarAlerta(msg, 'success');
                    }
                    cancelarSubida();
                    cargarDocumentos();
                } else {
                    mostrarAlerta(data.error || 'Error desconocido', 'error');
                }
            } catch (e) {
                mostrarAlerta('Error al procesar respuesta: ' + e.message, 'error');
            }
        } else {
            mostrarAlerta('Error al subir: ' + xhr.status, 'error');
        }
    };

    xhr.onerror = function () {
        btnSubir.disabled = false;
        btnSubir.innerHTML = '<i class="fas fa-upload"></i> Subir archivos';
        progreso.style.display = 'none';
        mostrarAlerta('Error de conexión con el servidor', 'error');
    };

    xhr.send(formData);
}

// Ver documento en modal (versión segura con data attributes)
function verDocumentoSafe(button) {
    var archivoUrl = button.getAttribute('data-url');
    var nombreArchivo = button.getAttribute('data-nombre');

    console.log("verDocumentoSafe - data-url:", archivoUrl);
    console.log("verDocumentoSafe - data-nombre:", nombreArchivo);

    if (!archivoUrl || !nombreArchivo) {
        mostrarAlerta('Error: No se pudo obtener la información del archivo', 'error');
        return;
    }

    verDocumento(archivoUrl, nombreArchivo);
}

// Función original verDocumento
function verDocumento(archivoUrl, nombreArchivo) {
    console.log("=== verDocumento INICIANDO ===");
    console.log("URL recibida:", archivoUrl);
    console.log("Nombre archivo:", nombreArchivo);
    console.log("URL completa a cargar:", window.location.origin + archivoUrl);
    console.log("=== FIN DEBUG INICIAL ===");

    var modal = _crearModalBase();
    var extension = nombreArchivo.split('.').pop().toLowerCase();

    // Ampliar el modal para que sea más grande
    var card = document.getElementById('modalDocsCard');
    if (!card) {
        mostrarAlerta('Error: No se pudo crear el modal', 'error');
        return;
    }

    card.style.width = '90vw';
    card.style.maxWidth = '1200px';
    card.style.height = '85vh';
    card.style.padding = '20px';

    // Detectar el tipo de archivo
    var isPDF = extension === 'pdf';
    var isImagen = ['jpg', 'jpeg', 'png', 'gif', 'webp'].indexOf(extension) !== -1;

    console.log("Tipo de archivo detectado:", { isPDF, isImagen, extension });

    if (isPDF) {
        var headerHtml = '<div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #e5e7eb; background: #f9fafb;">' +
            '<h3 style="margin: 0; color: #1f2937; font-size: 16px;"><i class="fas fa-file-pdf" style="margin-right: 8px; color: #ef4444;"></i>' + nombreArchivo + '</h3>' +
            '<div style="display:flex;gap:8px;align-items:center;">' +
            '<a href="' + archivoUrl + '" target="_blank" style="background:#6b7280;color:white;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:500;"><i class="fas fa-external-link-alt"></i> Nueva pestaña</a>' +
            '<button onclick="_cerrarModalButton()" style="background:#ef4444;color:white;border:none;font-size:20px;cursor:pointer;width:34px;height:34px;border-radius:6px;line-height:1;">&times;</button>' +
            '</div></div>';

        var contentHtml = '<div style="flex: 1; overflow: hidden;">' +
            '<iframe src="' + archivoUrl + '" style="width:100%;height:100%;border:none;" allowfullscreen>' +
            '</iframe>' +
            '</div>';

        var fullHtml = '<div style="display: flex; flex-direction: column; height: 100%; background: white; border-radius: 8px; overflow: hidden;">' +
            headerHtml + contentHtml + '</div>';

        card.innerHTML = fullHtml;
    } else if (isImagen) {
        var headerHtml = '<div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #e5e7eb; background: #f9fafb;">' +
            '<h3 style="margin: 0; color: #1f2937; font-size: 16px;"><i class="fas fa-image" style="margin-right: 8px; color: #8b5cf6;"></i>' + nombreArchivo + '</h3>' +
            '<button onclick="_cerrarModalButton()" style="background: none; border: none; color: #9ca3af; font-size: 24px; cursor: pointer; padding: 4px 8px;">&times;</button>' +
            '</div>';

        var contentHtml = '<div style="flex: 1; overflow: auto; display: flex; justify-content: center; align-items: center; background: #f5f5f5;">' +
            '<img src="' + archivoUrl + '" style="max-width: 100%; max-height: 100%; object-fit: contain;" alt="Vista previa" onerror="this.parentElement.innerHTML = \'<p style=\\\"color: #ef4444; text-align: center; padding: 20px;\\\">Error al cargar la imagen</p>\'" />' +
            '</div>';

        var fullHtml = '<div style="display: flex; flex-direction: column; height: 100%; background: white; border-radius: 8px; overflow: hidden;">' +
            headerHtml + contentHtml + '</div>';

        card.innerHTML = fullHtml;
    } else {
        // Para otros tipos de archivo, mostrar opciones
        card.innerHTML = '<div style="text-align: center; padding: 40px;">' +
            '<i class="fas fa-file" style="font-size: 64px; color: #d1d5db; margin-bottom: 20px; display: block;"></i>' +
            '<h3 style="margin: 0 0 12px 0; color: #1f2937;">Tipo de archivo no soportado</h3>' +
            '<p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px;">Archivo: <strong>' + extension.toUpperCase() + '</strong></p>' +
            '<p style="margin: 0 0 24px 0; color: #6b7280; font-size: 13px;">Este tipo de archivo no se puede abrir en navegador.</p>' +
            '<div style="display: flex; gap: 12px; justify-content: center;">' +
            '<a href="' + archivoUrl + '" download class="docs-modal-btn docs-modal-btn-confirm" style="text-decoration: none; display: inline-block;">' +
            '<i class="fas fa-download"></i> Descargar' +
            '</a>' +
            '<button onclick="_cerrarModalButton()" class="docs-modal-btn docs-modal-btn-cancel">' +
            'Cerrar' +
            '</button>' +
            '</div></div>';
    }

    modal.overlay.onclick = function (e) {
        if (e.target === modal.overlay) _cerrarModal(modal.overlay);
    };
}

// Función auxiliar para cerrar modal desde dentro del HTML
function _cerrarModalButton() {
    var modal = document.getElementById('modalDocsCustom');
    if (modal) {
        _cerrarModal(modal);
    }
}

// Eliminar documento (versión segura con data attributes)
function eliminarDocumentoSafe(button) {
    var id = parseInt(button.getAttribute('data-id'), 10);
    var titulo = button.getAttribute('data-titulo');

    if (!id || !titulo) {
        mostrarAlerta('Error: No se pudo obtener la información del documento', 'error');
        return;
    }

    eliminarDocumento(id, titulo);
}

// Función original eliminarDocumento
function eliminarDocumento(id, titulo) {
    mostrarConfirmacion(
        'Eliminar documento',
        '¿Estás seguro de eliminar <strong>"' + titulo + '"</strong>?<br><span style="font-size:12px;color:#9ca3af;">Esta acción no se puede deshacer.</span>',
        function () {
            var formData = new FormData();
            formData.append('csrfmiddlewaretoken', getCsrfToken());

            fetch('/documentos/api/eliminar/' + id + '/', {
                method: 'POST',
                body: formData,
            })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.success) {
                        mostrarAlerta('Documento eliminado correctamente.', 'success');
                        cargarDocumentos();
                    } else {
                        mostrarAlerta(data.error || 'No se pudo eliminar el documento.', 'error');
                    }
                })
                .catch(function () { mostrarAlerta('No se pudo conectar con el servidor.', 'error'); });
        },
        'danger'
    );
}