from django import forms
from visitaInterna.models import VisitaInterna
from .models import Ficha, Programa, Aprendiz
from django.core.exceptions import ValidationError


class VisitaInternaInstructorForm(forms.ModelForm):
    """
    Formulario para que el instructor interno reserve una visita interna.
    Reutiliza el modelo VisitaInterna existente.
    """

    numero_ficha = forms.TypedChoiceField(
        required=True,
        coerce=int,
        empty_value=None,
        widget=forms.Select(
            attrs={
                'class': 'form-select',
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        # Compatibilidad con vistas que envian owner_user.
        self.owner_user = kwargs.pop("owner_user", None)
        super().__init__(*args, **kwargs)

        fichas_qs = Ficha.objects.select_related('programa').filter(
            activa=True,
            programa__activo=True,
        )
        if self.owner_user is not None:
            fichas_qs = fichas_qs.filter(creado_por=self.owner_user)

        fichas_qs = fichas_qs.order_by('programa__nombre', 'numero')
        self.fields['numero_ficha'].choices = [
            ('', 'Selecciona una ficha'),
            *[
                (ficha.numero, f'{ficha.programa.nombre} - Ficha {ficha.numero}')
                for ficha in fichas_qs
            ],
        ]

    class Meta:
        model = VisitaInterna
        fields = [
            'numero_ficha',
            'responsable',
            'tipo_documento_responsable',
            'documento_responsable',
            'correo_responsable',
            'telefono_responsable',
            'cantidad_aprendices',
            'fecha_visita',
            'hora_inicio',
            'hora_fin',
            'observaciones',
        ]
        widgets = {
            'responsable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo del responsable',
            }),
            'tipo_documento_responsable': forms.Select(attrs={
                'class': 'form-select',
            }),
            'documento_responsable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de documento',
            }),
            'correo_responsable': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com',
            }),
            'telefono_responsable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono de contacto',
            }),
            'cantidad_aprendices': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cantidad de aprendices',
                'min': '1',
            }),
            'fecha_visita': forms.HiddenInput(attrs={
                'id': 'id_fecha_visita',
            }),
            'hora_inicio': forms.HiddenInput(attrs={
                'id': 'id_hora_inicio',
            }),
            'hora_fin': forms.HiddenInput(attrs={
                'id': 'id_hora_fin',
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Observaciones adicionales (opcional)',
            }),
        }


class ProgramaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.owner_user = kwargs.pop("owner_user", None)
        self.current_programa_id = kwargs.pop("current_programa_id", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Programa
        fields = ['nombre', 'descripcion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del programa de formación',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción del programa (opcional)',
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_nombre(self):
        nombre = (self.cleaned_data.get('nombre') or '').strip()
        if not nombre:
            raise ValidationError('El nombre del programa es obligatorio.')

        if self.owner_user is not None:
            existe = Programa.objects.filter(
                creado_por=self.owner_user,
                nombre__iexact=nombre,
            )
            if self.current_programa_id:
                existe = existe.exclude(pk=self.current_programa_id)
            if existe.exists():
                raise ValidationError(
                    'Ya existe un programa con ese nombre. No se distingue entre mayúsculas y minúsculas.'
                )

        return nombre


class FichaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.owner_user = kwargs.pop("owner_user", None)
        super().__init__(*args, **kwargs)

        programas_qs = Programa.objects.filter(activo=True)
        if self.owner_user is not None:
            programas_qs = programas_qs.filter(creado_por=self.owner_user)

        self.fields['programa'].queryset = programas_qs.order_by('nombre')

    class Meta:
        model = Ficha
        fields = ['numero', 'programa', 'jornada', 'cantidad_aprendices', 'activa']
        widgets = {
            'numero': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de ficha',
                'min': '1',
            }),
            'programa': forms.Select(attrs={
                'class': 'form-select',
            }),
            'jornada': forms.Select(attrs={
                'class': 'form-select',
            }),
            'cantidad_aprendices': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cantidad de aprendices',
                'min': '0',
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


class FichaProgramaUnificadoForm(forms.Form):
    """Formulario para registrar/editar programa y ficha en una sola operación."""

    def __init__(self, *args, **kwargs):
        self.owner_user = kwargs.pop('owner_user', None)
        self.current_programa_id = kwargs.pop('current_programa_id', None)
        super().__init__(*args, **kwargs)

    programa_nombre = forms.CharField(
        label='Nombre del programa',
        max_length=300,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del programa de formación',
                'maxlength': '300',
            }
        ),
    )
    numero_ficha = forms.IntegerField(
        label='Número de ficha',
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 2876541',
                'min': '1',
                'max': '9999999999',
            }
        ),
    )
    jornada = forms.ChoiceField(
        label='Jornada',
        choices=Ficha._meta.get_field('jornada').choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    cantidad_aprendices = forms.IntegerField(
        label='Cantidad de aprendices',
        min_value=1,
        max_value=100,
        initial=1,
        widget=forms.NumberInput(
            attrs={
                'class': 'form-control',
                'placeholder': '1',
                'min': '1',
                'max': '100',
            }
        ),
    )

    def clean_programa_nombre(self):
        nombre = (self.cleaned_data.get('programa_nombre') or '').strip()
        if not nombre:
            raise ValidationError('El nombre del programa es obligatorio.')

        if self.owner_user is not None:
            existe = Programa.objects.filter(
                creado_por=self.owner_user,
                nombre__iexact=nombre,
            )
            if self.current_programa_id:
                existe = existe.exclude(pk=self.current_programa_id)
            if existe.exists():
                raise ValidationError(
                    'Ya existe un programa con ese nombre. No se distingue entre mayúsculas y minúsculas.'
                )

        return nombre


class AprendizForm(forms.ModelForm):
    def __init__(self, *args, ficha=None, **kwargs):
        # Compatibilidad con vistas que envian ficha.
        self.ficha = ficha
        super().__init__(*args, **kwargs)

        documento_identidad = self.fields.get('documento_identidad')
        if documento_identidad is not None:
            documento_identidad.required = False
            documento_identidad.widget.attrs.pop('required', None)

    def clean(self):
        cleaned_data = super().clean()
        numero_documento = cleaned_data.get('numero_documento')
        ficha = self.ficha or (self.instance.ficha if self.instance and self.instance.pk else None)

        if numero_documento and ficha:
            query = Aprendiz.objects.filter(ficha=ficha, numero_documento=numero_documento)
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise ValidationError(
                    f'❌ Ya existe un aprendiz con el documento {numero_documento} en esta ficha. '
                    f'Cada documento debe ser único por ficha.'
                )

        return cleaned_data

    class Meta:
        model = Aprendiz
        fields = ['nombre', 'apellido', 'tipo_documento', 'numero_documento', 'correo', 'telefono', 'documento_identidad', 'documento_adicional', 'estado']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del aprendiz',
            }),
            'apellido': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellido del aprendiz',
            }),
            'tipo_documento': forms.Select(attrs={
                'class': 'form-select',
            }),
            'numero_documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de documento',
            }),
            'correo': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com',
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono (opcional)',
            }),
            'documento_identidad': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,.pdf',
            }),
            'documento_adicional': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,.pdf',
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select',
            }),
        }
        labels = {
            'documento_identidad': 'Documento de Identidad ★',
            'documento_adicional': 'Documento Adicional (Opcional)',
        }
