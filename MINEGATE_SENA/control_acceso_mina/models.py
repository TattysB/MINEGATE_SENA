from django.db import models
from django.contrib.auth.models import User


class RegistroAccesoMina(models.Model):
    """
    Historial congelado de entradas y salidas a la mina.
    Los datos se copian como texto plano al momento del registro,
    de modo que cambios posteriores en Aprendiz o Asistente no alteren el historial.
    """
    TIPO_CHOICES = [
        ('ENTRADA', 'Entrada'),
        ('SALIDA', 'Salida'),
    ]

    VISITA_TIPO_CHOICES = [
        ('interna', 'Interna'),
        ('externa', 'Externa'),
    ]

    documento = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name="Documento"
    )
    nombre_completo = models.CharField(
        max_length=200,
        verbose_name="Nombre Completo"
    )
    categoria = models.CharField(
        max_length=100,
        verbose_name="Categoría",
        help_text="Ej: 'Ficha: 12345' o 'Visitante Externo'"
    )
    visita_tipo = models.CharField(
        max_length=10,
        choices=VISITA_TIPO_CHOICES,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Tipo de Visita"
    )
    visita_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="ID de Visita"
    )
    tipo = models.CharField(
        max_length=7,
        choices=TIPO_CHOICES,
        verbose_name="Tipo de Movimiento"
    )
    fecha_hora = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha y Hora"
    )
    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Registrado por"
    )

    class Meta:
        verbose_name = "Registro de Acceso a la Mina"
        verbose_name_plural = "Registros de Acceso a la Mina"
        ordering = ['-fecha_hora']

    def __str__(self):
        visita_ref = f"{self.visita_tipo}:{self.visita_id}" if self.visita_tipo and self.visita_id else "sin-visita"
        return f"{self.nombre_completo} - {self.tipo} - {visita_ref} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"
