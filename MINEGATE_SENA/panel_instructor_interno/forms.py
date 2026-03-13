from django import forms
from visitaInterna.models import VisitaInterna
from .models import Ficha, Programa, Aprendiz
import os
import re
from django.core.exceptions import ValidationError


# ==================== VALIDADORES PERSONALIZADOS ====================

EXTENSIONES_DOCUMENTO_APRENDIZ_PERMITIDAS = {'.pdf', '.doc', '.docx'}


def validar_archivo_pdf_word(archivo, nombre_campo='archivo'):
    """Permite solo archivos PDF o Word para documentos del aprendiz."""
    if not archivo:
        return archivo

    extension = os.path.splitext(archivo.name)[1].lower()
    if extension not in EXTENSIONES_DOCUMENTO_APRENDIZ_PERMITIDAS:
        raise ValidationError(
            f'El {nombre_campo} debe estar en formato PDF o Word (.doc, .docx).'
        )

    return archivo

def validar_correo_formato(correo):
    """
    Valida que el correo tenga un formato válido.
    """
    patron_email = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(patron_email, correo):
        raise ValidationError('Por favor, ingresa un correo válido (ej: usuario@ejemplo.com)')


def validar_documento_numero(numero_documento, min_len=5, max_len=15):
    """
    Valida que el número de documento sea solo numérico y cumpla longitud.
    """
    if not numero_documento:
        raise ValidationError('El número de documento no puede estar vacío.')
    
    numero_documento = str(numero_documento).strip()
    
    # Solo números permitidos
    if not re.match(r'^[0-9]+$', numero_documento):
        raise ValidationError('El número de documento solo debe contener números (sin puntos ni guiones).')
    
    # Validar rango de longitud
    if len(numero_documento) < min_len:
        raise ValidationError(f'El número de documento debe tener al menos {min_len} dígitos.')
    if len(numero_documento) > max_len:
        raise ValidationError(f'El número de documento no puede exceder {max_len} dígitos.')
    
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
    
    # Normaliza espacios múltiples a un solo espacio.
    nombre = re.sub(r'\s+', ' ', nombre.strip())
    
    # Permite letras (incluyendo acentos), espacios y apóstrofos
    if not re.match(r"^[a-záéíóúñüA-ZÁÉÍÓÚÑÜ\s'-]+$", nombre):
        raise ValidationError(f'El {campo} solo debe contener letras, espacios y apóstrofos (sin números ni caracteres especiales).')
    
    # Validar longitud
    if len(nombre) < 2:
        raise ValidationError(f'El {campo} debe tener al menos 2 caracteres.')
    if len(nombre) > 100:
        raise ValidationError(f'El {campo} no puede exceder 100 caracteres.')
    
    # Validar que no sea solo espacios
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
    
    # Permite números, +, espacios y guiones
    if not re.match(r'^[\+]?[0-9\s\-]{7,20}$', telefono):
        raise ValidationError('El teléfono solo debe contener números y caracteres válidos (+, espacios, guiones).')
    
    # Contar solo los dígitos
    digitos = re.sub(r'[^\d]', '', telefono)
    if len(digitos) < 7 or len(digitos) > 15:
        raise ValidationError('El teléfono debe tener entre 7 y 15 dígitos.')
    
    return telefono


def validar_numero_ficha(numero_ficha):
    """
    Valida que el número de ficha sea solo numérico (1-10 dígitos).
    """
    if not numero_ficha:
        raise ValidationError('El número de ficha es obligatorio.')
    
    numero_ficha = str(numero_ficha).strip()
    
    if not re.match(r'^[0-9]+$', numero_ficha):
        raise ValidationError('El número de ficha solo debe contener números.')
    
    if len(numero_ficha) > 10:
        raise ValidationError('El número de ficha no puede exceder 10 dígitos.')
    
    return numero_ficha


def validar_observaciones(observaciones):
    """
    Valida que las observaciones sean texto válido (máximo 500 caracteres).
    """
    if not observaciones:
        return None  # Opcional
    
    observaciones = str(observaciones).strip()
    
    if len(observaciones) > 500:
        raise ValidationError('Las observaciones no pueden exceder 500 caracteres.')
    
    # Rechaza caracteres de control peligrosos
    if re.search(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', observaciones):
        raise ValidationError('Las observaciones contienen caracteres no permitidos.')
    
    return observaciones


# ==================== FORMULARIOS ====================

class VisitaInternaInstructorForm(forms.ModelForm):
    """
    Formulario para que el instructor interno reserve una visita interna.
    Con validaciones exhaustivas para todos los campos.
    """

    numero_ficha = forms.TypedChoiceField(
        coerce=int,
        choices=[],
        empty_value=None,
        label='Programa y ficha',
        widget=forms.Select(
            attrs={
                'class': 'form-select',
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        fichas = Ficha.objects.filter(activa=True).select_related('programa').order_by('numero')

        self.fields['numero_ficha'].choices = [('', 'Seleccione programa y ficha')] + [
            (f.numero, f'{f.programa.nombre} - Ficha {f.numero}') for f in fichas
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
            'cantidad_aprendices': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0',
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
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Observaciones adicionales (opcional)',
                'maxlength': '500',
            }),
        }
    
    def clean_numero_ficha(self):
        """Validación de ficha existente."""
        numero = self.cleaned_data.get('numero_ficha')
        if numero is None or numero == '':
            raise ValidationError('Debe seleccionar una ficha.')

        if not Ficha.objects.filter(numero=numero, activa=True).exists():
            raise ValidationError('La ficha seleccionada no es válida o está inactiva.')

        return int(numero)
    
    def clean_responsable(self):
        """Validación de nombre del responsable (solo letras)."""
        return validar_nombre_alfabetico(
            self.cleaned_data.get('responsable', ''),
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
        
        # Validar dominio
        partes = correo.split('@')
        if len(partes) != 2 or '.' not in partes[1]:
            raise ValidationError('El correo debe tener un dominio válido (ej: usuario@empresa.com).')
        
        if len(correo) > 150:
            raise ValidationError('El correo no puede exceder 150 caracteres.')
        
        return correo
    
    def clean_telefono_responsable(self):
        """Validación de teléfono."""
        return validar_telefono(self.cleaned_data.get('telefono_responsable', ''))
    
    def clean_cantidad_aprendices(self):
        """Validación de cantidad."""
        cantidad = self.cleaned_data.get('cantidad_aprendices')
        if cantidad is None or cantidad == '':
            raise ValidationError('La cantidad de aprendices es obligatoria.')
        return validar_cantidad_minima(cantidad)
    
    def clean_observaciones(self):
        """Validación de observaciones."""
        return validar_observaciones(self.cleaned_data.get('observaciones', ''))


class ProgramaForm(forms.ModelForm):
    class Meta:
        model = Programa
        fields = ['nombre', 'descripcion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del programa de formación',
                'maxlength': '200',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción del programa (opcional)',
                'maxlength': '500',
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
    
    def clean_nombre(self):
        """Validación del nombre."""
        return validar_nombre_alfabetico(
            self.cleaned_data.get('nombre', ''),
            'nombre del programa'
        )
    
    def clean_descripcion(self):
        """Validación de descripción."""
        return validar_observaciones(self.cleaned_data.get('descripcion', ''))


class FichaForm(forms.ModelForm):
    class Meta:
        model = Ficha
        fields = ['numero', 'programa', 'jornada', 'cantidad_aprendices', 'activa']
        widgets = {
            'numero': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0',
                'min': '1',
                'max': '9999999999',
            }),
            'programa': forms.Select(attrs={
                'class': 'form-select',
            }),
            'jornada': forms.Select(attrs={
                'class': 'form-select',
            }),
            'cantidad_aprendices': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0',
                'min': '0',
                'max': '100',
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
    
    def clean_numero(self):
        """Validación del número de ficha."""
        numero = self.cleaned_data.get('numero')
        if numero is None or numero == '':
            raise ValidationError('El número de ficha es obligatorio.')
        return validar_numero_ficha(numero)
    
    def clean_cantidad_aprendices(self):
        """Validación de cantidad."""
        cantidad = self.cleaned_data.get('cantidad_aprendices')
        if cantidad is not None and cantidad != '':
            try:
                cantidad = int(cantidad)
            except (TypeError, ValueError):
                raise ValidationError('La cantidad de aprendices debe ser un número entero válido.')

            if cantidad < 0:
                raise ValidationError('La cantidad de aprendices no puede ser negativa.')

            if cantidad > 100:
                raise ValidationError('La cantidad de aprendices por ficha no puede ser mayor a 100.')

            return cantidad
        return 0


class AprendizForm(forms.ModelForm):
    """
    Formulario para registrar aprendices con validaciones completas.
    """
    
    def __init__(self, *args, ficha=None, **kwargs):
        """Inicializa el formulario con la ficha opcional para validación."""
        self.ficha = ficha
        super().__init__(*args, **kwargs)
    
    class Meta:
        model = Aprendiz
        fields = ['nombre', 'apellido', 'tipo_documento', 'numero_documento', 'correo', 'telefono', 'documento_identidad', 'documento_adicional', 'estado']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del aprendiz',
                'maxlength': '100',
                'minlength': '2',
                'pattern': r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s'-]{2,100}",
                'title': 'Solo letras y espacios (2 a 100 caracteres).',
            }),
            'apellido': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellido del aprendiz',
                'maxlength': '100',
                'minlength': '2',
                'pattern': r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s'-]{2,100}",
                'title': 'Solo letras y espacios (2 a 100 caracteres).',
            }),
            'tipo_documento': forms.Select(attrs={
                'class': 'form-select',
            }),
            'numero_documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de documento (solo números)',
                'inputmode': 'numeric',
                'maxlength': '10',
                'minlength': '5',
                'pattern': r'[0-9]{5,10}',
                'title': 'Ingresa entre 5 y 10 dígitos numéricos.',
            }),
            'correo': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com (requerido para QR)',
                'maxlength': '150',
                'autocomplete': 'email',
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono (opcional)',
                'inputmode': 'tel',
                'maxlength': '20',
                'pattern': r'^[\+]?[0-9\s\-]{7,20}$',
                'title': 'Teléfono válido: 7 a 15 dígitos (puede incluir +, espacios y guiones).',
            }),
            'documento_identidad': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'required': True,
            }),
            'documento_adicional': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select',
            }),
        }
        labels = {
            'documento_identidad': 'Documento de Identidad ★',
            'documento_adicional': 'Documento Adicional (Opcional)',
        }
    
    def clean_nombre(self):
        """Validación de nombre (solo letras)."""
        return validar_nombre_alfabetico(
            self.cleaned_data.get('nombre', ''),
            'nombre del aprendiz'
        )
    
    def clean_apellido(self):
        """Validación de apellido (solo letras)."""
        return validar_nombre_alfabetico(
            self.cleaned_data.get('apellido', ''),
            'apellido del aprendiz'
        )
    
    def clean_numero_documento(self):
        """Validación de documento (solo números)."""
        documento = self.cleaned_data.get('numero_documento', '')
        if not documento:
            raise ValidationError('El número de documento es obligatorio.')
        return validar_documento_numero(documento, min_len=5, max_len=10)
    
    def clean_correo(self):
        """Validación de correo (CRÍTICO para envío de QR)."""
        correo = self.cleaned_data.get('correo', '').lower().strip()
        
        if not correo:
            raise ValidationError('El correo es OBLIGATORIO (necesario para envío del QR).')
        
        validar_correo_formato(correo)
        
        # Validar dominio
        partes = correo.split('@')
        if len(partes) != 2 or '.' not in partes[1]:
            raise ValidationError('El correo debe tener un dominio válido.')
        
        if len(correo) > 150:
            raise ValidationError('El correo no puede exceder 150 caracteres.')
        
        return correo
    
    def clean_telefono(self):
        """Validación de teléfono."""
        return validar_telefono(self.cleaned_data.get('telefono', ''))

    def clean_documento_identidad(self):
        """Valida formato permitido para documento de identidad."""
        return validar_archivo_pdf_word(
            self.cleaned_data.get('documento_identidad'),
            'documento de identidad'
        )

    def clean_documento_adicional(self):
        """Valida formato permitido para documento adicional."""
        return validar_archivo_pdf_word(
            self.cleaned_data.get('documento_adicional'),
            'documento adicional'
        )
    
    def clean(self):
        """Validación de la combinación única ficha + numero_documento."""
        cleaned_data = super().clean()
        numero_documento = cleaned_data.get('numero_documento')
        
        # Obtener ficha: de la inicialización o del instance
        ficha = self.ficha or (self.instance.ficha if self.instance else None)
        
        if numero_documento and ficha:
            from django.db.models import Q
            # Excluir el aprendiz actual si está editando
            query = Q(ficha=ficha, numero_documento=numero_documento)
            if self.instance and self.instance.pk:
                query &= ~Q(pk=self.instance.pk)
            
            if Aprendiz.objects.filter(query).exists():
                raise ValidationError(
                    f'❌ Ya existe un aprendiz con el documento {numero_documento} en esta ficha. '
                    f'Cada documento debe ser único por ficha.'
                )
        
        return cleaned_data

