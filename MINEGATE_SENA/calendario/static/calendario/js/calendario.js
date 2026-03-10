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
          main.innerHTML = html;
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
    var startTime = root.querySelector('#startTime');
    var endTime = root.querySelector('#endTime');
    var addRangeBtn = root.querySelector('#addRangeBtn');
    var selectedDatesSummary = root.querySelector('#selectedDatesSummary');
    var rangesList = root.querySelector('#rangesList');
    var dayEditor = root.querySelector('#dayEditor');
    var dayEditorTitle = root.querySelector('#dayEditorTitle');
    var dayEditorHint = root.querySelector('#dayEditorHint');
    var daySlotsList = root.querySelector('#daySlotsList');
    var replaceDayBtn = root.querySelector('#replaceDayBtn');
    var clearDayBtn = root.querySelector('#clearDayBtn');
    var saveBtn = root.querySelector('#saveAvailBtn');
    var selectedDatesCount = root.querySelector('#selectedDatesCount');
    var selectedDatesChips = root.querySelector('#selectedDatesChips');
    var calendarLayout = root.querySelector('.calendar-layout');
    var summaryBase = calendarLayout ? (calendarLayout.getAttribute('data-summary-base') || '/calendario/day/summary/') : '/calendario/day/summary/';
    var gestionVisitasUrl = calendarLayout ? (calendarLayout.getAttribute('data-gestion-url') || '/panel_administrativo/gestion_visitas/') : '/panel_administrativo/gestion_visitas/';

    var dayInspectorTitle = root.querySelector('#dayInspectorTitle');
    var dayInspectorBadge = root.querySelector('#dayInspectorBadge');
    var dayInspectorDate = root.querySelector('#dayInspectorDate');
    var dayInspectorRanges = root.querySelector('#dayInspectorRanges');
    var dayInspectorVisits = root.querySelector('#dayInspectorVisits');
    if(!startTime || !endTime || !addRangeBtn || !selectedDatesSummary || !rangesList || !saveBtn){ return; }

    var dayFetchBase = form.getAttribute('data-day-fetch-base') || '/calendario/day/';
    var dayUpdateUrl = form.getAttribute('data-day-update-url') || '/calendario/day/update/';
    var dayDeleteUrl = form.getAttribute('data-day-delete-url') || '/calendario/day/delete/';

    var selectedDates = new Set();
    var ranges = [];
    var currentDay = null;
    var currentDayRanges = [];

    function getCookie(name){ var v = document.cookie.match('(^|;)\\s*'+name+'\\s*=\\s*([^;]+)'); return v ? v.pop() : ''; }

    function setCellAvailability(dateStr, available){
      var td = root.querySelector('table.calendar-table td[data-date="' + dateStr + '"]');
      if(!td) return;
      if(td.classList.contains('other-month') || td.classList.contains('disabled')) return;
      if(td.classList.contains('pending') || td.classList.contains('occupied')) return;
      if(available){
        td.classList.remove('no-available');
        td.classList.add('available');
      } else {
        td.classList.remove('available');
        td.classList.add('no-available');
      }
    }

    function sortDates(list){
      return list.slice().sort(function(a,b){ return a.localeCompare(b); });
    }

    function renderSelectedDates(){
      var items = sortDates(Array.from(selectedDates));
      if(selectedDatesCount){ selectedDatesCount.textContent = String(items.length); }
      if(!items.length){
        if(selectedDatesChips){
          selectedDatesChips.innerHTML = '<span class="empty-day">Selecciona uno o varios días del calendario (lunes a sábado).</span>';
          return;
        }
        selectedDatesSummary.textContent = 'Selecciona uno o varios días del calendario (lunes a sábado).';
        return;
      }
      if(selectedDatesChips){
        selectedDatesChips.innerHTML = items.map(function(item){
          return '<span class="date-chip">' + item + '</span>';
        }).join('');
        return;
      }
      selectedDatesSummary.innerHTML = '<strong>Días seleccionados:</strong> ' + items.join(', ');
    }

    function renderRanges(){
      if(!ranges.length){
        rangesList.textContent = 'Agrega al menos un horario de inicio y fin.';
        return;
      }
      rangesList.innerHTML = '<strong>Horarios:</strong> ' + ranges.map(function(r, idx){
        return '<span class="range-chip">' + r + ' <button type="button" data-remove-range="' + idx + '">×</button></span>';
      }).join(' ');
      rangesList.querySelectorAll('button[data-remove-range]').forEach(function(btn){
        btn.addEventListener('click', function(){
          var index = parseInt(this.getAttribute('data-remove-range'), 10);
          if(index >= 0){
            ranges.splice(index, 1);
            renderRanges();
            refresh();
          }
        });
      });
    }

    function renderDayEditorDisabled(text){
      if(!dayEditor) return;
      dayEditor.classList.add('is-disabled');
      if(dayEditorTitle) dayEditorTitle.textContent = 'Edición del día';
      if(dayEditorHint) dayEditorHint.textContent = text || 'Selecciona un único día para ver, editar o eliminar su disponibilidad.';
      if(daySlotsList) daySlotsList.innerHTML = '';
    }

    function renderDaySlots(){
      if(!dayEditor || !daySlotsList || !dayEditorHint || !dayEditorTitle) return;
      if(!currentDay){
        renderDayEditorDisabled();
        return;
      }

      dayEditor.classList.remove('is-disabled');
      dayEditorTitle.textContent = 'Edición del día ' + currentDay;

      if(!currentDayRanges.length){
        dayEditorHint.textContent = 'Este día no tiene horarios guardados. Agrega rangos y usa “Reemplazar día con horarios agregados”.';
        daySlotsList.innerHTML = '<span class="empty-day">Sin horarios</span>';
        setCellAvailability(currentDay, false);
        return;
      }

      dayEditorHint.textContent = 'Puedes eliminar un rango individual (×), eliminar todo el día o reemplazar con nuevos rangos.';
      daySlotsList.innerHTML = currentDayRanges.map(function(r){
        return '<span class="range-chip day-time-chip">' + r.label + ' <button type="button" data-remove-range-day="' + r.label + '">×</button></span>';
      }).join(' ');

      daySlotsList.querySelectorAll('button[data-remove-range-day]').forEach(function(btn){
        btn.addEventListener('click', function(){
          removeSingleRange(this.getAttribute('data-remove-range-day'));
        });
      });

      setCellAvailability(currentDay, true);
    }

    function loadDayAvailability(dateStr){
      if(!dateStr || !dayEditor) return;
      dayEditor.classList.remove('is-disabled');
      if(dayEditorTitle) dayEditorTitle.textContent = 'Edición del día ' + dateStr;
      if(dayEditorHint) dayEditorHint.textContent = 'Cargando horarios...';
      if(daySlotsList) daySlotsList.innerHTML = '';

      fetch(dayFetchBase + dateStr + '/', { headers: { 'X-Requested-With':'XMLHttpRequest', 'Accept':'application/json' } })
        .then(function(res){ return res.json(); })
        .then(function(json){
          if(!json || !json.ok){
            throw new Error('No fue posible cargar horarios del día');
          }
          currentDay = dateStr;
          currentDayRanges = (json.ranges || []).slice();
          renderDaySlots();
        })
        .catch(function(err){
          console.error(err);
          if(dayEditorHint) dayEditorHint.textContent = 'Error al cargar horarios del día.';
        });
    }

    function refreshDayEditorForSelection(){
      if(selectedDates.size !== 1){
        currentDay = null;
        currentDayRanges = [];
        renderDayEditorDisabled('Selecciona un único día para ver, editar o eliminar su disponibilidad.');
        return;
      }
      var dateStr = Array.from(selectedDates)[0];
      loadDayAvailability(dateStr);
    }

    function removeSingleRange(rangeLabel){
      if(!currentDay || !rangeLabel) return;
      var data = new FormData();
      data.append('date', currentDay);
      data.append('range', rangeLabel);
      fetch(dayDeleteUrl, {
        method: 'POST',
        headers: { 'X-Requested-With':'XMLHttpRequest', 'X-CSRFToken': getCookie('csrftoken'), 'Accept':'application/json' },
        body: data
      })
      .then(function(res){ return res.json(); })
      .then(function(json){
        if(!json || !json.ok){ throw new Error('No se pudo eliminar rango'); }
        currentDayRanges = (json.ranges || []).slice();
        renderDaySlots();
      })
      .catch(function(err){ console.error(err); alert('No se pudo eliminar el rango.'); });
    }

    function canEnable(){ return selectedDates.size > 0 && ranges.length > 0; }
    function refresh(){ saveBtn.disabled = !canEnable(); }

    function getCellState(td){
      if(!td) return 'neutral';
      if(td.classList.contains('occupied')) return 'occupied';
      if(td.classList.contains('pending')) return 'pending';
      if(td.classList.contains('available')) return 'available';
      if(td.classList.contains('no-available')) return 'no-available';
      return 'neutral';
    }

    function renderInspectorBadge(state){
      if(!dayInspectorBadge) return;
      dayInspectorBadge.className = 'inspector-badge';
      if(state === 'available'){
        dayInspectorBadge.classList.add('available');
        dayInspectorBadge.textContent = 'Disponible';
      } else if(state === 'pending'){
        dayInspectorBadge.classList.add('pending');
        dayInspectorBadge.textContent = 'Pendiente';
      } else if(state === 'occupied'){
        dayInspectorBadge.classList.add('occupied');
        dayInspectorBadge.textContent = 'Ocupado';
      } else {
        dayInspectorBadge.classList.add('neutral');
        dayInspectorBadge.textContent = 'Sin selección';
      }
    }

    function renderInspectorRanges(ranges, state){
      if(!dayInspectorRanges) return;
      if(state !== 'available'){
        dayInspectorRanges.innerHTML = '<span class="empty-day">Selecciona un día verde para ver horarios libres.</span>';
        return;
      }
      if(!ranges || !ranges.length){
        dayInspectorRanges.innerHTML = '<span class="empty-day">No hay horarios libres para este día.</span>';
        return;
      }
      dayInspectorRanges.innerHTML = ranges.map(function(r){
        return '<span class="inspector-chip">' + r.label + '</span>';
      }).join('');
    }

    function renderInspectorVisits(visitas, state){
      if(!dayInspectorVisits) return;
      if(state !== 'pending' && state !== 'occupied'){
        dayInspectorVisits.innerHTML = '<div class="inspector-empty">Selecciona un día amarillo o rojo para ver la visita.</div>';
        return;
      }
      if(!visitas || !visitas.length){
        dayInspectorVisits.innerHTML = '<div class="inspector-empty">No hay reservas registradas para este día.</div>';
        return;
      }

      dayInspectorVisits.innerHTML = visitas.map(function(v){
        var estadoClass = v.estado === 'pendiente' ? 'pending' : 'confirmada';
        var showInfoButton = v.estado === 'confirmada';
        var infoPayload = encodeURIComponent(JSON.stringify(v || {}));
        return [
          '<article class="visit-item">',
            '<div class="visit-item-head">',
              '<div>',
                '<span class="visit-type">' + (v.tipo || 'visita') + '</span>',
                '<h5>' + (v.titulo || 'Visita') + '</h5>',
              '</div>',
              '<span class="visit-status ' + estadoClass + '">' + (v.estado_label || v.estado || '') + '</span>',
            '</div>',
            '<p><strong>Responsable:</strong> ' + (v.responsable || 'Sin responsable') + '</p>',
            '<p><strong>Documento:</strong> ' + (v.documento_responsable || 'N/A') + '</p>',
            '<p><strong>Horario:</strong> ' + (v.horario || 'Sin horario') + '</p>',
            '<div class="visit-actions" style="margin-top:8px;display:flex;justify-content:flex-end;">',
              showInfoButton
                ? '<button type="button" class="btn-inspector btn-inspector-danger" data-action="show-info" data-info="' + infoPayload + '">Ver informacion</button>'
                : '<button type="button" class="btn-inspector btn-inspector-warning" data-action="go-gestion">Ir a Gestion de Visitas</button>',
            '</div>',
          '</article>'
        ].join('');
      }).join('');

      dayInspectorVisits.querySelectorAll('button[data-action="go-gestion"]').forEach(function(btn){
        btn.addEventListener('click', function(){
          window.location.href = gestionVisitasUrl;
        });
      });

      dayInspectorVisits.querySelectorAll('button[data-action="show-info"]').forEach(function(btn){
        btn.addEventListener('click', function(){
          var raw = btn.getAttribute('data-info') || '';
          try {
            var info = JSON.parse(decodeURIComponent(raw));
            var message = [
              'Tipo: ' + (info.tipo || 'N/A'),
              'Estado: ' + (info.estado_label || info.estado || 'N/A'),
              'Responsable: ' + (info.responsable || 'N/A'),
              'Documento: ' + (info.documento_responsable || 'N/A'),
              'Horario: ' + (info.horario || 'N/A')
            ].join('\n');
            alert(message);
          } catch (e) {
            alert('No fue posible mostrar la informacion de la visita.');
          }
        });
      });
    }

    function loadDayInspector(dateStr, preferredState){
      if(!dateStr || !dayInspectorDate) return;
      if(dayInspectorTitle) dayInspectorTitle.textContent = 'Resumen del día';
      dayInspectorDate.textContent = 'Cargando información de ' + dateStr + '...';
      renderInspectorBadge('neutral');

      fetch(summaryBase + dateStr + '/', { headers: { 'X-Requested-With':'XMLHttpRequest', 'Accept':'application/json' } })
        .then(function(res){ return res.json(); })
        .then(function(json){
          if(!json || !json.ok){ throw new Error('No se pudo cargar el resumen del día'); }
          var state = json.day_state || preferredState || 'neutral';
          if(dayInspectorDate){ dayInspectorDate.textContent = json.date_formatted || dateStr; }
          renderInspectorBadge(state);
          renderInspectorRanges(json.available_ranges || [], state);
          renderInspectorVisits(json.visitas || [], state);
        })
        .catch(function(err){
          console.error(err);
          if(dayInspectorDate){ dayInspectorDate.textContent = 'No se pudo cargar el resumen del día.'; }
          renderInspectorBadge('neutral');
          renderInspectorRanges([], 'neutral');
          renderInspectorVisits([], 'neutral');
        });
    }

    var calendarTable = root.querySelector('table.calendar-table');
    if(calendarTable){
      calendarTable.addEventListener('click', function(ev){
        var td = ev.target.closest('td[data-date]');
        if(!td || !calendarTable.contains(td)) return;
        if(td.classList.contains('other-month') || td.classList.contains('disabled')) return;
        var d = td.getAttribute('data-date');
        if(!d) return;

        var state = getCellState(td);
        loadDayInspector(d, state);

        // Días con reserva: solo mostrar panel de detalle, no permitir selección múltiple para guardado.
        if(state === 'pending' || state === 'occupied'){
          return;
        }

        if(selectedDates.has(d)){
          selectedDates.delete(d);
          td.classList.remove('selected-day');
        } else {
          selectedDates.add(d);
          td.classList.add('selected-day');
        }
        renderSelectedDates();
        refreshDayEditorForSelection();
        refresh();
      });
    }

    addRangeBtn.addEventListener('click', function(){
      var s = (startTime.value || '').trim();
      var e = (endTime.value || '').trim();
      if(!s || !e){
        alert('Selecciona hora de inicio y hora fin.');
        return;
      }
      if(s >= e){
        alert('La hora fin debe ser mayor que la hora inicio.');
        return;
      }
      var key = s + '-' + e;
      if(ranges.indexOf(key) === -1){
        ranges.push(key);
      }
      renderRanges();
      refresh();
    });

    if(replaceDayBtn){
      replaceDayBtn.addEventListener('click', function(){
        if(selectedDates.size !== 1){
          alert('Selecciona un único día para reemplazar su disponibilidad.');
          return;
        }
        if(!ranges.length){
          alert('Agrega al menos un rango antes de reemplazar el día.');
          return;
        }
        var day = Array.from(selectedDates)[0];
        var data = new FormData();
        data.append('date', day);
        ranges.forEach(function(r){ data.append('ranges', r); });
        fetch(dayUpdateUrl, {
          method: 'POST',
          headers: { 'X-Requested-With':'XMLHttpRequest', 'X-CSRFToken': getCookie('csrftoken'), 'Accept':'application/json' },
          body: data
        })
        .then(function(res){ return res.json(); })
        .then(function(json){
          if(!json || !json.ok){ throw new Error('No se pudo reemplazar disponibilidad'); }
          currentDay = day;
          currentDayRanges = (json.ranges || []).slice();
          setCellAvailability(day, currentDayRanges.length > 0);
          ranges = [];
          renderRanges();
          renderDaySlots();
          refresh();
        })
        .catch(function(err){ console.error(err); alert('Error al reemplazar disponibilidad del día.'); });
      });
    }

    if(clearDayBtn){
      clearDayBtn.addEventListener('click', function(){
        if(selectedDates.size !== 1){
          alert('Selecciona un único día para quitar su disponibilidad.');
          return;
        }
        var day = Array.from(selectedDates)[0];
        var data = new FormData();
        data.append('date', day);
        fetch(dayDeleteUrl, {
          method: 'POST',
          headers: { 'X-Requested-With':'XMLHttpRequest', 'X-CSRFToken': getCookie('csrftoken'), 'Accept':'application/json' },
          body: data
        })
        .then(function(res){ return res.json(); })
        .then(function(json){
          if(!json || !json.ok){ throw new Error('No se pudo eliminar disponibilidad del día'); }
          currentDay = day;
          currentDayRanges = [];
          setCellAvailability(day, false);
          renderDaySlots();
        })
        .catch(function(err){ console.error(err); alert('Error al quitar la disponibilidad del día.'); });
      });
    }

    if(startTime) startTime.addEventListener('change', refresh);
    if(endTime) endTime.addEventListener('change', refresh);

    form.addEventListener('submit', function(e){
      e.preventDefault();
      if(!selectedDates.size){ alert('Selecciona al menos un día del calendario.'); return false; }
      if(!ranges.length){ alert('Agrega al menos un horario con inicio y fin.'); return false; }

      var data = new FormData();
      Array.from(selectedDates).forEach(function(d){ data.append('dates', d); });
      ranges.forEach(function(r){ data.append('ranges', r); });
      fetch(form.action, { method:'POST', headers:{ 'X-Requested-With':'XMLHttpRequest', 'X-CSRFToken':getCookie('csrftoken'), 'Accept':'application/json' }, body:data })
      .then(function(res){ return res.json(); })
      .then(function(json){
        if(json.available_dates){
          var avail = new Set();
          root.querySelectorAll('table.calendar-table td[data-date].available').forEach(function(td){
            var d0 = td.getAttribute('data-date');
            if(d0){ avail.add(d0); }
          });
          (json.available_dates || []).forEach(function(d){ avail.add(d); });

          // Para cada celda visible del calendario: marcar disponible o deshabilitar
          root.querySelectorAll('table.calendar-table td[data-date]').forEach(function(td){
            if(td.classList.contains('other-month') || td.classList.contains('disabled')) return;
            if(td.classList.contains('pending') || td.classList.contains('occupied')) return;
            var d = td.getAttribute('data-date');
            if(avail.has(d)){
              td.classList.remove('no-available');
              td.classList.add('available');
            } else {
              td.classList.remove('available');
              td.classList.add('no-available');
            }
            td.classList.remove('selected-day');
          });

          selectedDates.clear();
          ranges = [];
          renderSelectedDates();
          renderRanges();
          renderDayEditorDisabled();
          root.querySelectorAll('table.calendar-table td.selected-day').forEach(function(td){ td.classList.remove('selected-day'); });
          if(startTime) startTime.value = '';
          if(endTime) endTime.value = '';
          saveBtn.textContent = 'Guardado';
          setTimeout(function(){ saveBtn.textContent = 'Guardar Disponibilidades'; }, 1600);
          if(selectedDatesCount){ selectedDatesCount.textContent = '0'; }
          refresh();
        } else {
          alert('Disponibilidades guardadas.');
        }
      })
      .catch(function(err){ console.error(err); alert('Error al guardar disponibilidades.'); });
    });

    // initial state
    renderSelectedDates();
    renderRanges();
    renderDayEditorDisabled();
    refresh();
  }

  window.initAvailabilityControls = initAvailabilityControls;

  // Auto-init en carga normal de página
  document.addEventListener('DOMContentLoaded', function(){
    const container = document.querySelector('.calendar-card');
    const page = document.querySelector('.calendar-page');
    if(container) initCalendar(container);
    // Inicializar controles de disponibilidad en carga normal
    if(page && window.initAvailabilityControls){ window.initAvailabilityControls(page); }
  });
})();
