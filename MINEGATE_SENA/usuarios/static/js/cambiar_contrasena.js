function checkPasswordStrength(password) {
  const requirements = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /\d/.test(password),
    special: /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;'`~]/.test(password)
  };

  const metCount = Object.values(requirements).filter(Boolean).length;

  let strengthText = '';
  let strengthClass = '';

  if (password.length === 0) {
    strengthText = '';
    strengthClass = '';
  } else if (metCount <= 2) {
    strengthText = 'Muy débil';
    strengthClass = 'strength-weak';
  } else if (metCount === 3) {
    strengthText = 'Media';
    strengthClass = 'strength-medium';
  } else if (metCount === 4) {
    strengthText = 'Buena';
    strengthClass = 'strength-good';
  } else {
    strengthText = 'Segura';
    strengthClass = 'strength-strong';
  }

  return { requirements, metCount, strengthText, strengthClass };
}

function createPasswordStrengthUI(passwordInput) {
  if (!passwordInput) return;

  const inputWrapper = passwordInput.closest('.mb-3');
  if (!inputWrapper || inputWrapper.querySelector('.password-strength-container')) return;

  const strengthContainer = document.createElement('div');
  strengthContainer.className = 'password-strength-container';
  strengthContainer.innerHTML = `
      <div class="strength-bar-wrapper">
        <div class="strength-bar">
          <div class="strength-bar-fill"></div>
        </div>
        <span class="strength-text"></span>
      </div>
      <div class="password-requirements-dynamic">
        <div class="requirement unmet" data-req="length">
          <i class="fa-solid fa-circle-xmark req-icon"></i>
          <span>Mínimo 8 caracteres</span>
        </div>
        <div class="requirement unmet" data-req="uppercase">
          <i class="fa-solid fa-circle-xmark req-icon"></i>
          <span>Una letra mayúscula</span>
        </div>
        <div class="requirement unmet" data-req="lowercase">
          <i class="fa-solid fa-circle-xmark req-icon"></i>
          <span>Una letra minúscula</span>
        </div>
        <div class="requirement unmet" data-req="number">
          <i class="fa-solid fa-circle-xmark req-icon"></i>
          <span>Un número</span>
        </div>
        <div class="requirement unmet" data-req="special">
          <i class="fa-solid fa-circle-xmark req-icon"></i>
          <span>Un carácter especial (!@#$%...)</span>
        </div>
      </div>
    `;

  const helpText = inputWrapper.querySelector('.form-text');
  if (helpText) {
    helpText.after(strengthContainer);
  } else {
    passwordInput.after(strengthContainer);
  }

  passwordInput.addEventListener('input', function () {
    updatePasswordStrengthUI(this.value, strengthContainer);
  });

  passwordInput.addEventListener('focus', function () {
    strengthContainer.classList.add('visible');
  });

  passwordInput.addEventListener('blur', function () {
    if (!this.value) {
      strengthContainer.classList.remove('visible');
    }
  });
}

function updatePasswordStrengthUI(password, container) {
  if (!container) return;

  const result = checkPasswordStrength(password);
  const barFill = container.querySelector('.strength-bar-fill');
  const strengthText = container.querySelector('.strength-text');
  const requirements = container.querySelectorAll('.requirement');

  barFill.className = 'strength-bar-fill';
  if (result.strengthClass) {
    barFill.classList.add(result.strengthClass);
  }

  barFill.style.width = ((result.metCount / 5) * 100) + '%';
  strengthText.textContent = result.strengthText;
  strengthText.className = 'strength-text ' + result.strengthClass;

  requirements.forEach(req => {
    const reqName = req.dataset.req;
    const icon = req.querySelector('.req-icon');
    const isMet = result.requirements[reqName];

    if (isMet) {
      req.classList.add('met');
      req.classList.remove('unmet');
      icon.className = 'fa-solid fa-circle-check req-icon';
    } else {
      req.classList.remove('met');
      req.classList.add('unmet');
      icon.className = 'fa-solid fa-circle-xmark req-icon';
    }
  });

  if (password.length > 0) {
    container.classList.add('visible');
  }
}

function showFieldErrorInline(input, message) {
  if (!input) return;

  const container = input.closest('.mb-3');
  if (!container) return;

  const existingError = container.querySelector('.field-error-inline');
  if (existingError) existingError.remove();

  const errorDiv = document.createElement('div');
  errorDiv.className = 'field-error-inline';
  errorDiv.innerHTML = '<i class="ri-error-warning-line"></i> ' + message;
  container.appendChild(errorDiv);

  input.classList.add('is-invalid');
}

function setNewPasswordFieldsState(oldPasswordInput, pass1Input, pass2Input) {
  if (!oldPasswordInput || !pass1Input || !pass2Input) return;

  const hasOldPassword = oldPasswordInput.value.trim().length > 0;
  pass1Input.disabled = !hasOldPassword;
  pass2Input.disabled = !hasOldPassword;

  if (!hasOldPassword) {
    pass1Input.value = '';
    pass2Input.value = '';
    pass1Input.classList.remove('is-invalid');
    pass2Input.classList.remove('is-invalid');

    const pass1Container = pass1Input.closest('.mb-3');
    const strengthContainer = pass1Container?.querySelector('.password-strength-container');
    if (strengthContainer) {
      strengthContainer.classList.remove('visible');
      const barFill = strengthContainer.querySelector('.strength-bar-fill');
      const strengthText = strengthContainer.querySelector('.strength-text');
      const requirements = strengthContainer.querySelectorAll('.requirement');

      if (barFill) {
        barFill.className = 'strength-bar-fill';
        barFill.style.width = '0%';
      }

      if (strengthText) {
        strengthText.className = 'strength-text';
        strengthText.textContent = '';
      }

      requirements.forEach(req => {
        req.classList.remove('met');
        req.classList.add('unmet');
        const icon = req.querySelector('.req-icon');
        if (icon) {
          icon.className = 'fa-solid fa-circle-xmark req-icon';
        }
      });
    }
  }
}

function setupChangePasswordValidation() {
  const form = document.getElementById('changePasswordForm');
  if (!form) return;

  const oldPasswordInput = document.getElementById('id_old_password');
  const pass1Input = document.getElementById('id_new_password1');
  const pass2Input = document.getElementById('id_new_password2');

  createPasswordStrengthUI(pass1Input);
  setNewPasswordFieldsState(oldPasswordInput, pass1Input, pass2Input);

  oldPasswordInput?.addEventListener('input', function () {
    setNewPasswordFieldsState(oldPasswordInput, pass1Input, pass2Input);
  });

  form.addEventListener('submit', function (e) {
    const oldPassword = oldPasswordInput?.value || '';
    const password1 = pass1Input?.value || '';
    const password2 = pass2Input?.value || '';
    let hasErrors = false;

    document.querySelectorAll('.field-error-inline').forEach(el => el.remove());
    [oldPasswordInput, pass1Input, pass2Input].forEach(input => input?.classList.remove('is-invalid'));

    if (!oldPassword) {
      showFieldErrorInline(oldPasswordInput, 'La contraseña actual es obligatoria');
      hasErrors = true;
    }

    if (!password1) {
      showFieldErrorInline(pass1Input, 'La nueva contraseña es obligatoria');
      hasErrors = true;
    }

    if (!password2) {
      showFieldErrorInline(pass2Input, 'Debes confirmar la nueva contraseña');
      hasErrors = true;
    }

    if (!hasErrors) {
      const passwordResult = checkPasswordStrength(password1);
      if (passwordResult.metCount < 5) {
        const missingReqs = [];
        if (!passwordResult.requirements.length) missingReqs.push('mínimo 8 caracteres');
        if (!passwordResult.requirements.uppercase) missingReqs.push('una mayúscula');
        if (!passwordResult.requirements.lowercase) missingReqs.push('una minúscula');
        if (!passwordResult.requirements.number) missingReqs.push('un número');
        if (!passwordResult.requirements.special) missingReqs.push('un carácter especial');

        showFieldErrorInline(pass1Input, 'Falta: ' + missingReqs.join(', '));
        hasErrors = true;
      }

      if (password1 !== password2) {
        showFieldErrorInline(pass2Input, 'Las contraseñas no coinciden');
        hasErrors = true;
      }
    }

    if (hasErrors) {
      e.preventDefault();
    }
  });
}

document.addEventListener('DOMContentLoaded', function () {
  const errorTexts = document.querySelectorAll('.error-text');
  errorTexts.forEach(function (errorText) {
    const inputGroup = errorText.closest('.mb-3');
    if (inputGroup) {
      const input = inputGroup.querySelector('.form-control, input');
      if (input) {
        input.classList.add('is-invalid');
      }
    }
  });

  setupChangePasswordValidation();
});
