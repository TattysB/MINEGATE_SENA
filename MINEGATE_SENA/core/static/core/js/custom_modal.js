(function () {
  let resolveModal = null;

  function showModal(opts) {
    return new Promise((resolve) => {
      resolveModal = resolve;

      const overlay = document.getElementById('customModal');
      const icon = document.getElementById('cmIcon');
      const title = document.getElementById('cmTitle');
      const message = document.getElementById('cmMessage');
      const inputWrap = document.getElementById('cmInputWrap');
      const input = document.getElementById('cmInput');
      const buttons = document.getElementById('cmButtons');

      if (!overlay || !icon || !title || !message || !inputWrap || !input || !buttons) {
        resolve(null);
        return;
      }

      icon.className = 'cm-icon ' + (opts.iconClass || 'cm-info');
      icon.innerHTML = opts.icon || '';
      title.textContent = opts.title || '';
      message.innerHTML = opts.message || '';

      if (opts.showInput) {
        inputWrap.style.display = 'block';
        input.value = '';
        input.placeholder = opts.placeholder || 'Escriba aquí...';
      } else {
        inputWrap.style.display = 'none';
      }

      buttons.innerHTML = '';
      (opts.buttons || []).forEach((buttonConfig) => {
        const button = document.createElement('button');
        button.className = 'cm-btn ' + (buttonConfig.class || 'cm-btn-primary');
        button.textContent = buttonConfig.text;
        button.onclick = () => {
          overlay.classList.remove('active');
          if (opts.showInput && buttonConfig.value === true) {
            resolve(input.value);
          } else {
            resolve(buttonConfig.value);
          }
        };
        buttons.appendChild(button);
      });

      overlay.classList.add('active');

      if (opts.showInput) {
        setTimeout(() => input.focus(), 100);
      }
    });
  }

  function alertModal(message, type) {
    const configs = {
      success: { icon: '<i class="ri-check-line"></i>', iconClass: 'cm-success', title: '¡Exitoso!' },
      error: { icon: '<i class="ri-close-line"></i>', iconClass: 'cm-error', title: 'Error' },
      warning: { icon: '<i class="ri-alert-line"></i>', iconClass: 'cm-warning', title: 'Atención' },
      info: { icon: '<i class="ri-information-line"></i>', iconClass: 'cm-info', title: 'Información' },
    };

    const config = configs[type] || configs.info;

    if (!type) {
      if (message.includes('✅') || message.includes('exitoso') || message.includes('aprobad') || message.includes('confirmad') || message.includes('enviad')) {
        config.iconClass = 'cm-success';
        config.icon = '<i class="ri-check-line"></i>';
        config.title = '¡Exitoso!';
      } else if (message.includes('Error') || message.includes('error') || message.includes('❌')) {
        config.iconClass = 'cm-error';
        config.icon = '<i class="ri-close-line"></i>';
        config.title = 'Error';
      } else if (message.includes('⚠') || message.includes('Debe')) {
        config.iconClass = 'cm-warning';
        config.icon = '<i class="ri-alert-line"></i>';
        config.title = 'Atención';
      }
    }

    return showModal({
      icon: config.icon,
      iconClass: config.iconClass,
      title: config.title,
      message,
      buttons: [{ text: 'Aceptar', class: 'cm-btn-primary', value: true }],
    });
  }

  function confirmModal(message, opts = {}) {
    return showModal({
      icon: opts.icon || '<i class="ri-question-line"></i>',
      iconClass: opts.iconClass || 'cm-question',
      title: opts.title || 'Confirmar',
      message,
      buttons: [
        { text: opts.cancelText || 'Cancelar', class: 'cm-btn-cancel', value: false },
        { text: opts.confirmText || 'Sí, confirmar', class: opts.confirmClass || 'cm-btn-primary', value: true },
      ],
    });
  }

  function promptModal(message, opts = {}) {
    return showModal({
      icon: opts.icon || '<i class="ri-edit-line"></i>',
      iconClass: opts.iconClass || 'cm-info',
      title: opts.title || 'Ingrese información',
      message,
      showInput: true,
      placeholder: opts.placeholder || 'Escriba aquí...',
      buttons: [
        { text: 'Cancelar', class: 'cm-btn-cancel', value: null },
        { text: opts.confirmText || 'Enviar', class: opts.confirmClass || 'cm-btn-primary', value: true },
      ],
    });
  }

  window.mAlert = alertModal;
  window.mConfirm = confirmModal;
  window.mPrompt = promptModal;

  document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.getElementById('customModal');
    if (!overlay) {
      return;
    }

    overlay.addEventListener('click', function (event) {
      if (event.target === this) {
        this.classList.remove('active');
        if (resolveModal) {
          resolveModal(null);
          resolveModal = null;
        }
      }
    });
  });
})();
