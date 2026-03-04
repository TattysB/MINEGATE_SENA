from django import forms
from visitaInterna.models import VisitaInterna
from .models import Ficha, Programa, Aprendiz


class VisitaInternaInstructorForm(forms.ModelForm):
    """
    Formulario para que el instructor interno reserve una visita interna.
    Reutiliza el modelo VisitaInterna existente.
    """

    class Meta:
        model = VisitaInterna
        fields = [
            'nombre_programa',
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
            'nombre_programa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del programa de formación',
            }),
            'numero_ficha': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de ficha',
            }),
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


class FichaForm(forms.ModelForm):
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


class AprendizForm(forms.ModelForm):
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
                'required': True,
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
