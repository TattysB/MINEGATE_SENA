from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class VisitaExterna(models.Model):
    ESTADO_CHOICES = [
        ("pendiente", "Pendiente de revisión"),
        ("enviada_coordinacion", "Enviada a coordinación"),
        ("aprobada_inicial", "Aprobada - Registro de asistentes habilitado"),
        ("documentos_enviados", "Documentos enviados - Pendiente revisión"),
        ("en_revision_documentos", "En revisión de documentos"),
        ("confirmada", "Visita Confirmada"),
        ("rechazada", "Rechazada"),
    ]

    id = models.AutoField(primary_key=True, verbose_name="ID")
    estado = models.CharField(
        max_length=25,
        choices=ESTADO_CHOICES,
        default="pendiente",
        verbose_name="Estado",
    )
    token_acceso = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Token de acceso",
    )
    fecha_solicitud = models.DateTimeField(
        default=timezone.now, verbose_name="Fecha de solicitud"
    )
    nombre = models.CharField(max_length=200, verbose_name="Nombre de la institución")
    nombre_responsable = models.CharField(
        max_length=200, verbose_name=" nombre Responsable"
    )
    tipo_documento_responsable = [
        ("CC", "Cédula de Ciudadanía"),
        ("CE", "Cédula de Extranjería"),
        ("TI", "Tarjeta de Identidad"),
        ("PPT", "Permiso Especial de Permanencia"),
        ("PP", "Pasaporte"),
    ]
    tipo_documento_responsable = models.CharField(
        max_length=3,
        choices=tipo_documento_responsable,
        verbose_name="Tipo de Documento del responsable",
    )
    documento_responsable = models.CharField(
        max_length=50, verbose_name="Documento del responsable"
    )
    correo_responsable = models.EmailField(
        verbose_name="Correo Electrónico del responsable"
    )
    telefono_responsable = models.CharField(
        max_length=20, verbose_name="Teléfono del responsable"
    )
    cantidad_visitantes = models.IntegerField(verbose_name="Cantidad de Visitantes")

    # Campos de fecha y horario de la visita
    fecha_visita = models.DateField(
        verbose_name="Fecha de la visita", null=True, blank=True
    )
    hora_inicio = models.TimeField(verbose_name="Hora de inicio", null=True, blank=True)
    hora_fin = models.TimeField(verbose_name="Hora de fin", null=True, blank=True)
    
    observacion = models.TextField(verbose_name="Observación", null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.token_acceso:
            self.token_acceso = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def get_enlace_registro(self):
        """Retorna el enlace único para registro de asistentes"""
        return f"/registro-asistentes/externa/{self.token_acceso}/"

    class Meta:
        verbose_name = "Visita Externa"
        verbose_name_plural = "Visitas Externas"  
        db_table = 'visita_externa'
    
    def __str__(self):
        return f"{self.nombre} - {self.nombre_responsable}"


def documento_asistente_path_externa(instance, filename):
    """Genera ruta para documentos de asistentes de visitas externas"""
    return f"documentos_asistentes/externa/{instance.visita.id}/{instance.numero_documento}/{filename}"


class AsistenteVisitaExterna(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ("CC", "Cédula de Ciudadanía"),
        ("CE", "Cédula de Extranjería"),
        ("TI", "Tarjeta de Identidad"),
        ("PPT", "Permiso Especial de Permanencia"),
        ("PP", "Pasaporte"),
    ]

    ESTADO_ASISTENTE_CHOICES = [
        ("pendiente_documentos", "Pendiente de revisión de documentos"),
        ("documentos_aprobados", "Documentos aprobados"),
        ("documentos_rechazados", "Documentos rechazados"),
    ]

    visita = models.ForeignKey(
        VisitaExterna,
        on_delete=models.CASCADE,
        related_name="asistentes",
        verbose_name="Visita",
    )
    nombre_completo = models.CharField(max_length=200, verbose_name="Nombre Completo")
    tipo_documento = models.CharField(
        max_length=3, choices=TIPO_DOCUMENTO_CHOICES, verbose_name="Tipo de Documento"
    )
    numero_documento = models.CharField(
        max_length=50, verbose_name="Número de Documento"
    )
    correo = models.EmailField(blank=True, verbose_name="Correo Electrónico")
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    fecha_registro = models.DateTimeField(
        auto_now_add=True, verbose_name="Fecha de Registro"
    )

    # Estado del asistente
    estado = models.CharField(
        max_length=25,
        choices=ESTADO_ASISTENTE_CHOICES,
        default="pendiente_documentos",
        verbose_name="Estado de documentos",
    )

    # Documentos
    documento_identidad = models.FileField(
        upload_to=documento_asistente_path_externa,
        blank=True,
        null=True,
        verbose_name="Documento de Identidad (PDF/Imagen)",
    )
    documento_adicional = models.FileField(
        upload_to=documento_asistente_path_externa,
        blank=True,
        null=True,
        verbose_name="Documento Adicional (Opcional)",
    )
    formato_autorizacion_padres = models.FileField(
        upload_to=documento_asistente_path_externa,
        blank=True,
        null=True,
        verbose_name="Formato Autorización Padres de Familia (Requerido para menores de edad)",
    )
    estado_autorizacion_padres = models.CharField(
        max_length=20,
        choices=[
            ("pendiente", "Pendiente"),
            ("aprobado", "Aprobado"),
            ("rechazado", "Rechazado"),
        ],
        default="pendiente",
        verbose_name="Estado Autorización Padres",
    )
    observaciones_autorizacion_padres = models.TextField(
        blank=True, verbose_name="Observaciones Autorización Padres"
    )

    # Observaciones del revisor
    observaciones_revision = models.TextField(
        blank=True, verbose_name="Observaciones de revisión"
    )

    # Campos para QR
    qr_generado = models.BooleanField(default=False, verbose_name="QR Generado")
    fecha_envio_qr = models.DateTimeField(
        null=True, blank=True, verbose_name="Fecha de Envío del QR"
    )
    email_qr_enviado = models.BooleanField(
        default=False, verbose_name="Email con QR Enviado"
    )

    # Campos para reutilización de asistentes
    puede_reutilizar = models.BooleanField(
        default=True, verbose_name="Puede reutilizarse en futuras visitas"
    )
    es_reutilizado = models.BooleanField(
        default=False, verbose_name="Es una copia de un asistente anterior"
    )
    visita_original = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="copias",
        verbose_name="Asistente original (si es reutilizado)",
    )

    class Meta:
        verbose_name = "Asistente de Visita Externa"
        verbose_name_plural = "Asistentes de Visitas Externas"
        ordering = ['nombre_completo']
        unique_together = ['visita', 'numero_documento']
        db_table = 'asistente_visita_externa'
    
    def __str__(self):
        return f"{self.nombre_completo} - {self.visita.nombre}"


class HistorialAccionVisitaExterna(models.Model):
    """Registro de todas las acciones realizadas sobre visitas externas"""

    TIPO_ACCION_CHOICES = [
        ("creacion", "Solicitud creada"),
        ("ver_detalle", "Detalle visualizado"),
        ("envio_coordinacion", "Enviada a coordinación"),
        ("aprobacion", "Visita aprobada"),
        ("rechazo", "Visita rechazada"),
        ("notificacion", "Notificación enviada"),
        ("modificacion", "Datos modificados"),
    ]

    visita = models.ForeignKey(
        VisitaExterna,
        on_delete=models.CASCADE,
        related_name="historial",
        verbose_name="Visita",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Usuario",
    )
    tipo_accion = models.CharField(
        max_length=20, choices=TIPO_ACCION_CHOICES, verbose_name="Tipo de acción"
    )
    descripcion = models.TextField(verbose_name="Descripción")
    fecha_hora = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y hora")
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name="Dirección IP"
    )

    class Meta:
        verbose_name = "Historial de Acción"
        verbose_name_plural = "Historial de Acciones"
        ordering = ['-fecha_hora']
        db_table = 'historial_accion_visita_externa'
    
    def __str__(self):
        return f"{self.get_tipo_accion_display()} - {self.visita} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"
