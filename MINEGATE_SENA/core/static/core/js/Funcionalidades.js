
const sidebarItems = document.querySelectorAll('.sidebar li');

sidebarItems.forEach(item => {
  item.addEventListener('click', () => {
    const section = item.getAttribute('data-content');

    if (!section || section === 'cerrar') {
      return;
    }

    sidebarItems.forEach(i => i.classList.remove('active'));
    item.classList.add('active');
    cargarContenido(section);
  });
});

function cargarContenido(section) {
  const mainContent = document.getElementById('mainContent');

  if (!section || section === 'cerrar') {
    return;
  }

  const todasLasSecciones = mainContent.querySelectorAll('.contenido-seccion');
  todasLasSecciones.forEach(sec => sec.style.display = 'none');

  const contenidoTemporal = mainContent.querySelector('.contenido-temporal');
  if (contenidoTemporal) {
    contenidoTemporal.remove();
  }

  if (section === 'GestionPermisos') {
    const seccionPermisos = document.getElementById('seccion-gestion-permisos');
    if (seccionPermisos) {
      seccionPermisos.style.display = 'block';
    } else {
      console.warn('Sección de permisos no encontrada');
    }
  }
  else if (section === 'gestionvisitas') {
    const seccionVisitas = document.getElementById('seccion-gestion-visitas');
    if (seccionVisitas) {
      seccionVisitas.style.display = 'block';
      if (typeof cargarVisitas === 'function') {
        cargarVisitas();
      }
    } else {
      console.warn('Sección de gestión de visitas no encontrada');
    }
  }
  
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
    return;
  }
}