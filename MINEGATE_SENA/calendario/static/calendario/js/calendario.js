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
          const page = main.querySelector('.calendar-page');
          const newContainer = main.querySelector('.calendar-card');
          // cargar el script si es necesario
          if(window.initCalendar && newContainer){ window.initCalendar(newContainer); }
          if(window.initAvailabilityControls && page){ window.initAvailabilityControls(page); }
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

  // Inicializador para los controles de disponibilidad (formulario)
  function initAvailabilityControls(container){
    var root = container || document;
    var form = root.querySelector('#availabilityForm');
    if(!form) return;
    var timesText = root.querySelector('#timesText');
    var startDate = root.querySelector('#startDate');
    var endDate = root.querySelector('#endDate');
    var saveBtn = root.querySelector('#saveAvailBtn');
    if(!startDate || !endDate || !timesText || !saveBtn){ return; }

    function canEnable(){ return startDate.value && endDate.value && timesText.value.trim(); }
    function refresh(){ if(canEnable()) saveBtn.disabled = false; else saveBtn.disabled = true; }
    if(timesText) timesText.addEventListener('input', refresh);
    if(startDate) startDate.addEventListener('change', refresh);
    if(endDate) endDate.addEventListener('change', refresh);

    form.addEventListener('submit', function(e){
      e.preventDefault();
      var val = timesText.value.trim();
      if(!val){ alert('Ingrese al menos un horario en formato HH:MM separado por comas.'); return false; }
      var parts = val.split(',').map(function(s){return s.trim();}).filter(Boolean);
      var data = new FormData(); data.append('start_date', startDate.value); data.append('end_date', endDate.value);
      parts.forEach(function(p){ data.append('times', p); });
      function getCookie(name){ var v = document.cookie.match('(^|;)\\s*'+name+'\\s*=\\s*([^;]+)'); return v ? v.pop() : ''; }
      fetch(form.action, { method:'POST', headers:{ 'X-Requested-With':'XMLHttpRequest', 'X-CSRFToken':getCookie('csrftoken'), 'Accept':'application/json' }, body:data })
      .then(function(res){ return res.json(); })
      .then(function(json){
        if(json.available_dates){
          var avail = new Set(json.available_dates || []);
          // Para cada celda visible del calendario: marcar disponible o deshabilitar
          document.querySelectorAll('table.calendar-table td[data-date]').forEach(function(td){
            if(td.classList.contains('other-month') || td.classList.contains('disabled')) return;
            var d = td.getAttribute('data-date');
            if(avail.has(d)){
              td.classList.remove('no-available');
              td.classList.add('available');
              td.style.pointerEvents = 'auto';
            } else {
              td.classList.remove('available');
              td.classList.add('no-available');
              td.style.pointerEvents = 'none';
            }
          });
          saveBtn.textContent = 'Guardado';
          setTimeout(function(){ saveBtn.textContent = 'Guardar Disponibilidades'; }, 1600);
        } else {
          alert('Disponibilidades guardadas.');
        }
      })
      .catch(function(err){ console.error(err); alert('Error al guardar disponibilidades.'); });
    });

    // initial state
    refresh();
  }

  window.initAvailabilityControls = initAvailabilityControls;

  // Auto-init en carga normal de página
  document.addEventListener('DOMContentLoaded', function(){
    const container = document.querySelector('.calendar-card');
    if(container) initCalendar(container);
    // Inicializar controles de disponibilidad en carga normal
    if(container && window.initAvailabilityControls){ window.initAvailabilityControls(container); }
  });
})();
