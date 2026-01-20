// ===== FUNCIONES DE AUTENTICACIÓN (LOGIN Y REGISTRO) =====

// Función para mostrar alertas (modal centrado con overlay)
window.showAlert = function(message, type) {
    // Crear overlay si no existe
    let overlay = document.getElementById('alertOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'alertOverlay';
        overlay.className = 'alert-overlay';
        document.body.appendChild(overlay);
    }

    // Crear modal si no existe
    let modal = document.getElementById('alertModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'alertModal';
        modal.className = 'alert-modal';
        document.body.appendChild(modal);
    }

    // Limpiar clases de tipo anteriores y agregar la nueva
    modal.className = 'alert-modal alert-' + (type || 'info');

    // Definir icono y color según tipo
    const iconMap = {
        success: { icon: 'circle-check', color: '#10b981' },
        error: { icon: 'circle-exclamation', color: '#ef4444' },
        info: { icon: 'circle-info', color: '#3b82f6' },
        warning: { icon: 'triangle-exclamation', color: '#f59e0b' }
    };
    const config = iconMap[type] || iconMap.info;

    // Contenido del modal
    modal.innerHTML = `
        <div class="alert-modal-icon" style="color: ${config.color}">
            <i class="fa-solid fa-${config.icon}"></i>
        </div>
        <div class="alert-modal-message">${message}</div>
        <button type="button" class="alert-modal-btn" id="alertCloseBtn">
            <i class="fa-solid fa-check"></i> Entendido
        </button>
    `;

    // Mostrar overlay y modal
    overlay.classList.add('active');
    modal.classList.add('active');
    document.body.classList.add('alert-open');

    // Función para cerrar
    function closeModal() {
        modal.classList.remove('active');
        overlay.classList.remove('active');
        document.body.classList.remove('alert-open');
    }

    // Eventos de cierre
    document.getElementById('alertCloseBtn').addEventListener('click', closeModal);
    overlay.addEventListener('click', closeModal);
    document.addEventListener('keydown', function onEsc(e) {
        if (e.key === 'Escape') {
            closeModal();
            document.removeEventListener('keydown', onEsc);
        }
    });
};

// Función auxiliar para mostrar error inline en un campo
function showFieldError(input, message) {
    const container = input.closest('.form-group') || input.closest('.password-field') || input.parentElement;
    // Eliminar error previo del mismo campo
    const existingError = container.querySelector('.field-error');
    if (existingError) existingError.remove();
    // Crear y añadir mensaje de error
    const errorSpan = document.createElement('span');
    errorSpan.className = 'field-error';
    errorSpan.textContent = message;
    container.appendChild(errorSpan);
    input.classList.add('input-error');
}

// Función auxiliar para limpiar error inline de un campo
function clearFieldError(input) {
    const container = input.closest('.form-group') || input.closest('.password-field') || input.parentElement;
    const existingError = container.querySelector('.field-error');
    if (existingError) existingError.remove();
    input.classList.remove('input-error');
}

// ===== VALIDACIÓN EN TIEMPO REAL =====

// Función para validar que solo se ingresen números
function setupNumericOnlyField(input) {
    if (!input) return;
    
    input.addEventListener('input', function(e) {
        // Eliminar cualquier carácter que no sea número
        this.value = this.value.replace(/[^0-9]/g, '');
    });
    
    input.addEventListener('keypress', function(e) {
        // Prevenir ingreso de caracteres no numéricos
        if (!/[0-9]/.test(e.key) && e.key !== 'Backspace' && e.key !== 'Delete' && e.key !== 'Tab') {
            e.preventDefault();
        }
    });
    
    // Prevenir pegado de texto no numérico
    input.addEventListener('paste', function(e) {
        e.preventDefault();
        const pastedText = (e.clipboardData || window.clipboardData).getData('text');
        const numericOnly = pastedText.replace(/[^0-9]/g, '');
        document.execCommand('insertText', false, numericOnly);
    });
}

// Función para validar que solo se ingresen letras y convertir a formato título
function setupLettersOnlyField(input) {
    if (!input) return;
    
    input.addEventListener('input', function(e) {
        // Eliminar cualquier carácter que no sea letra o espacio
        let value = this.value.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]/g, '');
        // Evitar espacios múltiples
        value = value.replace(/\s+/g, ' ');
        this.value = value;
    });
    
    input.addEventListener('keypress', function(e) {
        // Prevenir ingreso de caracteres no alfabéticos (excepto espacio)
        const char = e.key;
        if (!/^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]$/.test(char) && char !== 'Backspace' && char !== 'Delete' && char !== 'Tab') {
            e.preventDefault();
        }
    });
    
    // Convertir a formato título al perder el foco
    input.addEventListener('blur', function() {
        if (this.value.trim()) {
            this.value = this.value.trim().split(' ')
                .filter(word => word.length > 0)
                .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
                .join(' ');
        }
    });
    
    // Prevenir pegado de texto con caracteres no válidos
    input.addEventListener('paste', function(e) {
        e.preventDefault();
        const pastedText = (e.clipboardData || window.clipboardData).getData('text');
        const lettersOnly = pastedText.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]/g, '').replace(/\s+/g, ' ');
        document.execCommand('insertText', false, lettersOnly);
    });
}

// ===== VALIDACIÓN DE FORTALEZA DE CONTRASEÑA =====

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
    
    // Verificar si ya existe la UI
    if (formGroup.querySelector('.password-strength-container')) return;
    
    // Crear contenedor de fortaleza
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
    
    // Insertar después del password-field
    const passwordField = formGroup.querySelector('.password-field');
    if (passwordField) {
        passwordField.after(strengthContainer);
    } else {
        formGroup.appendChild(strengthContainer);
    }
    
    // Configurar evento de input
    passwordInput.addEventListener('input', function() {
        updatePasswordStrengthUI(this.value, strengthContainer);
    });
    
    // Mostrar requisitos al enfocar
    passwordInput.addEventListener('focus', function() {
        strengthContainer.classList.add('visible');
    });
    
    // Ocultar requisitos al desenfocar (si la contraseña está vacía)
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
    
    // Actualizar barra de fortaleza
    barFill.className = 'strength-bar-fill';
    if (result.strengthClass) {
        barFill.classList.add(result.strengthClass);
    }
    
    // Calcular ancho de la barra
    const widthPercent = (result.metCount / 5) * 100;
    barFill.style.width = widthPercent + '%';
    
    // Actualizar texto
    strengthText.textContent = result.strengthText;
    strengthText.className = 'strength-text ' + result.strengthClass;
    
    // Actualizar requisitos
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
    
    // Mostrar contenedor si hay texto
    if (password.length > 0) {
        container.classList.add('visible');
    }
}

// Configurar validación de campos (errores inline, sin alertas flotantes)
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

// Funcionalidad para mostrar/ocultar contraseñas
function setupPasswordToggle() {
    const toggleButtons = document.querySelectorAll('.toggle-password');
    
    toggleButtons.forEach(button => {
        // Asegurar que el botón sea de tipo button
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

// Validación de login
function setupLoginValidation() {
    const loginForm = document.getElementById('loginForm');
    if (!loginForm) return;
    
    loginForm.addEventListener('submit', function(e) {
        const userInput = document.querySelector('#loginForm input[name="username"]');
        const passInput = document.querySelector('#loginForm input[name="password"]');
        const username = userInput?.value?.trim() || '';
        const password = passInput?.value || '';
        let hasErrors = false;

        // Limpiar errores previos
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

// Validación de registro
function setupRegistroValidation() {
    const registroForm = document.getElementById('registroForm');
    if (!registroForm) return;
    
    // Configurar validación de campos específicos
    const docInput = document.querySelector('#registroForm input[name="documento"]');
    const firstNameInput = document.querySelector('#registroForm input[name="first_name"]');
    const lastNameInput = document.querySelector('#registroForm input[name="last_name"]');
    const pass1Input = document.querySelector('#registroForm input[name="password1"]');
    
    // Aplicar validación solo números para documento
    setupNumericOnlyField(docInput);
    
    // Aplicar validación solo letras y formato título para nombre y apellido
    setupLettersOnlyField(firstNameInput);
    setupLettersOnlyField(lastNameInput);
    
    // Crear UI de fortaleza de contraseña
    createPasswordStrengthUI(pass1Input);
    
    registroForm.addEventListener('submit', function(e) {
        const fields = [
            { name: 'documento', label: 'Número de documento' },
            { name: 'email', label: 'Correo electrónico' },
            { name: 'first_name', label: 'Nombre' },
            { name: 'last_name', label: 'Apellido' },
            { name: 'password1', label: 'Contraseña' },
            { name: 'password2', label: 'Confirmar contraseña' }
        ];
        
        let hasErrors = false;

        // Limpiar errores previos
        fields.forEach(f => {
            const input = document.querySelector(`#registroForm input[name="${f.name}"]`);
            if (input) clearFieldError(input);
        });

        // Validar campos vacíos
        fields.forEach(f => {
            const input = document.querySelector(`#registroForm input[name="${f.name}"]`);
            const value = input?.value?.trim() || '';
            if (!value) {
                showFieldError(input, 'Este campo es obligatorio');
                hasErrors = true;
            }
        });

        if (hasErrors) {
            e.preventDefault();
            return false;
        }

        // Validaciones específicas
        const emailInput = document.querySelector('#registroForm input[name="email"]');
        const pass2Input = document.querySelector('#registroForm input[name="password2"]');

        const documento = docInput?.value?.trim() || '';
        const firstName = firstNameInput?.value?.trim() || '';
        const lastName = lastNameInput?.value?.trim() || '';
        const email = emailInput?.value?.trim() || '';
        const password1 = pass1Input?.value || '';
        const password2 = pass2Input?.value || '';

        // Validar documento (solo números)
        if (!/^\d+$/.test(documento)) {
            showFieldError(docInput, 'Solo debe contener números');
            hasErrors = true;
        }
        
        // Validar nombre (solo letras)
        if (!/^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$/.test(firstName)) {
            showFieldError(firstNameInput, 'Solo debe contener letras');
            hasErrors = true;
        }
        
        // Validar apellido (solo letras)
        if (!/^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$/.test(lastName)) {
            showFieldError(lastNameInput, 'Solo debe contener letras');
            hasErrors = true;
        }

        // Validar email
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            showFieldError(emailInput, 'Correo electrónico no válido');
            hasErrors = true;
        }

        // Validar contraseña con estándares de seguridad
        const passwordResult = checkPasswordStrength(password1);
        if (passwordResult.metCount < 5) {
            let missingReqs = [];
            if (!passwordResult.requirements.length) missingReqs.push('mínimo 8 caracteres');
            if (!passwordResult.requirements.uppercase) missingReqs.push('una mayúscula');
            if (!passwordResult.requirements.lowercase) missingReqs.push('una minúscula');
            if (!passwordResult.requirements.number) missingReqs.push('un número');
            if (!passwordResult.requirements.special) missingReqs.push('un carácter especial');
            showFieldError(pass1Input, 'Falta: ' + missingReqs.join(', '));
            hasErrors = true;
        }

        // Validar que las contraseñas coincidan
        if (password1 !== password2) {
            showFieldError(pass2Input, 'Las contraseñas no coinciden');
            hasErrors = true;
        }

        if (hasErrors) {
            e.preventDefault();
            return false;
        }

        return true;
    });
}

// Inicializar todo cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    setupValidationMessages();
    setupPasswordToggle();
    setupLoginValidation();
    setupRegistroValidation();
});
