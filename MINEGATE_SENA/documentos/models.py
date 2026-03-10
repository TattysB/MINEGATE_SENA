import os
from django.db import models
from django.contrib.auth.models import User


def documento_upload_path(instance, filename):
    """Genera la ruta de subida: media/documentos/usuario_id/filename"""
    return f"documentos/{instance.subido_por.id}/{filename}"


def documento_subido_upload_path(instance, filename):
    """Genera ruta para documentos subidos por asistentes"""
    if instance.asistente_interna:
        return f"documentos_asistentes/interna/{instance.asistente_interna.visita.id}/{instance.asistente_interna.numero_documento}/{filename}"
    elif instance.asistente_externa:
        return f"documentos_asistentes/externa/{instance.asistente_externa.visita.id}/{instance.asistente_externa.numero_documento}/{filename}"
    return f"documentos_asistentes/otros/{filename}"


class Documento(models.Model):
    CATEGORIA_CHOICES = [
        ("EPP Necesarios", "👷🏻‍♂️ EPP Necesarios"),
        ("Formato Inducción y Reinducción", "📜 Formato Inducción y Reinducción"),
        ("ATS", "📝 ATS"),
        (
            "Formato Auto Reporte Condiciones de Salud",
            "👩🏻‍⚕️ Formato Auto Reporte Condiciones de Salud",
        ),
        ("Charla de Seguridad y Calestenia", "🤸🏻‍♂️ Charla de Seguridad y Calestenia"),
        (
            "Formato Autorización Padres de Familia",
            "📋 Formato Autorización Padres de Familia",
        ),
    ]

    titulo = models.CharField(max_length=255)
    archivo = models.FileField(upload_to=documento_upload_path)
    categoria = models.CharField(
        max_length=100, choices=CATEGORIA_CHOICES, default="EPP Necesarios"
    )
    descripcion = models.TextField(blank=True, null=True)
    subido_por = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="documentos"
    )
    fecha_subida = models.DateTimeField(auto_now_add=True)
    tamaño = models.PositiveIntegerField(default=0, help_text="Tamaño en bytes")

    class Meta:
        ordering = ["-fecha_subida"]
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        db_table = "documento"

    def __str__(self):
        return self.titulo

    @property
    def extension(self):
        _, ext = os.path.splitext(self.archivo.name)
        return ext.lower()

    @property
    def tamaño_legible(self):
        size = self.tamaño
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @property
    def nombre_archivo(self):
        return os.path.basename(self.archivo.name)


class DocumentoSubidoAsistente(models.Model):
    """Documento subido por un asistente correspondiente a un documento requerido"""

    documento_requerido = models.ForeignKey(
        Documento,
        on_delete=models.CASCADE,
        related_name="documentos_subidos",
        verbose_name="Documento requerido",
    )
    asistente_interna = models.ForeignKey(
        "visitaInterna.AsistenteVisitaInterna",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documentos_subidos",
    )
    asistente_externa = models.ForeignKey(
        "visitaExterna.AsistenteVisitaExterna",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documentos_subidos",
    )
    ESTADO_CHOICES = [
        ("pendiente", "Pendiente de revisión"),
        ("aprobado", "Aprobado"),
        ("rechazado", "Rechazado"),
    ]
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default="pendiente"
    )
    observaciones_revision = models.TextField(blank=True, null=True)
    archivo = models.FileField(
        upload_to=documento_subido_upload_path,
        max_length=500,
        verbose_name="Archivo subido",
    )
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Documento Subido por Asistente"
        verbose_name_plural = "Documentos Subidos por Asistentes"
        ordering = ["documento_requerido__categoria"]
        db_table = "documento_subido_asistente"

    def __str__(self):
        asistente = self.asistente_interna or self.asistente_externa
        nombre = asistente.nombre_completo if asistente else "N/A"
        return f"{nombre} - {self.documento_requerido.titulo}"

    @property
    def nombre_archivo(self):
        return os.path.basename(self.archivo.name)

    @property
    def extension(self):
        _, ext = os.path.splitext(self.archivo.name)
        return ext.lower()


class DocumentoSubidoAprendiz(models.Model):
    """Documento subido por un aprendiz para un documento requerido"""

    documento_requerido = models.ForeignKey(
        Documento,
        on_delete=models.CASCADE,
        related_name="documentos_subidos_aprendices",
        verbose_name="Documento requerido",
    )
    aprendiz = models.ForeignKey(
        "panel_instructor_interno.Aprendiz",
        on_delete=models.CASCADE,
        related_name="documentos_subidos",
        verbose_name="Aprendiz",
    )
    ESTADO_CHOICES = [
        ("pendiente", "Pendiente de revisión"),
        ("aprobado", "Aprobado"),
        ("rechazado", "Rechazado"),
    ]
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default="pendiente"
    )
    observaciones_revision = models.TextField(blank=True, null=True)
    archivo = models.FileField(
        upload_to="documentos_aprendices/%Y/%m/",
        max_length=500,
        verbose_name="Archivo subido",
    )
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Documento Subido por Aprendiz"
        verbose_name_plural = "Documentos Subidos por Aprendices"
        ordering = ["-fecha_subida"]
        unique_together = ["aprendiz", "documento_requerido"]

    def __str__(self):
        return f"{self.aprendiz.get_nombre_completo()} - {self.documento_requerido.titulo}"

    @property
    def nombre_archivo(self):
        return os.path.basename(self.archivo.name)

    @property
    def extension(self):
        _, ext = os.path.splitext(self.archivo.name)
        return ext.lower()
