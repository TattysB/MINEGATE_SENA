(function(){
  function getCsrf(){
    const name = 'csrftoken';
    const match = document.cookie.match(new RegExp('(^|;)\\s*'+name+'=([^;]+)'));
    return match ? match.pop() : '';
  }

  function debounce(fn, ms){
    let t;
    return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), ms); };
  }

  function createNotificationsController(root){
    const container = root.querySelector('#notif-list-container') || document.getElementById('notif-list-container');
    const search = root.querySelector('#notif-search');
    const priority = root.querySelector('#notif-priority');
    const dateFrom = root.querySelector('#notif-date-from');
    const dateTo = root.querySelector('#notif-date-to');

    function loadList(){
      const q = search ? encodeURIComponent(search.value.trim()) : '';
      const p = priority ? priority.value : '';
      const df = dateFrom && dateFrom.value ? dateFrom.value : '';
      const dt = dateTo && dateTo.value ? dateTo.value : '';
      const url = `/notificaciones/?q=${q}&priority=${p}&date_from=${df}&date_to=${dt}`;
      fetch(url, {headers:{'X-Requested-With':'XMLHttpRequest'}})
        .then(r=>{ if(!r.ok) throw new Error('HTTP '+r.status); return r.text(); })
        .then(html=>{
          if(!container) return;
          // Si existe una columna para la lista, inyectar allí para preservar la columna de detalle
          const listCol = container.querySelector('.notif-list-column');
          if(listCol){ listCol.innerHTML = html; attachButtons(); attachDetailHandlers(); }
          else { container.innerHTML = html; attachButtons(); attachDetailHandlers(); }
        })
        .catch(e=>{
          console.error('notifications.loadList error', e);
          if(container) container.innerHTML = '<div class="sin-notificaciones">Error cargando notificaciones</div>';
        });
    }

    function attachButtons(){
      const base = (container ? container : document);
      base.querySelectorAll('.btn-mark-read').forEach(btn=>{
        btn.onclick = function(){
          const id = this.dataset.id;
          fetch(`/notificaciones/mark_read/${id}/`, {method:'POST', headers:{'X-CSRFToken': getCsrf(), 'X-Requested-With':'XMLHttpRequest'}})
            .then(r=>{ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
            .then(()=>{ if(search||priority) loadList(); else if(container) loadList(); })
            .catch(e=>console.error('mark_read error', e));
        };
      });
      base.querySelectorAll('.btn-delete').forEach(btn=>{
        btn.onclick = function(){
          if(!confirm('Eliminar notificación?')) return;
          const id = this.dataset.id;
          fetch(`/notificaciones/delete/${id}/`, {method:'POST', headers:{'X-CSRFToken': getCsrf(), 'X-Requested-With':'XMLHttpRequest'}})
            .then(r=>{ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
            .then(()=>{ if(search||priority) loadList(); else if(container) loadList(); })
            .catch(e=>console.error('delete error', e));
        };
      });
    }

    function attachDetailHandlers(){
      try{
        if(!container) return;
        const listCol = container.querySelector('.notif-list-column') || container;
        const detailPane = container.querySelector('#notif-detail-pane');
        if(!listCol || !detailPane) return;
        // remove previous handlers by cloning
        const newListCol = listCol.cloneNode(true);
        listCol.parentNode.replaceChild(newListCol, listCol);
        // attach click to items
        newListCol.querySelectorAll('.notif-item').forEach(item=>{
          item.addEventListener('click', function(ev){
            // ignore clicks on action buttons
            if(ev.target.closest('.btn-mark-read') || ev.target.closest('.btn-delete')) return;
            const id = this.dataset.id;
            if(!id) return;
            detailPane.innerHTML = 'Cargando detalle...';
            fetch(`/notificaciones/detail/${id}/`, {headers:{'X-Requested-With':'XMLHttpRequest'}})
              .then(r=>{ if(!r.ok) throw new Error('HTTP '+r.status); return r.text(); })
              .then(html=>{ detailPane.innerHTML = html; })
              .catch(e=>{ console.error('detail load error', e); detailPane.innerHTML = '<div class="notif-empty">No se pudo cargar el detalle.</div>'; });
          });
        });
      }catch(e){ console.error('attachDetailHandlers error', e); }
    }

    if(search) search.addEventListener('input', debounce(loadList, 350));
    if(priority) priority.addEventListener('change', loadList);
    if(dateFrom) dateFrom.addEventListener('change', loadList);
    if(dateTo) dateTo.addEventListener('change', loadList);

    return {
      loadList,
      attachButtons,
    };
  }

  // Expose initializer for dynamically injected content
  window.initNotifications = function(rootElement){
    try{
      const root = rootElement instanceof Element ? rootElement : document;
      const ctrl = createNotificationsController(root);
      // if the container exists, load via AJAX the list fragment
      const container = root.querySelector('#notif-list-container') || document.getElementById('notif-list-container');
      if(container) ctrl.loadList();
      return ctrl;
    }catch(e){ console.error('initNotifications error', e); }
  };

  // Auto-init on initial page load if notifications container is present
  document.addEventListener('DOMContentLoaded', function(){
    if(document.getElementById('notif-list-container')){
      window.initNotifications(document);
    }
  });

})();
