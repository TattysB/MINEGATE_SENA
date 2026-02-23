from django.db import models
from django.core.validators import MaxValueValidator
from django.conf import settings
from django.utils import timezone
import uuid

class VisitaInterna(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de revisión'),
        ('enviada_coordinacion', 'Enviada a coordinación'),
        ('aprobada_inicial', 'Aprobada - Registro de asistentes habilitado'),
        ('documentos_enviados', 'Documentos enviados - Pendiente revisión'),
        ('en_revision_documentos', 'En revisión de documentos'),
        ('confirmada', 'Visita Confirmada'),
        ('rechazada', 'Rechazada'),
    ]
     
    id = models.AutoField(primary_key=True, verbose_name="ID")
    estado = models.CharField(max_length=25, choices=ESTADO_CHOICES, default='pendiente', verbose_name="Estado")
    token_acceso = models.CharField(max_length=64, unique=True, blank=True, null=True, verbose_name="Token de acceso")
    fecha_solicitud = models.DateTimeField(default=timezone.now, verbose_name="Fecha de solicitud")
    nombre_programa = models.CharField(max_length=200, verbose_name="Nombre de programa", default="")
    numero_ficha = models.PositiveIntegerField(verbose_name="Número de Ficha", default=0)
    responsable = models.CharField(max_length=200, verbose_name="Responsable")
    tipo_documento_responsable = [
        ('CC', 'Cédula de Ciudadanía'),
        ('CE', 'Cédula de Extranjería'),
        ('TI', 'Tarjeta de Identidad'),
        ('PPT', 'Permiso Especial de Permanencia'),
        ('PP', 'Pasaporte'),
    ]
    tipo_documento_responsable = models.CharField(max_length=3, choices=tipo_documento_responsable, verbose_name="Tipo de Documento del responsable")
    documento_responsable = models.CharField(max_length=50, verbose_name="Documento del responsable", default="")
    correo_responsable = models.EmailField(max_length=254, verbose_name="Correo del responsable", default="")
    telefono_responsable = models.CharField(max_length=20, verbose_name="Teléfono del responsable", default="")
    cantidad_aprendices = models.PositiveIntegerField(verbose_name="Cantidad de aprendices", default=0, validators=[MaxValueValidator(99999999)])
    observaciones = models.TextField(verbose_name="Observaciones", blank=True, default="")
    
    def save(self, *args, **kwargs):
        if not self.token_acceso:
            self.token_acceso = uuid.uuid4().hex
        super().save(*args, **kwargs)
    
    def get_enlace_registro(self):
        """Retorna el enlace único para registro de asistentes"""
        return f"/registro-asistentes/interna/{self.token_acceso}/"

    class Meta:
        verbose_name = "Visita Interna"
        verbose_name_plural = "Visitas Internas"
        ordering = ['-id']

    def __str__(self):
        return f"{self.nombre_programa}"


def documento_asistente_path_interna(instance, filename):
    """Genera ruta para documentos de asistentes de visitas internas"""
    return f'documentos_asistentes/interna/{instance.visita.id}/{instance.numero_documento}/{filename}'


class AsistenteVisitaInterna(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('CC', 'Cédula de Ciudadanía'),
        ('CE', 'Cédula de Extranjería'),
        ('TI', 'Tarjeta de Identidad'),
        ('PPT', 'Permiso Especial de Permanencia'),
        ('PP', 'Pasaporte'),
    ]
    
    ESTADO_ASISTENTE_CHOICES = [
        ('pendiente_documentos', 'Pendiente de revisión de documentos'),
        ('documentos_aprobados', 'Documentos aprobados'),
        ('documentos_rechazados', 'Documentos rechazados'),
    ]
    
    visita = models.ForeignKey(VisitaInterna, on_delete=models.CASCADE, related_name='asistentes', verbose_name="Visita")
    nombre_completo = models.CharField(max_length=200, verbose_name="Nombre Completo")
    tipo_documento = models.CharField(max_length=3, choices=TIPO_DOCUMENTO_CHOICES, verbose_name="Tipo de Documento")
    numero_documento = models.CharField(max_length=50, verbose_name="Número de Documento")
    correo = models.EmailField(blank=True, verbose_name="Correo Electrónico")
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    
    # Estado del asistente
    estado = models.CharField(
        max_length=25, 
        choices=ESTADO_ASISTENTE_CHOICES, 
        default='pendiente_documentos', 
        verbose_name="Estado de documentos"
    )
    
    # Documentos
    documento_identidad = models.FileField(
        upload_to=documento_asistente_path_interna,
        blank=True,
        null=True,
        verbose_name="Documento de Identidad (PDF/Imagen)"
    )
    documento_adicional = models.FileField(
        upload_to=documento_asistente_path_interna,
        blank=True,
        null=True,
        verbose_name="Documento Adicional (Opcional)"
    )
    
    # Observaciones del revisor
    observaciones_revision = models.TextField(blank=True, verbose_name="Observaciones de revisión")
    
    class Meta:
        verbose_name = "Asistente de Visita Interna"
        verbose_name_plural = "Asistentes de Visitas Internas"
        ordering = ['nombre_completo']
        unique_together = ['visita', 'numero_documento']
    
    def __str__(self):
        return f"{self.nombre_completo} - {self.visita.nombre_programa}"


class HistorialAccionVisitaInterna(models.Model):
    """Registro de todas las acciones realizadas sobre visitas internas"""
    TIPO_ACCION_CHOICES = [
        ('creacion', 'Solicitud creada'),
        ('ver_detalle', 'Detalle visualizado'),
        ('envio_coordinacion', 'Enviada a coordinación'),
        ('aprobacion', 'Visita aprobada'),
        ('rechazo', 'Visita rechazada'),
        ('notificacion', 'Notificación enviada'),
        ('modificacion', 'Datos modificados'),
    ]
    
    visita = models.ForeignKey(VisitaInterna, on_delete=models.CASCADE, related_name='historial', verbose_name="Visita")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Usuario")
    tipo_accion = models.CharField(max_length=20, choices=TIPO_ACCION_CHOICES, verbose_name="Tipo de acción")
    descripcion = models.TextField(verbose_name="Descripción")
    fecha_hora = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y hora")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Dirección IP")
    
    class Meta:
        verbose_name = "Historial de Acción"
        verbose_name_plural = "Historial de Acciones"
        ordering = ['-fecha_hora']
    
    def __str__(self):
        return f"{self.get_tipo_accion_display()} - {self.visita} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"


class RegistroEnvioCoordinacionInterna(models.Model):
    """Registro de cada envío a coordinación"""
    visita = models.ForeignKey(VisitaInterna, on_delete=models.CASCADE, related_name='envios_coordinacion', verbose_name="Visita")
    correo_destino = models.EmailField(verbose_name="Correo destino")
    usuario_remitente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Remitente")
    fecha_envio = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de envío")
    estado_resultado = models.CharField(max_length=20, choices=[
        ('enviado', 'Enviado exitosamente'),
        ('fallido', 'Fallo en envío'),
    ], default='enviado', verbose_name="Estado")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP")
    
    class Meta:
        verbose_name = "Registro de Envío a Coordinación"
        verbose_name_plural = "Registros de Envíos a Coordinación"
        ordering = ['-fecha_envio']
    
    def __str__(self):
        return f"Envío a {self.correo_destino} - {self.fecha_envio.strftime('%d/%m/%Y %H:%M')}"
