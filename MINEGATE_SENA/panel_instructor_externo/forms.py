from django import forms
from visitaExterna.models import VisitaExterna
import re
from django.core.exceptions import ValidationError



def validar_correo_formato(correo):
    """
    Valida que el correo tenga un formato válido.
    """
    patron_email = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(patron_email, correo):
        raise ValidationError('Por favor, ingresa un correo válido (ej: usuario@ejemplo.com)')


def validar_documento_numero(numero_documento):
    """
    Valida que el número de documento sea solo numérico (5-15 dígitos).
    """
    if not numero_documento:
        raise ValidationError('El número de documento no puede estar vacío.')
    
    numero_documento = str(numero_documento).strip()
    
    if not re.match(r'^[0-9]+$', numero_documento):
        raise ValidationError('El número de documento solo debe contener números (sin puntos ni guiones).')
    
    if len(numero_documento) < 5:
        raise ValidationError('El número de documento debe tener al menos 5 dígitos.')
    if len(numero_documento) > 15:
        raise ValidationError('El número de documento no puede exceder 15 dígitos.')
    
    return numero_documento


def validar_cantidad_minima(cantidad):
    """
    Valida que la cantidad sea un número entero >= 1 y <= 1000.
    """
    try:
        cantidad_int = int(cantidad)
        if cantidad_int < 1:
            raise ValidationError('La cantidad debe ser al menos 1.')
        if cantidad_int > 1000:
            raise ValidationError('La cantidad no puede exceder 1000.')
    except (ValueError, TypeError):
        raise ValidationError('La cantidad debe ser un número entero válido.')
    return cantidad_int


def validar_nombre_alfabetico(nombre, campo='nombre'):
    """
    Valida que el nombre contenga solo letras, espacios y acentos.
    """
    if not nombre:
        raise ValidationError(f'El {campo} no puede estar vacío.')
    
    nombre = nombre.strip()
    
    if not re.match(r"^[a-záéíóúñüA-ZÁÉÍÓÚÑÜ\s'-]+$", nombre):
        raise ValidationError(f'El {campo} solo debe contener letras, espacios y apóstrofos (sin números ni caracteres especiales).')
    
    if len(nombre) < 2:
        raise ValidationError(f'El {campo} debe tener al menos 2 caracteres.')
    if len(nombre) > 100:
        raise ValidationError(f'El {campo} no puede exceder 100 caracteres.')
    
    if not nombre.replace(' ', '').replace("'", ''):
        raise ValidationError(f'El {campo} no puede ser solo espacios.')
    
    return nombre


def validar_telefono(telefono):
    """
    Valida que el teléfono sea solo numérico (7-15 dígitos, con + opcional).
    """
    if not telefono:
        return None  # Opcional
    
    telefono = str(telefono).strip()
    
    if not re.match(r'^[\+]?[0-9\s\-]{6,14}$', telefono):
        raise ValidationError('El teléfono solo debe contener números y caracteres válidos (+, espacios, guiones).')
    
    digitos = re.sub(r'[^\d]', '', telefono)
    if len(digitos) < 7 or len(digitos) > 15:
        raise ValidationError('El teléfono debe tener entre 7 y 15 dígitos.')
    
    return telefono


def validar_observaciones(observaciones):
    """
    Valida que las observaciones sean texto válido (máximo 500 caracteres).
    """
    if not observaciones:
        return None  # Opcional
    
    observaciones = str(observaciones).strip()
    
    if len(observaciones) > 500:
        raise ValidationError('Las observaciones no pueden exceder 500 caracteres.')
    
    if re.search(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', observaciones):
        raise ValidationError('Las observaciones contienen caracteres no permitidos.')
    
    return observaciones



class VisitaExternaInstructorForm(forms.ModelForm):
    """
    Formulario para que el instructor externo reserve una visita externa.
    Con validaciones exhaustivas para todos los campos.
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
            'fecha_visita',
            'hora_inicio',
            'hora_fin',
            'observacion',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la institución o empresa',
                'maxlength': '200',
            }),
            'nombre_responsable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo del responsable',
                'maxlength': '100',
            }),
            'tipo_documento_responsable': forms.Select(attrs={
                'class': 'form-select',
            }),
            'documento_responsable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de documento (solo números)',
                'inputmode': 'numeric',
                'maxlength': '15',
            }),
            'correo_responsable': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com',
                'maxlength': '150',
            }),
            'telefono_responsable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono de contacto',
                'inputmode': 'tel',
                'maxlength': '20',
            }),
            'cantidad_visitantes': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cantidad de visitantes',
                'min': '1',
                'max': '1000',
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
            'observacion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Observaciones adicionales (opcional)',
                'maxlength': '500',
            }),
        }
    
    def clean_nombre(self):
        """Validación del nombre de institución."""
        nombre = self.cleaned_data.get('nombre', '').strip()
        if not nombre:
            raise ValidationError('El nombre de la institución es obligatorio.')
        if len(nombre) < 3:
            raise ValidationError('El nombre debe tener al menos 3 caracteres.')
        if len(nombre) > 200:
            raise ValidationError('El nombre no puede exceder 200 caracteres.')
        return nombre
    
    def clean_nombre_responsable(self):
        """Validación de nombre del responsable (solo letras)."""
        return validar_nombre_alfabetico(
            self.cleaned_data.get('nombre_responsable', ''),
            'nombre del responsable'
        )
    
    def clean_documento_responsable(self):
        """Validación de documento (solo números)."""
        documento = self.cleaned_data.get('documento_responsable', '')
        if not documento:
            raise ValidationError('El número de documento es obligatorio.')
        return validar_documento_numero(documento)
    
    def clean_correo_responsable(self):
        """Validación de correo."""
        correo = self.cleaned_data.get('correo_responsable', '').lower().strip()
        
        if not correo:
            raise ValidationError('El correo es obligatorio.')
        
        validar_correo_formato(correo)
        
        partes = correo.split('@')
        if len(partes) != 2 or '.' not in partes[1]:
            raise ValidationError('El correo debe tener un dominio válido (ej: usuario@empresa.com).')
        
        if len(correo) > 150:
            raise ValidationError('El correo no puede exceder 150 caracteres.')
        
        return correo
    
    def clean_telefono_responsable(self):
        """Validación de teléfono."""
        return validar_telefono(self.cleaned_data.get('telefono_responsable', ''))
    
    def clean_cantidad_visitantes(self):
        """Validación de cantidad - entre 1 y 80 visitantes."""
        cantidad = self.cleaned_data.get('cantidad_visitantes')
        if cantidad is None or cantidad == '':
            raise ValidationError('La cantidad de visitantes es obligatoria.')
        try:
            cantidad_int = int(cantidad)
            if cantidad_int < 1:
                raise ValidationError('Debe registrar mínimo 1 visitante.')
            if cantidad_int > 80:
                raise ValidationError('La cantidad de visitantes no puede exceder 80.')
        except (ValueError, TypeError):
            raise ValidationError('La cantidad debe ser un número válido.')
        return cantidad
    
    def clean_observacion(self):
        """Validación de observaciones."""
        return validar_observaciones(self.cleaned_data.get('observacion', ''))
