from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox
import re
from .models import PerfilUsuario


class LoginForm(AuthenticationForm):
    """
    Formulario personalizado para inicio de sesión
    Usamos el campo username para almacenar el documento
    """

    username = forms.CharField(
        label="Documento",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingrese su documento",
                "autofocus": True,
            }
        ),
        error_messages={
            "required": "Ingresa tu número de documento.",
        },
    )

    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Ingrese su contraseña"}
        ),
        error_messages={
            "required": "Ingresa tu contraseña.",
        },
    )

    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Recordarme",
    )

    captcha = ReCaptchaField(
        widget=ReCaptchaV2Checkbox,
        error_messages={"required": "Debe completar el captcha."},
    )

    def clean(self):
        """
        Sobreescribimos clean() para NO hacer la autenticación aquí.
        La autenticación y mensajes específicos se manejan en la vista.
        Solo validamos que los campos no estén vacíos.
        """
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username and password:
            pass

        return self.cleaned_data


class RegistroForm(UserCreationForm):
    """
    Formulario para registro de nuevos usuarios
    Extiende UserCreationForm de Django
    """

    documento = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Número de documento",
                "inputmode": "numeric",
                "maxlength": "10",
            }
        ),
        error_messages={
            "required": "El número de documento es obligatorio.",
            "max_length": "El documento no puede tener más de 10 caracteres.",
        },
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "correo@ejemplo.com"}
        ),
        error_messages={
            "required": "El correo electrónico es obligatorio.",
            "invalid": "Por favor ingresa un correo electrónico válido.",
        },
    )

    first_name = forms.CharField(
        max_length=150,
        required=True,
        label="Nombre",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Nombre"}
        ),
        error_messages={
            "required": "El nombre es obligatorio.",
            "max_length": "El nombre es demasiado largo.",
        },
    )

    last_name = forms.CharField(
        max_length=150,
        required=True,
        label="Apellido",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Apellido"}
        ),
        error_messages={
            "required": "El apellido es obligatorio.",
            "max_length": "El apellido es demasiado largo.",
        },
    )

    def clean_first_name(self):
        """Valida y formatea el nombre (solo letras, formato título)"""
        first_name = self.cleaned_data.get("first_name", "").strip()
        if not first_name:
            raise forms.ValidationError("El nombre es obligatorio.")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$", first_name):
            raise forms.ValidationError("El nombre solo debe contener letras.")
        return " ".join(word.capitalize() for word in first_name.split())

    def clean_last_name(self):
        """Valida y formatea el apellido (solo letras, formato título)"""
        last_name = self.cleaned_data.get("last_name", "").strip()
        if not last_name:
            raise forms.ValidationError("El apellido es obligatorio.")
        if not re.match(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$", last_name):
            raise forms.ValidationError("El apellido solo debe contener letras.")
        return " ".join(word.capitalize() for word in last_name.split())

    telefono = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Teléfono (opcional)",
                "inputmode": "numeric",
                "maxlength": "10",
            }
        ),
    )

    captcha = ReCaptchaField(
        widget=ReCaptchaV2Checkbox,
        error_messages={"required": "Debe completar el captcha."},
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
        ]
        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control d-none"}
            ),  # Oculto, usamos documento
            "password1": forms.PasswordInput(
                attrs={"class": "form-control", "placeholder": "Contraseña"}
            ),
            "password2": forms.PasswordInput(
                attrs={"class": "form-control", "placeholder": "Confirmar contraseña"}
            ),
        }
        error_messages = {
            "username": {
                "required": "El nombre de usuario es obligatorio.",
                "unique": "Este documento ya está registrado.",
            },
            "email": {
                "required": "El correo electrónico es obligatorio.",
                "invalid": "Por favor ingresa un correo electrónico válido.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].error_messages = {
            "required": "La contraseña es obligatoria.",
        }
        self.fields["password2"].error_messages = {
            "required": "Debes confirmar la contraseña.",
        }
        self.fields["password1"].help_text = (
            "La contraseña debe tener al menos 8 caracteres y no puede ser completamente numérica."
        )
        self.fields["password2"].help_text = (
            "Ingresa la misma contraseña para verificación."
        )

        self.fields["username"].required = False

    def clean(self):
        """Valida los datos del formulario y asigna documento como username"""
        cleaned_data = super().clean()
        documento = cleaned_data.get("documento")

        if documento:
            cleaned_data["username"] = documento

        return cleaned_data

    def clean_documento(self):
        """Valida que el documento no exista en la base de datos"""
        documento = (self.cleaned_data.get("documento") or "").strip()
        if not documento:
            raise forms.ValidationError("El número de documento es obligatorio.")
        if len(documento) < 5:
            raise forms.ValidationError(
                "El documento debe tener al menos 5 dígitos."
            )
        if len(documento) > 10:
            raise forms.ValidationError(
                "El documento no puede tener más de 10 dígitos."
            )
        if PerfilUsuario.objects.filter(documento=documento).exists():
            raise forms.ValidationError("Este número de documento ya está registrado.")
        if User.objects.filter(username=documento).exists():
            raise forms.ValidationError("Este número de documento ya está registrado.")
        if not documento.isdigit():
            raise forms.ValidationError("El documento solo debe contener números.")
        return documento

    def clean_telefono(self):
        """Valida teléfono opcional con solo números y longitud razonable."""
        telefono = (self.cleaned_data.get("telefono") or "").strip()

        if not telefono:
            return ""

        if not telefono.isdigit():
            raise forms.ValidationError("El teléfono solo debe contener números.")

        if len(telefono) < 10:
            raise forms.ValidationError("El teléfono debe tener al menos 10 dígitos.")

        if len(telefono) > 11:
            raise forms.ValidationError("El teléfono no puede tener más de 11 dígitos.")

        return telefono

    def clean_email(self):
        """Valida que el email no exista en la base de datos"""
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

    def clean_password1(self):
        """Valida que la contraseña cumpla con estándares de seguridad"""
        password = self.cleaned_data.get("password1")
        if not password:
            raise forms.ValidationError("La contraseña es obligatoria.")

        errors = []

        if len(password) < 8:
            errors.append("La contraseña debe tener al menos 8 caracteres.")

        if not re.search(r"[A-Z]", password):
            errors.append("Debe contener al menos una letra mayúscula.")

        if not re.search(r"[a-z]", password):
            errors.append("Debe contener al menos una letra minúscula.")

        if not re.search(r"\d", password):
            errors.append("Debe contener al menos un número.")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]', password):
            errors.append("Debe contener al menos un carácter especial (!@#$%^&*...).")

        if errors:
            raise forms.ValidationError(errors)

        return password

    def clean_password2(self):
        """Valida que las contraseñas coincidan"""
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("Las contraseñas no coinciden.")
        return password2

    def save(self, commit=True):
        """
        Guarda el usuario y crea su perfil con el documento
        """
        user = super().save(commit=False)
        user.username = self.cleaned_data["documento"]  # Usamos documento como username
        user.email = self.cleaned_data["email"]

        if commit:
            user.save()
            perfil, created = PerfilUsuario.objects.get_or_create(
                user=user,
                defaults={
                    "documento": self.cleaned_data["documento"],
                    "telefono": self.cleaned_data.get("telefono", ""),
                },
            )
            if not created:
                perfil.documento = self.cleaned_data["documento"]
                perfil.telefono = self.cleaned_data.get("telefono", "")
                perfil.save()

        return user


class EditarUsuarioForm(forms.ModelForm):
    """
    Formulario para editar información del usuario
    """

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ingrese su nombre",
                    "required": True,
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ingrese su apellido",
                    "required": True,
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ingrese su correo electrónico ejm: nombre@dominio.com",
                    "required": True,
                }
            ),
        }
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Correo Electrónico",
        }
        error_messages = {
            "first_name": {
                "required": "El nombre es obligatorio",
            },
            "last_name": {
                "required": "El apellido es obligatorio",
            },
            "email": {
                "required": "El correo electrónico es obligatorio",
                "invalid": "Ingresa un correo válido",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["email"].required = True

    def save(self, commit=True):
        """
        Guarda el usuario preservando la contraseña original
        """
        user = super().save(commit=False)

        if self.instance.pk:
            original_user = User.objects.get(pk=self.instance.pk)
            user.password = original_user.password

        if commit:
            user.save()

        return user


class EditarPerfilForm(forms.ModelForm):
    """
    Formulario para editar el perfil del usuario
    """

    class Meta:
        model = PerfilUsuario
        fields = ["foto_perfil"]
        widgets = {
            "foto_perfil": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Selecciona tu foto de perfil",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)




class PasswordResetRequestForm(forms.Form):
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

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if not User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Este correo no está registrado en el sistema."
            )
        return email


class PasswordResetConfirmForm(forms.Form):
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

        if len(password) < 8:
            errors.append("La contraseña debe tener al menos 8 caracteres.")

        if not re.search(r"[A-Z]", password):
            errors.append("Debe contener al menos una letra mayúscula.")

        if not re.search(r"[a-z]", password):
            errors.append("Debe contener al menos una letra minúscula.")

        if not re.search(r"\d", password):
            errors.append("Debe contener al menos un número.")

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
