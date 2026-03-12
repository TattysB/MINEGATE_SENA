(function () {
  if (window.__minegateCustomModalLoaded) {
    return;
  }
  window.__minegateCustomModalLoaded = true;

  var resolveModal = null;
  var nativeAlert = window.alert ? window.alert.bind(window) : function () { };

  function ensureModalMarkup() {
    var overlay = document.getElementById('customModal');
    if (overlay) {
      return overlay;
    }

    overlay = document.createElement('div');
    overlay.id = 'customModal';
    overlay.className = 'cm-overlay';
    overlay.innerHTML =
      '<div class="cm-box" id="cmBox">' +
      '  <div class="cm-icon" id="cmIcon"></div>' +
      '  <h3 class="cm-title" id="cmTitle"></h3>' +
      '  <p class="cm-message" id="cmMessage"></p>' +
      '  <div class="cm-input-wrap" id="cmInputWrap" style="display:none;">' +
      '    <textarea id="cmInput" class="cm-input" rows="3" placeholder="Escriba aquí..."></textarea>' +
      '  </div>' +
      '  <div class="cm-buttons" id="cmButtons"></div>' +
      '</div>';

    document.body.appendChild(overlay);
    return overlay;
  }

  function closeModal(overlay, value) {
    overlay.classList.remove('active');
    if (resolveModal) {
      var resolver = resolveModal;
      resolveModal = null;
      resolver(value);
    }
  }

  function showModal(opts) {
    return new Promise(function (resolve) {
      resolveModal = resolve;

      var overlay = ensureModalMarkup();
      var icon = document.getElementById('cmIcon');
      var title = document.getElementById('cmTitle');
      var message = document.getElementById('cmMessage');
      var inputWrap = document.getElementById('cmInputWrap');
      var input = document.getElementById('cmInput');
      var buttons = document.getElementById('cmButtons');

      if (!overlay || !icon || !title || !message || !inputWrap || !input || !buttons) {
        resolve(null);
        return;
      }

      icon.className = 'cm-icon ' + (opts.iconClass || 'cm-info');
      icon.innerHTML = opts.icon || '';
      title.textContent = opts.title || '';
      message.innerHTML = (opts.message || '').replace(/\n/g, '<br>');

      if (opts.showInput) {
        inputWrap.style.display = 'block';
        input.value = '';
        input.placeholder = opts.placeholder || 'Escriba aquí...';
      } else {
        inputWrap.style.display = 'none';
      }

      buttons.innerHTML = '';
      (opts.buttons || []).forEach(function (buttonConfig) {
        var button = document.createElement('button');
        button.className = 'cm-btn ' + (buttonConfig.class || 'cm-btn-primary');
        button.innerHTML = buttonConfig.html || buttonConfig.text || '';
        button.onclick = function () {
          if (opts.showInput && buttonConfig.value === true) {
            closeModal(overlay, input.value);
            return;
          }
          closeModal(overlay, buttonConfig.value);
        };
        buttons.appendChild(button);
      });

      overlay.classList.add('active');

      if (opts.showInput) {
        setTimeout(function () { input.focus(); }, 100);
      }
    });
  }

  function normalizeType(message, type) {
    if (type) return type;
    var msg = String(message || '').toLowerCase();
    if (msg.indexOf('error') !== -1 || msg.indexOf('no se pudo') !== -1) return 'error';
    if (msg.indexOf('elimin') !== -1) return 'warning';
    if (msg.indexOf('exito') !== -1 || msg.indexOf('guardad') !== -1 || msg.indexOf('aprobad') !== -1) return 'success';
    return 'info';
  }

  function alertModal(message, type) {
    var t = normalizeType(message, type);
    var cfg = {
      success: { icon: '<i class="fas fa-check"></i>', iconClass: 'cm-success', title: 'Operación exitosa', btn: 'cm-btn-success' },
      error: { icon: '<i class="fas fa-xmark"></i>', iconClass: 'cm-error', title: 'Error', btn: 'cm-btn-danger' },
      warning: { icon: '<i class="fas fa-triangle-exclamation"></i>', iconClass: 'cm-warning', title: 'Atención', btn: 'cm-btn-warning' },
      info: { icon: '<i class="fas fa-circle-info"></i>', iconClass: 'cm-info', title: 'Información', btn: 'cm-btn-primary' }
    }[t] || { icon: '<i class="fas fa-circle-info"></i>', iconClass: 'cm-info', title: 'Información', btn: 'cm-btn-primary' };

    return showModal({
      icon: cfg.icon,
      iconClass: cfg.iconClass,
      title: cfg.title,
      message: String(message || ''),
      buttons: [{ text: 'Aceptar', class: cfg.btn, value: true }]
    });
  }

  function confirmModal(message, opts) {
    var options = opts || {};
    var ctx = ((options.title || '') + ' ' + String(message || '') + ' ' + (options.confirmText || '')).toLowerCase();

    var inferred = {
      icon: '<i class="fas fa-circle-question"></i>',
      iconClass: 'cm-info',
      confirmClass: 'cm-btn-primary',
      confirmText: 'Confirmar',
      confirmIcon: 'fas fa-check'
    };

    if (ctx.indexOf('elimin') !== -1 || ctx.indexOf('borrar') !== -1 || ctx.indexOf('delete') !== -1) {
      inferred = {
        icon: '<i class="fas fa-trash"></i>',
        iconClass: 'cm-danger-soft',
        confirmClass: 'cm-btn-danger',
        confirmText: 'Eliminar',
        confirmIcon: 'fas fa-trash'
      };
    } else if (ctx.indexOf('cerrar sesi') !== -1 || ctx.indexOf('logout') !== -1 || ctx.indexOf('salir') !== -1) {
      inferred = {
        icon: '<i class="fas fa-right-from-bracket"></i>',
        iconClass: 'cm-warning',
        confirmClass: 'cm-btn-success',
        confirmText: 'Sí, Cerrar Sesión',
        confirmIcon: 'fas fa-right-from-bracket'
      };
    } else if (ctx.indexOf('enviar') !== -1 || ctx.indexOf('finalizar') !== -1) {
      inferred = {
        icon: '<i class="fas fa-paper-plane"></i>',
        iconClass: 'cm-info',
        confirmClass: 'cm-btn-success',
        confirmText: 'Sí, enviar',
        confirmIcon: 'fas fa-paper-plane'
      };
    } else if (ctx.indexOf('aprobar') !== -1 || ctx.indexOf('confirmar visita') !== -1) {
      inferred = {
        icon: '<i class="fas fa-check-circle"></i>',
        iconClass: 'cm-success',
        confirmClass: 'cm-btn-success',
        confirmText: 'Aprobar',
        confirmIcon: 'fas fa-check'
      };
    }

    return showModal({
      icon: options.icon || inferred.icon,
      iconClass: options.iconClass || inferred.iconClass,
      title: options.title || 'Confirmar acción',
      message: String(message || ''),
      buttons: [
        { text: options.cancelText || 'Cancelar', class: 'cm-btn-cancel', value: false },
        {
          html: (options.confirmIcon ? ('<i class="' + options.confirmIcon + ' me-1"></i>') : ('<i class="' + inferred.confirmIcon + ' me-1"></i>')) + (options.confirmText || inferred.confirmText),
          class: options.confirmClass || inferred.confirmClass,
          value: true
        }
      ]
    });
  }

  function promptModal(message, opts) {
    var options = opts || {};
    return showModal({
      icon: options.icon || '<i class="fas fa-pen"></i>',
      iconClass: options.iconClass || 'cm-info',
      title: options.title || 'Ingrese información',
      message: String(message || ''),
      showInput: true,
      placeholder: options.placeholder || 'Escriba aquí...',
      buttons: [
        { text: 'Cancelar', class: 'cm-btn-cancel', value: null },
        { text: options.confirmText || 'Enviar', class: options.confirmClass || 'cm-btn-primary', value: true }
      ]
    });
  }

  function extractConfirmMessage(attrValue) {
    if (!attrValue) return '¿Desea continuar?';
    var match = attrValue.match(/confirm\((['"])([\s\S]*?)\1\)/);
    return match && match[2] ? match[2] : '¿Desea continuar?';
  }

  function attachInlineConfirmInterceptor() {
    document.addEventListener('submit', function (event) {
      var form = event.target;
      if (!form || !form.getAttribute) return;
      if (form.dataset.cmBypassSubmit === '1') {
        form.dataset.cmBypassSubmit = '0';
        return;
      }

      var onsubmit = form.getAttribute('onsubmit') || '';
      if (onsubmit.indexOf('confirm(') === -1) return;

      event.preventDefault();
      var message = extractConfirmMessage(onsubmit);
      confirmModal(message, { title: 'Confirmar acción' }).then(function (ok) {
        if (!ok) return;
        form.dataset.cmBypassSubmit = '1';
        form.submit();
      });
    }, true);

    document.addEventListener('click', function (event) {
      var target = event.target;
      if (!target || !target.closest) return;
      var trigger = target.closest('[onclick*="confirm("]');
      if (!trigger || !trigger.getAttribute) return;

      var onclick = trigger.getAttribute('onclick') || '';
      if (onclick.indexOf('confirm(') === -1) return;

      event.preventDefault();
      event.stopImmediatePropagation();
      var message = extractConfirmMessage(onclick);

      confirmModal(message, { title: 'Confirmar acción' }).then(function (ok) {
        if (!ok) return;
        if (trigger.tagName === 'A' && trigger.href) {
          window.location.href = trigger.href;
          return;
        }
        if (trigger.form) {
          trigger.form.submit();
        }
      });
    }, true);
  }

  window.mAlert = alertModal;
  window.mConfirm = confirmModal;
  window.mPrompt = promptModal;

  // Reemplaza alert nativo para unificar la experiencia visual.
  window.alert = function (message) {
    return alertModal(message, null);
  };

  document.addEventListener('DOMContentLoaded', function () {
    var overlay = ensureModalMarkup();
    if (!overlay) {
      return;
    }

    overlay.addEventListener('click', function (event) {
      if (event.target === overlay) {
        closeModal(overlay, null);
      }
    });

    attachInlineConfirmInterceptor();
  });

  // Fallback si por alguna razón no se pudo crear el modal.
  window.mNativeAlert = nativeAlert;
})();
