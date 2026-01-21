(function(){
  // Inicializador reutilizable para la UI del calendario
  function initCalendar(container){
    if(!container) return;
    const prev = container.querySelector('#prev');
    const next = container.querySelector('#next');
    const year = parseInt(container.getAttribute('data-year'));
    const month = parseInt(container.getAttribute('data-month'));

    function fetchMonth(y,m){
      // construir URL absoluta relativa a /calendario/
      const url = new URL(window.location.origin + '/calendario/' + y + '/' + m + '/');
      return fetch(url, {headers: {'X-Requested-With':'XMLHttpRequest'}})
        .then(r => r.text());
    }

    function goTo(y,m){
      // Si estamos dentro del panel principal (injected), usa AJAX
      const main = document.getElementById('mainContent');
      if(main){
        fetchMonth(y,m).then(html => {
          main.innerHTML = '<div class="calendar-page">' + html + '</div>';
          // re-inicializar calendar en el nuevo contenido
          const newContainer = main.querySelector('.calendar-card');
          // cargar el script si es necesario
          if(window.initCalendar){
            window.initCalendar(newContainer);
          }
        }).catch(err => console.error(err));
      } else {
        // caso normal: navegar a la URL completa
        window.location.href = '/calendario/' + y + '/' + m + '/';
      }
    }

    if(prev) prev.addEventListener('click', ()=>{
      let y = year;
      let m = month - 1;
      if(m < 1){ m = 12; y -= 1; }
      goTo(y,m);
    });
    if(next) next.addEventListener('click', ()=>{
      let y = year;
      let m = month + 1;
      if(m > 12){ m = 1; y += 1; }
      goTo(y,m);
    });
  }

  // Exponer para que el panel pueda re-inicializar después de inyección
  window.initCalendar = initCalendar;

  // Auto-init en carga normal de página
  document.addEventListener('DOMContentLoaded', function(){
    const container = document.querySelector('.calendar-card');
    if(container) initCalendar(container);
  });
})();
