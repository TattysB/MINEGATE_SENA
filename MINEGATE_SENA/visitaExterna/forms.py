from django import forms
from .models import VisitaExterna


class VisitaExternaForm(forms.ModelForm):
    """Formulario basado en modelo para crear y editar visitas externas"""
    
    class Meta:
        model = VisitaExterna
        fields = [
            'nombre',
            'responsable',
            'correo',
            'telefono',
            'articulacion',
            'cantidad',
            'fecha',
            'hora'
        ]
        # Widgets
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el nombre de la visita'
            }),
            'responsable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el nombre del responsable'
            }),
            'correo': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '3001234567'
            }),
            'articulacion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese la articulación'
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de visitantes',
                'min': '1'
            }),
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'hora': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            })
        }
        # Etiquetas 
        labels = {
            'nombre': 'Nombre',
            'responsable': 'Responsable',
            'correo': 'Correo Electrónico',
            'telefono': 'Teléfono',
            'articulacion': 'Articulación',
            'cantidad': 'Cantidad de Visitantes',
            'fecha': 'Fecha de la Visita',
            'hora': 'Hora de la Visita'
        }
        
    # Validaciones 
    
    def clean_telefono(self):
        """Validar que el teléfono contenga solo números"""
        telefono = self.cleaned_data.get('telefono')
        if telefono and not telefono.isdigit():
            raise forms.ValidationError("El teléfono debe contener solo números.")
        if telefono and len(telefono) != 10:
            raise forms.ValidationError("El teléfono debe tener 10 dígitos.")
        return telefono
    
    def clean_cantidad(self):
        """Validar que la cantidad sea un número positivo"""
        cantidad = self.cleaned_data.get('cantidad')
        if cantidad and cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser un número positivo mayor a 0.")
        return cantidad
    
    def clean_fecha(self):
        """Validar que la fecha no sea en el pasado"""
        from datetime import date
        fecha = self.cleaned_data.get('fecha')
        if fecha and fecha < date.today():
            raise forms.ValidationError("La fecha no puede ser anterior a hoy.")
        return fecha