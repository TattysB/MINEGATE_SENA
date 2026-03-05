from django import forms
from .models import VisitaExterna


class VisitaExternaForm(forms.ModelForm):
    """Formulario basado en modelo para crear y editar visitas externas"""
    
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
            'observacion'
        ]
        # Widgets
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el nombre'
            }),
            'nombre_responsable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el nombre'
            }),
            'tipo_documento_responsable': forms.Select(attrs={
                'class': 'form-control'
            }),
            'documento_responsable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Documento del responsable',
                'readonly': True,
                'style': 'background-color: #e9ecef; cursor: not-allowed;'
            }),
            'correo_responsable': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com',
                'readonly': True,
                'style': 'background-color: #e9ecef; cursor: not-allowed;'
            }),
            'telefono_responsable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '3001234567'
            }),
            'cantidad_visitantes': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de visitantes',
                'min': '1'
            }),
            'observacion': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese observaciones (opcional)',
                'rows': 4
            })
        }
        # Etiquetas 
        labels = {
            'nombre': 'Nombre de la Institución',
            'nombre_responsable': 'Nombre del Responsable',
            'tipo_documento_responsable': 'Tipo de Documento del Responsable',
            'documento_responsable': 'Documento del Responsable',
            'correo_responsable': 'Correo del Responsable',
            'telefono_responsable': 'Teléfono',
            'cantidad_visitantes': 'Cantidad de Visitantes',
            'observacion': 'Observación'
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
    
    def clean_cantidad_visitantes(self):
        """Validar que la cantidad sea un número positivo"""
        cantidad = self.cleaned_data.get('cantidad_visitantes')
        if cantidad and cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser un número positivo mayor a 0.")
        return cantidad
