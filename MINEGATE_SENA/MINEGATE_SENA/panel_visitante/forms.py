from django import forms
from .models import RegistroVisitante
import re


class RegistroVisitanteForm(forms.Form):
    nombre = forms.CharField(
        label="Nombre",
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Nombre"}
        ),
    )
    apellido = forms.CharField(
        label="Apellido",
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Apellido"}
        ),
    )
    tipo_documento = forms.ChoiceField(
        label="Tipo de Documento",
        choices=RegistroVisitante.TIPOS_DOCUMENTO,
        widget=forms.Select(
            attrs={"class": "form-control"}
        ),
        initial='CC',
    )
    documento = forms.CharField(
        label="Numero de Documento",
        max_length=20,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Numero de documento"}
        ),
    )
    telefono = forms.CharField(
        label="Telefono",
        max_length=10,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Telefono"}
        ),
    )
    correo = forms.EmailField(
        label="Correo electronico",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "correo@ejemplo.com"}
        ),
    )
    rol = forms.ChoiceField(
        label="Tipo de Usuario",
        choices=[
            ('interno', '👥 Usuario Interno (SENA)'),
            ('externo', '🏢 Usuario Externo'),
        ],
        widget=forms.RadioSelect(
            attrs={"class": "form-check-input"}
        ),
        required=True,
        error_messages={
            'required': 'Debe seleccionar un tipo de usuario.',
        },
    )
    password1 = forms.CharField(
        label="Contrasena",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Contrasena"}
        ),
    )
    password2 = forms.CharField(
        label="Confirmar contrasena",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Confirmar contrasena"}
        ),
    )

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()
        if not nombre:
            raise forms.ValidationError("El nombre es obligatorio.")
        # Permitir solo letras y espacios
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$", nombre):
            raise forms.ValidationError("El nombre solo debe contener letras.")
        return " ".join(word.capitalize() for word in nombre.split())

    def clean_apellido(self):
        apellido = self.cleaned_data.get("apellido", "").strip()
        if not apellido:
            raise forms.ValidationError("El apellido es obligatorio.")
        # Permitir solo letras y espacios
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$", apellido):
            raise forms.ValidationError("El apellido solo debe contener letras.")
        return " ".join(word.capitalize() for word in apellido.split())

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono", "").strip()
        if not telefono:
            raise forms.ValidationError("El telefono es obligatorio.")
        if not re.match(r"^\d{10}$", telefono):
            raise forms.ValidationError("El telefono debe tener exactamente 10 numeros.")
        return telefono

    def clean_documento(self):
        documento = self.cleaned_data.get("documento", "").strip()
        if not documento:
            raise forms.ValidationError("El numero de documento es obligatorio.")
        if not documento.isdigit():
            raise forms.ValidationError("El documento solo debe contener numeros.")
        if RegistroVisitante.objects.filter(documento=documento).exists():
            raise forms.ValidationError("Este documento ya esta registrado.")
        return documento

    def clean_correo(self):
        correo = self.cleaned_data.get("correo", "").strip()
        if RegistroVisitante.objects.filter(correo__iexact=correo).exists():
            raise forms.ValidationError("Este correo ya esta registrado.")
        return correo

    def clean_password1(self):
        password = self.cleaned_data.get("password1")
        
        if not password:
            raise forms.ValidationError("La contraseña es obligatoria.")
        
        errors = []
        
        # Longitud mínima de 8 caracteres
        if len(password) < 8:
            errors.append("Debe tener al menos 8 caracteres.")
        
        # Al menos una letra mayúscula
        if not re.search(r'[A-Z]', password):
            errors.append("Debe contener al menos una letra mayúscula.")
        
        # Al menos una letra minúscula
        if not re.search(r'[a-z]', password):
            errors.append("Debe contener al menos una letra minúscula.")
        
        # Al menos un número
        if not re.search(r'\d', password):
            errors.append("Debe contener al menos un número.")
        
        # Al menos un carácter especial
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]', password):
            errors.append("Debe contener al menos un carácter especial (!@#$%^&*...).")
        
        if errors:
            raise forms.ValidationError(errors)
        
        return password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("Las contrasenias no coinciden.")

        return cleaned_data


class PasswordResetRequestForm(forms.Form):
    """Formulario para solicitar recuperación de contraseña"""
    email = forms.EmailField(
        label="Correo Electrónico",
        max_length=254,
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingrese su correo electrónico",
                "autofocus": True,
            }
        ),
        help_text="Ingrese el correo asociado a su cuenta",
    )


class PasswordResetConfirmForm(forms.Form):
    """Formulario para restablecer contraseña"""
    password1 = forms.CharField(
        label="Nueva Contraseña",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingrese su nueva contraseña",
                "autocomplete": "new-password",
            }
        ),
        help_text="Mínimo 8 caracteres. No puede ser completamente numérica.",
    )

    password2 = forms.CharField(
        label="Confirmar Contraseña",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Confirme su nueva contraseña",
                "autocomplete": "new-password",
            }
        ),
    )

    def clean_password1(self):
        """Valida que la contraseña cumpla con estándares de seguridad"""
        password = self.cleaned_data.get("password1")
        if not password:
            raise forms.ValidationError("La contraseña es obligatoria.")

        errors = []

        # Mínimo 8 caracteres
        if len(password) < 8:
            errors.append("La contraseña debe tener al menos 8 caracteres.")

        # Al menos una letra mayúscula
        if not re.search(r"[A-Z]", password):
            errors.append("Debe contener al menos una letra mayúscula.")

        # Al menos una letra minúscula
        if not re.search(r"[a-z]", password):
            errors.append("Debe contener al menos una letra minúscula.")

        # Al menos un número
        if not re.search(r"\d", password):
            errors.append("Debe contener al menos un número.")

        # Al menos un carácter especial
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]', password):
            errors.append("Debe contener al menos un carácter especial (!@#$%^&*...).")

        if errors:
            raise forms.ValidationError(errors)

        return password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("Las contraseñas no coinciden.")

        return cleaned_data


class ActualizarPerfilForm(forms.Form):
    """Formulario para actualizar datos del perfil del usuario"""
    nombre = forms.CharField(
        label="Nombre",
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Nombre"}
        ),
    )
    apellido = forms.CharField(
        label="Apellido",
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Apellido"}
        ),
    )
    tipo_documento = forms.ChoiceField(
        label="Tipo de Documento",
        choices=RegistroVisitante.TIPOS_DOCUMENTO,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    telefono = forms.CharField(
        label="Teléfono",
        max_length=10,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Teléfono"}
        ),
    )
    correo = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "correo@ejemplo.com"}
        ),
    )

    def __init__(self, *args, current_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_user = current_user

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()
        if not nombre:
            raise forms.ValidationError("El nombre es obligatorio.")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$", nombre):
            raise forms.ValidationError("El nombre solo debe contener letras.")
        return " ".join(word.capitalize() for word in nombre.split())

    def clean_apellido(self):
        apellido = self.cleaned_data.get("apellido", "").strip()
        if not apellido:
            raise forms.ValidationError("El apellido es obligatorio.")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$", apellido):
            raise forms.ValidationError("El apellido solo debe contener letras.")
        return " ".join(word.capitalize() for word in apellido.split())

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono", "").strip()
        if not telefono:
            raise forms.ValidationError("El teléfono es obligatorio.")
        if not re.match(r"^\d{10}$", telefono):
            raise forms.ValidationError("El teléfono debe tener exactamente 10 números.")
        return telefono

    def clean_correo(self):
        correo = self.cleaned_data.get("correo", "").strip()
        if RegistroVisitante.objects.filter(correo__iexact=correo).exclude(id=self.current_user.id if self.current_user else None).exists():
            raise forms.ValidationError("Este correo ya está registrado por otro usuario.")
        return correo


class CambiarContrasenaForm(forms.Form):
    """Formulario para cambiar la contraseña"""
    contrasena_actual = forms.CharField(
        label="Contraseña Actual",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Contraseña actual"}
        ),
    )
    nueva_contrasena = forms.CharField(
        label="Nueva Contraseña",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Nueva contraseña"}
        ),
    )
    confirmar_contrasena = forms.CharField(
        label="Confirmar Nueva Contraseña",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Confirmar contraseña"}
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        nueva = cleaned_data.get("nueva_contrasena")
        confirmar = cleaned_data.get("confirmar_contrasena")

        if nueva and confirmar:
            if nueva != confirmar:
                raise forms.ValidationError("Las contraseñas no coinciden.")
            
            # Validación de la nueva contraseña
            errors = []
            if len(nueva) < 8:
                errors.append("La contraseña debe tener al menos 8 caracteres.")
            if not re.search(r"[A-Z]", nueva):
                errors.append("Debe contener al menos una letra mayúscula.")
            if not re.search(r"[a-z]", nueva):
                errors.append("Debe contener al menos una letra minúscula.")
            if not re.search(r"\d", nueva):
                errors.append("Debe contener al menos un número.")
                
            if errors:
                raise forms.ValidationError(errors)

        return cleaned_data
