from django import forms
from visitaExterna.models import VisitaExterna


class VisitaExternaInstructorForm(forms.ModelForm):
    """
    Formulario para que el instructor externo reserve una visita externa.
    Reutiliza el modelo VisitaExterna existente.
    """

    class Meta:
        model = VisitaExterna
        fields = [
            'nombre',
            'nombre_responsable',
            'tipo_documento_responsable',
            'documento_responsable',
            'correo_responsable',
            'telefono_responsable',
            'cantidad_visitantes',
            'observacion',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la institución o empresa',
            }),
            'nombre_responsable': forms.TextInput(attrs={
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
            'cantidad_visitantes': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cantidad de visitantes',
                'min': '1',
            }),
            'observacion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Observaciones adicionales (opcional)',
            }),
        }
