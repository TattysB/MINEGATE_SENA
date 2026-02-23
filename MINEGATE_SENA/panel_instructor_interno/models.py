from django.db import models
from django.contrib.auth.models import User


class Programa(models.Model):
    """
    Programa de formación SENA.
    El instructor puede gestionar estos programas para usarlos
    al momento de reservar una visita interna.
    """
    nombre = models.CharField(
        max_length=300,
        unique=True,
        verbose_name='Nombre del Programa'
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='programas_creados',
        verbose_name='Creado por'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Programa'
        verbose_name_plural = 'Programas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Ficha(models.Model):
    """
    Ficha de formación SENA asociada a un programa.
    El instructor puede gestionar estas fichas para usarlas
    al momento de reservar una visita interna.
    """
    numero = models.PositiveIntegerField(
        unique=True,
        verbose_name='Número de Ficha'
    )
    programa = models.ForeignKey(
        Programa,
        on_delete=models.PROTECT,
        related_name='fichas',
        verbose_name='Programa'
    )
    jornada = models.CharField(
        max_length=20,
        choices=[
            ('mañana', 'Mañana'),
            ('tarde', 'Tarde'),
            ('noche', 'Noche'),
            ('mixta', 'Mixta'),
        ],
        default='mañana',
        verbose_name='Jornada'
    )
    cantidad_aprendices = models.PositiveIntegerField(
        default=0,
        verbose_name='Cantidad de Aprendices'
    )
    activa = models.BooleanField(
        default=True,
        verbose_name='Activa'
    )
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fichas_creadas',
        verbose_name='Creado por'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ficha'
        verbose_name_plural = 'Fichas'
        ordering = ['-numero']

    def __str__(self):
        return f'Ficha {self.numero} - {self.programa.nombre}'
