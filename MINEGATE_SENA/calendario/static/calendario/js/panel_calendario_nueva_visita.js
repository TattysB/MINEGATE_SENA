(function () {
  let selectedDate = null;
  let selectedSchedule = null;

  function ensureCss(src) {
    if (!src || document.querySelector("link[href='" + src + "']")) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = src;
    document.head.appendChild(link);
  }

  function initCalendarioSeleccionEvents(container) {
    if (!container) return;

    const prev = container.querySelector('#prevSel');
    const next = container.querySelector('#nextSel');
    const cardEl = container.querySelector('.calendar-card');
    const horarioTitle = container.querySelector('#horarioTitle');
    const horarioHint = container.querySelector('#horarioHint');
    const horariosList = container.querySelector('#horariosList');
    const btnContinuar = container.querySelector('#btnContinuarVisita');

    if (!cardEl) return;

    const year = parseInt(cardEl.getAttribute('data-year'), 10);
    const month = parseInt(cardEl.getAttribute('data-month'), 10);

    selectedDate = null;
    selectedSchedule = null;

    function fetchMonth(y, m) {
      return fetch('/calendario/seleccion/' + y + '/' + m + '/', {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      }).then((response) => response.text());
    }

    function goTo(y, m) {
      const contenedor = document.getElementById('calendarioNuevaVisitaContent');
      if (!contenedor) return;

      const config = window.calendarioPanelConfig || {};
      ensureCss(config.seleccionCssUrl || '/static/calendario/css/calendario_seleccion.css');

      fetchMonth(y, m).then((html) => {
        contenedor.innerHTML = html;
        const newContainer = contenedor.querySelector('#calendarioSeleccionPage');
        if (newContainer) initCalendarioSeleccionEvents(newContainer);
      });
    }

    if (prev) {
      prev.onclick = function () {
        let newYear = year;
        let newMonth = month - 1;
        if (newMonth < 1) {
          newMonth = 12;
          newYear -= 1;
        }
        goTo(newYear, newMonth);
      };
    }

    if (next) {
      next.onclick = function () {
        let newYear = year;
        let newMonth = month + 1;
        if (newMonth > 12) {
          newMonth = 1;
          newYear += 1;
        }
        goTo(newYear, newMonth);
      };
    }

    const table = container.querySelector('.calendar-table');
    if (table) {
      table.onclick = function (event) {
        const td = event.target.closest('td');
        if (!td || !td.classList.contains('available')) return;

        container.querySelectorAll('td.selected-day').forEach((el) => el.classList.remove('selected-day'));
        td.classList.add('selected-day');

        selectedDate = td.getAttribute('data-date');
        selectedSchedule = null;

        if (btnContinuar) btnContinuar.style.display = 'none';

        loadHorarios(selectedDate);
      };
    }

    function loadHorarios(dateStr) {
      if (horarioHint) horarioHint.textContent = 'Cargando horarios...';
      if (horariosList) {
        horariosList.innerHTML = '';
        horariosList.style.display = 'none';
      }

      fetch('/calendario/horarios/' + dateStr + '/', {
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' }
      })
        .then((response) => response.json())
        .then((data) => {
          if (!data.ok) {
            if (horarioHint) horarioHint.textContent = 'Error: ' + (data.error || 'No se pudieron cargar');
            return;
          }

          if (!data.ranges || !data.ranges.length) {
            if (horarioHint) horarioHint.textContent = 'No hay horarios configurados para este día.';
            return;
          }

          if (horarioTitle) horarioTitle.textContent = 'Horarios disponibles para ' + dateStr;
          if (horarioHint) horarioHint.textContent = 'Selecciona el horario que prefieras:';

          if (!horariosList) return;

          horariosList.innerHTML = data.ranges
            .map((range) => '<span class="horario-chip" data-start="' + range.start + '" data-end="' + range.end + '">' + range.label + '</span>')
            .join('');

          horariosList.style.display = 'block';

          horariosList.querySelectorAll('.horario-chip').forEach((chip) => {
            chip.onclick = function () {
              horariosList.querySelectorAll('.horario-chip').forEach((c) => c.classList.remove('selected'));
              this.classList.add('selected');
              selectedSchedule = {
                start: this.getAttribute('data-start'),
                end: this.getAttribute('data-end'),
                label: this.textContent
              };
              if (btnContinuar) btnContinuar.style.display = 'inline-block';
            };
          });
        })
        .catch(() => {
          if (horarioHint) horarioHint.textContent = 'Error al cargar horarios.';
        });
    }

    if (btnContinuar) {
      btnContinuar.onclick = function () {
        if (!selectedDate || !selectedSchedule) {
          alert('Por favor selecciona una fecha y un horario.');
          return;
        }

        sessionStorage.setItem('visita_fecha', selectedDate);
        sessionStorage.setItem('visita_horario_inicio', selectedSchedule.start);
        sessionStorage.setItem('visita_horario_fin', selectedSchedule.end);
        sessionStorage.setItem('visita_horario_label', selectedSchedule.label);

        alert('Fecha: ' + selectedDate + '\nHorario: ' + selectedSchedule.label + '\n\nDatos guardados.');
      };
    }
  }

  function mostrarCalendarioNuevaVisita() {
    const contenedor = document.getElementById('contenedorCalendarioNuevaVisita');
    const contenido = document.getElementById('calendarioNuevaVisitaContent');
    const config = window.calendarioPanelConfig || {};

    if (!contenedor || !contenido) return;

    ensureCss(config.seleccionCssUrl || '/static/calendario/css/calendario_seleccion.css');

    contenedor.style.display = 'block';
    contenido.innerHTML =
      '<div style="text-align: center; padding: 30px;">' +
      '<i class="ri-loader-4-line" style="font-size: 40px; color: #10b981; animation: spin 1s linear infinite;"></i>' +
      '<p style="color: #6b7280; margin-top: 10px;">Cargando calendario...</p>' +
      '</div>';

    fetch('/calendario/seleccion/', {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
      .then((response) => response.text())
      .then((html) => {
        contenido.innerHTML = html;
        const calendarioContainer = contenido.querySelector('#calendarioSeleccionPage');
        if (calendarioContainer) initCalendarioSeleccionEvents(calendarioContainer);
      })
      .catch(() => {
        contenido.innerHTML =
          '<div style="text-align: center; padding: 30px;">' +
          '<i class="ri-error-warning-line" style="font-size: 40px; color: #ef4444;"></i>' +
          '<p style="color: #6b7280; margin-top: 10px;">Error al cargar el calendario.</p>' +
          '<button onclick="mostrarCalendarioNuevaVisita()" style="margin-top: 10px; padding: 8px 16px; background: #10b981; color: white; border: none; border-radius: 6px; cursor: pointer;">Reintentar</button>' +
          '</div>';
      });

    setTimeout(() => {
      contenedor.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
  }

  function ocultarCalendarioNuevaVisita() {
    const contenedor = document.getElementById('contenedorCalendarioNuevaVisita');
    if (contenedor) contenedor.style.display = 'none';
  }

  window.initCalendarioSeleccionEvents = initCalendarioSeleccionEvents;
  window.mostrarCalendarioNuevaVisita = mostrarCalendarioNuevaVisita;
  window.ocultarCalendarioNuevaVisita = ocultarCalendarioNuevaVisita;
})();
