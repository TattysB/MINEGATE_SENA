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
  } else {
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