from django import forms
from .models import RegistroVisitante
import re


class RegistroVisitanteForm(forms.Form):
    correo = forms.EmailField(
        label="Correo electronico",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "correo@ejemplo.com"}
        ),
    )
    documento = forms.CharField(
        label="Documento",
        max_length=20,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Numero de documento"}
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
        initial='interno',
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


class EditarPerfilForm(forms.ModelForm):
    """Formulario para que el visitante edite su información personal"""
    
    password_actual = forms.CharField(
        label="Contraseña Actual",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingrese su contraseña actual",
            }
        ),
        help_text="Solo requerida si desea cambiar su contraseña",
    )
    
    nueva_password = forms.CharField(
        label="Nueva Contraseña",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Nueva contraseña (opcional)",
            }
        ),
        help_text="Dejar en blanco si no desea cambiar la contraseña",
    )
    
    confirmar_password = forms.CharField(
        label="Confirmar Nueva Contraseña",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Confirme su nueva contraseña",
            }
        ),
    )
    
    class Meta:
        model = RegistroVisitante
        fields = ['nombre', 'apellido', 'tipo_documento', 'telefono', 'correo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre'
            }),
            'apellido': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellido'
            }),
            'tipo_documento': forms.Select(attrs={
                'class': 'form-select'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono'
            }),
            'correo': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.visitante = kwargs.pop('visitante', None)
        super().__init__(*args, **kwargs)
    
    def clean_correo(self):
        correo = self.cleaned_data.get('correo', '').strip()
        if RegistroVisitante.objects.filter(correo__iexact=correo).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este correo ya está registrado por otro usuario.")
        return correo
    
    def clean(self):
        cleaned_data = super().clean()
        password_actual = cleaned_data.get('password_actual')
        nueva_password = cleaned_data.get('nueva_password')
        confirmar_password = cleaned_data.get('confirmar_password')
        
        # Si quiere cambiar contraseña
        if nueva_password or confirmar_password:
            # Verificar contraseña actual
            if not password_actual:
                raise forms.ValidationError("Debe ingresar su contraseña actual para cambiarla.")
            
            if self.visitante and not self.visitante.check_password(password_actual):
                raise forms.ValidationError("La contraseña actual es incorrecta.")
            
            # Validar que coincidan
            if nueva_password != confirmar_password:
                raise forms.ValidationError("Las contraseñas nuevas no coinciden.")
            
            # Validar seguridad de la contraseña
            if len(nueva_password) < 8:
                raise forms.ValidationError("La nueva contraseña debe tener al menos 8 caracteres.")
        
        return cleaned_data
