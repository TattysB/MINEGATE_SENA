
const sidebarItems = document.querySelectorAll('.sidebar li');

sidebarItems.forEach(item => {
  item.addEventListener('click', () => {
    sidebarItems.forEach(i => i.classList.remove('active'));
    item.classList.add('active');

    const section = item.getAttribute('data-content');
    cargarContenido(section);
  });
});

function cargarContenido(section) {
  const mainContent = document.getElementById('mainContent');
  
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
  } else {
    const divTemporal = document.createElement('div');
    divTemporal.className = 'contenido-temporal';
    divTemporal.innerHTML = `<div class="seccion-${section}">
      <h2>Sección: ${section}</h2>
      <p>Contenido de ${section} en desarrollo...</p>
    </div>`;
    mainContent.appendChild(divTemporal);
  }
}