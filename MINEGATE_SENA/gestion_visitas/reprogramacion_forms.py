"""
Formularios para gestión de reprogramación de visitas
y cambios de estado con validaciones personalizadas
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from visitaInterna.models import VisitaInterna, HistorialReprogramacion as HistorialReprogramacionInterna
from visitaExterna.models import VisitaExterna, HistorialReprogramacion as HistorialReprogramacionExterna
from panel_instructor_interno.models import Aprendiz


class SolicitudesReprogramacionForm(forms.Form):
    """
    Formulario para solicitar reprogramación de una visita
    Usado por coordinador o administrador
    """
    
    motivo = forms.CharField(
        label='Motivo de la Reprogramación',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Explica por qué se requiere cambio de fecha...',
            'maxlength': 500
        }),
        max_length=500,
        required=True,
        help_text='Máximo 500 caracteres'
    )
    
    tipo_solicitud = forms.ChoiceField(
        label='Tipo de Solicitud',
        choices=[
            ('coordinador', 'Solicitar como Coordinador'),
            ('administrador', 'Solicitar como Administrador'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=True
    )
    
    def __init__(self, usuario=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        
        # Si el usuario es coordinador, predefinir
        if usuario and usuario.groups.filter(name="coordinador").exists():
            self.fields['tipo_solicitud'].initial = 'coordinador'
            self.fields['tipo_solicitud'].widget.attrs['disabled'] = True
    
    def clean_motivo(self):
        motivo = self.cleaned_data.get('motivo', '').strip()
        if not motivo:
            raise ValidationError('El motivo es requerido.')
        if len(motivo) < 10:
            raise ValidationError('El motivo debe tener al menos 10 caracteres.')
        return motivo


class CompletarReprogramacionForm(forms.Form):
    """
    Formulario para completar la reprogramación eligiendo nueva fecha
    Usado por instructor u organizador de la visita
    """
    
    fecha = forms.DateField(
        label='Nueva Fecha',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'required': True
        }),
        required=True,
        help_text='Selecciona una fecha futura'
    )
    
    hora = forms.TimeField(
        label='Nueva Hora de Inicio',
        widget=forms.TimeInput(attrs={
            'class': 'form-control',
            'type': 'time',
            'required': True
        }),
        required=True,
        help_text='Selecciona la hora de inicio de la visita'
    )
    
    duracion_horas = forms.IntegerField(
        label='Duración (horas)',
        initial=2,
        min_value=1,
        max_value=8,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'type': 'number',
            'min': '1',
            'max': '8'
        }),
        help_text='Duración aproximada de la visita'
    )
    
    observacion = forms.CharField(
        label='Observación (opcional)',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Comentarios adicionales...',
            'maxlength': 300
        }),
        max_length=300,
        required=False
    )
    
    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if fecha:
            # Validar que sea una fecha futura
            hoy = timezone.now().date()
            if fecha <= hoy:
                raise ValidationError('La nuevo debe ser en el futuro.')
            
            # Validar no más allá de 90 días
            fecha_max = hoy + timedelta(days=90)
            if fecha > fecha_max:
                raise ValidationError('La fecha no puede ser más allá de 90 días.')
        
        return fecha
    
    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha')
        hora = cleaned_data.get('hora')
        
        if fecha and hora:
            # Validar que fecha + hora sea en el futuro
            fecha_hora = timezone.datetime.combine(fecha, hora)
            if fecha_hora < timezone.now():
                raise ValidationError('La fecha y hora deben ser en el futuro.')
        
        return cleaned_data


class RegistroRechazoDocumentoForm(forms.Form):
    """
    Formulario para registrar el rechazo de documentos de un aprendiz
    Usado por administrador
    """
    
    aprendiz = forms.ModelChoiceField(
        label='Aprendiz',
        queryset=Aprendiz.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    
    motivo_rechazo = forms.CharField(
        label='Motivo del Rechazo',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Describe qué documentos tienen problemas y por qué...',
            'maxlength': 500
        }),
        max_length=500,
        required=True
    )
    
    documentos_pendientes = forms.MultipleChoiceField(
        label='Documentos Pendientes de Reenvío',
        choices=[
            ('identidad', 'Cédula/Documento de Identidad'),
            ('adicional', 'Documento Adicional'),
            ('autorizacion', 'Autorización de Padres'),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
        help_text='Selecciona los documentos que deben ser reenviados'
    )
    
    forzar_reprogramacion = forms.BooleanField(
        label='Forzar Reprogramación Inmediata',
        initial=False,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Si la visita es en menos de 24h, cambiar automáticamente a reprogramación'
    )
    
    def clean_motivo_rechazo(self):
        motivo = self.cleaned_data.get('motivo_rechazo', '').strip()
        if not motivo:
            raise ValidationError('El motivo del rechazo es requerido.')
        if len(motivo) < 10:
            raise ValidationError('El motivo debe ser más descriptivo (al menos 10 caracteres).')
        return motivo
    
    def __init__(self, visita=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Si se proporciona una visita, filtrar aprendices de esa visita
        if visita:
            if hasattr(visita, 'visitainterna'):
                # Es una visita interna
                self.fields['aprendiz'].queryset = Aprendiz.objects.filter(
                    ficha__numero=visita.numero_ficha
                )
            # Para visita externa, se podría agregar lógica similar si existe relación


class CambioEstadoVisitaForm(forms.Form):
    """
    Formulario genérico para cambiar el estado de una visita
    Con validaciones según permisos del usuario
    """
    
    TRANSICIONES_COORDINADOR = [
        ('aprobada_coord', 'Aprobar Fecha'),
        ('reprogramacion_solicitada', 'Solicitar Reprogramación'),
        ('rechazada', 'Rechazar Visita'),
    ]
    
    TRANSICIONES_ADMIN = [
        ('correccion_docs', 'Solicitar Corrección de Documentos'),
        ('reprogramacion_solicitada', 'Forzar Reprogramación'),
        ('rechazada', 'Rechazar Visita'),
        ('aprobada_final', 'Aprobar Final'),
    ]
    
    nuevo_estado = forms.ChoiceField(
        label='Nuevo Estado',
        choices=[],  # Se llena dinámicamente en __init__
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=True
    )
    
    observaciones = forms.CharField(
        label='Observaciones',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Notas sobre este cambio de estado...',
            'maxlength': 500
        }),
        max_length=500,
        required=False
    )
    
    def __init__(self, usuario=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        
        # Determinar qué transiciones están disponibles
        if usuario:
            if usuario.is_superuser:
                self.fields['nuevo_estado'].choices = self.TRANSICIONES_ADMIN
            elif usuario.groups.filter(name="coordinador").exists():
                self.fields['nuevo_estado'].choices = self.TRANSICIONES_COORDINADOR
            else:
                # Usuario normal, sin cambios de estado
                self.fields['nuevo_estado'].widget.attrs['disabled'] = True


class FilterReprogramacionesForm(forms.Form):
    """
    Formulario para filtrar el historial de reprogramaciones
    """
    
    completada = forms.ChoiceField(
        label='Estado de Reprogramación',
        choices=[
            ('', 'Todas'),
            ('true', 'Completadas'),
            ('false', 'Pendientes'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    
    tipo_solicitud = forms.ChoiceField(
        label='Tipo de Solicitud',
        choices=[
            ('', 'Todas'),
            ('coordinador', 'Por Coordinador'),
            ('administrador', 'Por Administrador'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    
    fecha_desde = forms.DateField(
        label='Desde',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False
    )
    
    fecha_hasta = forms.DateField(
        label='Hasta',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        fecha_desde = cleaned_data.get('fecha_desde')
        fecha_hasta = cleaned_data.get('fecha_hasta')
        
        if fecha_desde and fecha_hasta:
            if fecha_desde > fecha_hasta:
                raise ValidationError('La fecha "desde" no puede ser posterior a "hasta".')
        
        return cleaned_data
