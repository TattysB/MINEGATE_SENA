
window.showAlert = function(message, type) {
    let overlay = document.getElementById('alertOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'alertOverlay';
        overlay.className = 'alert-overlay';
        document.body.appendChild(overlay);
    }

    let modal = document.getElementById('alertModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'alertModal';
        modal.className = 'alert-modal';
        document.body.appendChild(modal);
    }

    modal.className = 'alert-modal alert-' + (type || 'info');

    const iconMap = {
        success: { icon: 'circle-check', color: '#10b981' },
        error: { icon: 'circle-exclamation', color: '#ef4444' },
        info: { icon: 'circle-info', color: '#3b82f6' },
        warning: { icon: 'triangle-exclamation', color: '#f59e0b' }
    };
    const config = iconMap[type] || iconMap.info;

    modal.innerHTML = `
        <div class="alert-modal-icon" style="color: ${config.color}">
            <i class="fa-solid fa-${config.icon}"></i>
        </div>
        <div class="alert-modal-message">${message}</div>
        <button type="button" class="alert-modal-btn" id="alertCloseBtn">
            <i class="fa-solid fa-check"></i> Entendido
        </button>
    `;

    overlay.classList.add('active');
    modal.classList.add('active');
    document.body.classList.add('alert-open');

    function closeModal() {
        modal.classList.remove('active');
        overlay.classList.remove('active');
        document.body.classList.remove('alert-open');
    }

    document.getElementById('alertCloseBtn').addEventListener('click', closeModal);
    overlay.addEventListener('click', closeModal);
    document.addEventListener('keydown', function onEsc(e) {
        if (e.key === 'Escape') {
            closeModal();
            document.removeEventListener('keydown', onEsc);
        }
    });
};

function showFieldError(input, message) {
    const container = input.closest('.form-group') || input.closest('.password-field') || input.parentElement;
    const existingError = container.querySelector('.field-error');
    if (existingError) existingError.remove();
    const errorSpan = document.createElement('span');
    errorSpan.className = 'field-error';
    errorSpan.textContent = message;
    container.appendChild(errorSpan);
    input.classList.add('input-error');
}

function clearFieldError(input) {
    const container = input.closest('.form-group') || input.closest('.password-field') || input.parentElement;
    const existingError = container.querySelector('.field-error');
    if (existingError) existingError.remove();
    input.classList.remove('input-error');
}


function setupNumericOnlyField(input) {
    if (!input) return;
    
    input.addEventListener('input', function(e) {
        this.value = this.value.replace(/[^0-9]/g, '');
    });
    
    input.addEventListener('keypress', function(e) {
        if (!/[0-9]/.test(e.key) && e.key !== 'Backspace' && e.key !== 'Delete' && e.key !== 'Tab') {
            e.preventDefault();
        }
    });
    
    input.addEventListener('paste', function(e) {
        e.preventDefault();
        const pastedText = (e.clipboardData || window.clipboardData).getData('text');
        const numericOnly = pastedText.replace(/[^0-9]/g, '');
        document.execCommand('insertText', false, numericOnly);
    });
}

function setupLettersOnlyField(input) {
    if (!input) return;
    
    input.addEventListener('input', function(e) {
        let value = this.value.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]/g, '');
        value = value.replace(/\s+/g, ' ');
        this.value = value;
    });
    
    input.addEventListener('keypress', function(e) {
        const char = e.key;
        if (!/^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]$/.test(char) && char !== 'Backspace' && char !== 'Delete' && char !== 'Tab') {
            e.preventDefault();
        }
    });
    
    input.addEventListener('blur', function() {
        if (this.value.trim()) {
            this.value = this.value.trim().split(' ')
                .filter(word => word.length > 0)
                .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
                .join(' ');
        }
    });
    
    input.addEventListener('paste', function(e) {
        e.preventDefault();
        const pastedText = (e.clipboardData || window.clipboardData).getData('text');
        const lettersOnly = pastedText.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]/g, '').replace(/\s+/g, ' ');
        document.execCommand('insertText', false, lettersOnly);
    });
}


function checkPasswordStrength(password) {
    const requirements = {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        number: /\d/.test(password),
        special: /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;'`~]/.test(password)
    };
    
    const metCount = Object.values(requirements).filter(Boolean).length;
    
    let strength = 'none';
    let strengthText = '';
    let strengthClass = '';
    
    if (password.length === 0) {
        strength = 'none';
        strengthText = '';
        strengthClass = '';
    } else if (metCount <= 2) {
        strength = 'weak';
        strengthText = 'Muy débil';
        strengthClass = 'strength-weak';
    } else if (metCount === 3) {
        strength = 'medium';
        strengthText = 'Media';
        strengthClass = 'strength-medium';
    } else if (metCount === 4) {
        strength = 'good';
        strengthText = 'Buena';
        strengthClass = 'strength-good';
    } else if (metCount === 5) {
        strength = 'strong';
        strengthText = 'Segura';
        strengthClass = 'strength-strong';
    }
    
    return {
        requirements,
        metCount,
        strength,
        strengthText,
        strengthClass
    };
}

function createPasswordStrengthUI(passwordInput) {
    if (!passwordInput) return;
    
    const formGroup = passwordInput.closest('.form-group');
    if (!formGroup) return;
    
    if (formGroup.querySelector('.password-strength-container')) return;
    
    const strengthContainer = document.createElement('div');
    strengthContainer.className = 'password-strength-container';
    strengthContainer.innerHTML = `
        <div class="strength-bar-wrapper">
            <div class="strength-bar">
                <div class="strength-bar-fill"></div>
            </div>
            <span class="strength-text"></span>
        </div>
        <div class="password-requirements">
            <div class="requirement unmet" data-req="length">
                <i class="fa-solid fa-circle-xmark req-icon" style="color: #ef4444;"></i>
                <span style="color: #ef4444;">Mínimo 8 caracteres</span>
            </div>
            <div class="requirement unmet" data-req="uppercase">
                <i class="fa-solid fa-circle-xmark req-icon" style="color: #ef4444;"></i>
                <span style="color: #ef4444;">Una letra mayúscula</span>
            </div>
            <div class="requirement unmet" data-req="lowercase">
                <i class="fa-solid fa-circle-xmark req-icon" style="color: #ef4444;"></i>
                <span style="color: #ef4444;">Una letra minúscula</span>
            </div>
            <div class="requirement unmet" data-req="number">
                <i class="fa-solid fa-circle-xmark req-icon" style="color: #ef4444;"></i>
                <span style="color: #ef4444;">Un número</span>
            </div>
            <div class="requirement unmet" data-req="special">
                <i class="fa-solid fa-circle-xmark req-icon" style="color: #ef4444;"></i>
                <span style="color: #ef4444;">Un carácter especial (!@#$%...)</span>
            </div>
        </div>
    `;
    
    const passwordField = formGroup.querySelector('.password-field');
    if (passwordField) {
        passwordField.after(strengthContainer);
    } else {
        formGroup.appendChild(strengthContainer);
    }
    
    passwordInput.addEventListener('input', function() {
        updatePasswordStrengthUI(this.value, strengthContainer);
    });
    
    passwordInput.addEventListener('focus', function() {
        strengthContainer.classList.add('visible');
    });
    
    passwordInput.addEventListener('blur', function() {
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
    
    const widthPercent = (result.metCount / 5) * 100;
    barFill.style.width = widthPercent + '%';
    
    strengthText.textContent = result.strengthText;
    strengthText.className = 'strength-text ' + result.strengthClass;
    
    requirements.forEach(req => {
        const reqName = req.dataset.req;
        const icon = req.querySelector('.req-icon');
        const textSpan = req.querySelector('span');
        
        if (result.requirements[reqName]) {
            req.classList.add('met');
            req.classList.remove('unmet');
            icon.className = 'fa-solid fa-circle-check req-icon';
            icon.style.color = '#10b981';
            if (textSpan) textSpan.style.color = '#10b981';
        } else {
            req.classList.remove('met');
            req.classList.add('unmet');
            icon.className = 'fa-solid fa-circle-xmark req-icon';
            icon.style.color = '#ef4444';
            if (textSpan) textSpan.style.color = '#ef4444';
        }
    });
    
    if (password.length > 0) {
        container.classList.add('visible');
    }
}

function setupValidationMessages() {
    const inputs = document.querySelectorAll('input[required], input[type="email"]');
    inputs.forEach(input => {
        input.addEventListener('invalid', function(e) {
            e.preventDefault();
            if (this.validity.valueMissing) {
                showFieldError(this, 'Este campo es obligatorio');
            } else if (this.validity.typeMismatch && this.type === 'email') {
                showFieldError(this, 'Por favor ingresa un correo electrónico válido');
            }
        });

        input.addEventListener('input', function() {
            this.setCustomValidity('');
            clearFieldError(this);
        });
    });
}

function setupPasswordToggle() {
    const toggleButtons = document.querySelectorAll('.toggle-password');
    
    toggleButtons.forEach(button => {
        button.type = 'button';
        
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const targetId = this.getAttribute('data-target');
            const passwordInput = document.getElementById(targetId);
            const icon = this.querySelector('i');

            if (passwordInput) {
                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';
                    if (icon) {
                        icon.classList.remove('fa-eye');
                        icon.classList.add('fa-eye-slash');
                    }
                    this.classList.add('active');
                } else {
                    passwordInput.type = 'password';
                    if (icon) {
                        icon.classList.remove('fa-eye-slash');
                        icon.classList.add('fa-eye');
                    }
                    this.classList.remove('active');
                }
            }
        });
    });
}

function setupLoginValidation() {
    const loginForm = document.getElementById('loginForm');
    if (!loginForm) return;
    
    loginForm.addEventListener('submit', function(e) {
        const userInput = document.querySelector('#loginForm input[name="username"]');
        const passInput = document.querySelector('#loginForm input[name="password"]');
        const username = userInput?.value?.trim() || '';
        const password = passInput?.value || '';
        let hasErrors = false;

        clearFieldError(userInput);
        clearFieldError(passInput);

        if (!username) {
            showFieldError(userInput, 'Este campo es obligatorio');
            hasErrors = true;
        }
        if (!password) {
            showFieldError(passInput, 'Este campo es obligatorio');
            hasErrors = true;
        }

        if (hasErrors) {
            e.preventDefault();
            return false;
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    setupValidationMessages();
    setupPasswordToggle();
    setupLoginValidation();
});
