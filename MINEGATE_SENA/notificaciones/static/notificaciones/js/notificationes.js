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

    function loadList(){
      const q = search ? encodeURIComponent(search.value.trim()) : '';
      const p = priority ? priority.value : '';
      const url = `/notificaciones/?q=${q}&priority=${p}`;
      fetch(url, {headers:{'X-Requested-With':'XMLHttpRequest'}})
        .then(r=>{ if(!r.ok) throw new Error('HTTP '+r.status); return r.text(); })
        .then(html=>{ if(container) container.innerHTML = html; attachButtons(); })
        .catch(e=>{
          console.error('notifications.loadList error', e);
          if(container) container.innerHTML = '<div class="sin-notificaciones">Error cargando notificaciones</div>';
        });
    }

    function attachButtons(){
      (container ? container : document).querySelectorAll('.btn-mark-read').forEach(btn=>{
        btn.onclick = function(){
          const id = this.dataset.id;
          fetch(`/notificaciones/mark_read/${id}/`, {method:'POST', headers:{'X-CSRFToken': getCsrf(), 'X-Requested-With':'XMLHttpRequest'}})
            .then(r=>{ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
            .then(()=>{ if(search||priority) loadList(); else if(container) loadList(); })
            .catch(e=>console.error('mark_read error', e));
        };
      });
      (container ? container : document).querySelectorAll('.btn-delete').forEach(btn=>{
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

    if(search) search.addEventListener('input', debounce(loadList, 350));
    if(priority) priority.addEventListener('change', loadList);

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
