from django import forms
from .models import VisitaInterna


class VisitaInternaForm(forms.ModelForm):
    """Formulario basado en modelo para crear y editar visitas internas"""
    
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
            'observaciones',
        ]
        # Widgets 
        widgets = {
            'nombre_programa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el nombre'
            }),
            'numero_ficha': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de ficha',
                'min': '1'
            }),
            'responsable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el nombre'
            }),
            'tipo_documento_responsable': forms.Select(attrs={
                'class': 'form-control'
            }),
            'documento_responsable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Documento del responsable'
            }),
            'correo_responsable': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'telefono_responsable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '3001234567'
            }),
            'cantidad_aprendices': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de aprendices',
                'min': '1'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese observaciones (opcional)',
                'rows': 4
            }),
        }
        # Etiquetas 
        labels = {
            'nombre_programa': 'Nombre de Programa',
            'numero_ficha': 'Número de Ficha',
            'responsable': 'Responsable',
            'tipo_documento_responsable': 'Tipo de Documento del responsable',
            'documento_responsable': 'Documento del responsable',
            'correo_responsable': 'Correo del responsable',
            'telefono_responsable': 'Teléfono del responsable',
            'cantidad_aprendices': 'Cantidad de aprendices',
            'observaciones': 'Observaciones',
        }
        
    # Validaciones
    
    def clean_telefono_responsable(self):
        """Validar que el teléfono contenga solo números"""
        telefono = self.cleaned_data.get('telefono_responsable')
        if telefono and not telefono.isdigit():
            raise forms.ValidationError("El teléfono debe contener solo números.")
        if telefono and len(telefono) != 10:
            raise forms.ValidationError("El teléfono debe tener 10 dígitos.")
        return telefono
    
    def clean_cantidad_aprendices(self):
        """Validar que la cantidad sea un número positivo"""
        cantidad = self.cleaned_data.get('cantidad_aprendices')
        if cantidad and cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser un número positivo mayor a 0.")
        return cantidad
