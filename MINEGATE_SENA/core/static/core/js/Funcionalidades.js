// ==============================
// Funcionalidad de la barra lateral
// ==============================

const sidebarItems = document.querySelectorAll('.sidebar li');

// Activar item de barra lateral
sidebarItems.forEach(item => {
  item.addEventListener('click', () => {
    sidebarItems.forEach(i => i.classList.remove('active'));
    item.classList.add('active');

    const section = item.getAttribute('data-content');
    cargarContenido(section);
  });
});

// Función para cargar el contenido dinámicamente
function cargarContenido(section) {
  const mainContent = document.getElementById('mainContent');

  // Ocultar todas las secciones
  const todasLasSecciones = mainContent.querySelectorAll('.contenido-seccion');
  todasLasSecciones.forEach(sec => sec.style.display = 'none');

  // Remover contenido temporal si existe
  const contenidoTemporal = mainContent.querySelector('.contenido-temporal');
  if (contenidoTemporal) {
    contenidoTemporal.remove();
  }

  // Si es la sección de Gestión de Permisos, mostrarla
  if (section === 'GestionPermisos') {
    const seccionPermisos = document.getElementById('seccion-gestion-permisos');
    if (seccionPermisos) {
      seccionPermisos.style.display = 'block';
    } else {
      console.warn('Sección de permisos no encontrada');
    }
  }
  // Si es la sección de Gestión de Visitas
  else if (section === 'gestionvisitas') {
    const seccionVisitas = document.getElementById('seccion-gestion-visitas');
    if (seccionVisitas) {
      seccionVisitas.style.display = 'block';
      // Cargar visitas al mostrar la sección
      if (typeof cargarVisitas === 'function') {
        cargarVisitas();
      }
    } else {
      console.warn('Sección de gestión de visitas no encontrada');
    }
  }
  
  // Si es la sección de Documentos
  else if (section === 'documentos') {
    console.log(">>> Sección DOCUMENTOS activada");
    const seccionDocs = document.getElementById('seccion-documentos');
    if (seccionDocs) {
      seccionDocs.style.display = 'block';
      console.log(">>> seccion-documentos visible, llamando cargarDocumentos()");
      if (typeof cargarDocumentos === 'function') {
        console.log(">>> cargarDocumentos es una función, ejecutando...");
        cargarDocumentos();
      } else {
        console.error("❌ cargarDocumentos NO es una función");
      }
    } else {
      console.warn('Sección de documentos no encontrada');
    }
  }
  else {
    // Aquí puedes agregar la lógica para cargar otras secciones
    // Por ahora solo muestra un mensaje temporal
    const divTemporal = document.createElement('div');
    divTemporal.className = 'contenido-temporal';
    divTemporal.innerHTML = `<div class="seccion-${section}">
      <h2>Sección: ${section}</h2>
      <p>Contenido de ${section} en desarrollo...</p>
    </div>`;
    mainContent.appendChild(divTemporal);
  }
}