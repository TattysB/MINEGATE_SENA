(function () {
  function ensureCss(src) {
    if (!src || document.querySelector("link[href='" + src + "']")) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = src;
    document.head.appendChild(link);
  }

  function ensureScript(src) {
    return new Promise((resolve) => {
      if (!src || document.querySelector("script[src='" + src + "']")) return resolve();
      const script = document.createElement('script');
      script.src = src;
      script.onload = () => resolve();
      document.body.appendChild(script);
    });
  }

  function initPanelCalendarLoader() {
    const config = window.calendarioPanelConfig || {};
    const calendarioLink = document.querySelector("a[href='" + config.calendarioIndexUrl + "']");

    if (!calendarioLink || !config.calendarioIndexUrl) return;

    calendarioLink.addEventListener('click', function (event) {
      event.preventDefault();

      ensureCss(config.calendarioCssUrl);

      fetch(config.calendarioIndexUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then((response) => response.text())
        .then((html) => {
          const main = document.getElementById('mainContent');
          if (!main) return;

          if (!window._previousMainHTML) {
            window._previousMainHTML = main.innerHTML;
          }

          main.innerHTML = html;
          main.classList.add('calendar-in-panel');

          ensureScript(config.calendarioJsUrl).then(() => {
            const newContainer = main.querySelector('.calendar-card');
            const page = main.querySelector('.calendar-page');

            if (window.initCalendar && newContainer) {
              window.initCalendar(newContainer);
            }
            if (window.initAvailabilityControls && page) {
              window.initAvailabilityControls(page);
            }
            if (typeof main.scrollIntoView === 'function') {
              main.scrollIntoView({ behavior: 'smooth' });
            }
          });
        })
        .catch((error) => console.error('Error cargando calendario:', error));
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPanelCalendarLoader);
  } else {
    initPanelCalendarLoader();
  }
})();
