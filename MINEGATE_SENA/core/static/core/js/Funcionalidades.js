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