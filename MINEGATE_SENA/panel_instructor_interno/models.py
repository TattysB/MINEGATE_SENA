from django.core.validators import MaxValueValidator, MinValueValidator
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
        verbose_name='Descripción',
        null=True
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
        db_table = 'programa'

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
        default=1,
        verbose_name='Cantidad de Aprendices',
        validators=[
            MinValueValidator(1),
            MaxValueValidator(100),
        ],
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
        db_table = 'ficha'

    def __str__(self):
        return f'Ficha {self.numero} - {self.programa.nombre}'    
    def tiene_visitas_registradas(self):
        """Verifica si la ficha tiene al menos una visita registrada"""
        from visitaInterna.models import VisitaInterna
        return VisitaInterna.objects.filter(numero_ficha=self.numero).exists()


class Aprendiz(models.Model):
    """
    Modelo para gestionar aprendices asociados a una ficha.
    Los aprendices se registran directamente en la ficha con sus documentos.
    """
    ficha = models.ForeignKey(
        Ficha,
        on_delete=models.CASCADE,
        related_name='aprendices',
        verbose_name='Ficha'
    )
    
    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre'
    )
    
    apellido = models.CharField(
        max_length=100,
        verbose_name='Apellido'
    )
    
    tipo_documento = models.CharField(
        max_length=3,
        choices=[
            ('CC', 'Cédula de Ciudadanía'),
            ('CE', 'Cédula de Extranjería'),
            ('TI', 'Tarjeta de Identidad'),
            ('PPT', 'Permiso Especial de Permanencia'),
            ('PP', 'Pasaporte'),
        ],
        default='CC',
        verbose_name='Tipo de Documento'
    )
    
    numero_documento = models.CharField(
        max_length=10,
        verbose_name='Número de Documento'
    )
    
    correo = models.EmailField(
        verbose_name='Correo Electrónico'
    )
    
    telefono = models.CharField(
        max_length=20,
        blank=False,
        verbose_name='Teléfono',
        null=False,
        default=''
    )
    
    documento_identidad = models.FileField(
        upload_to='aprendices/documentos/%Y/%m/',
        blank=True,
        null=True,
    )
    
    documento_adicional = models.FileField(
        upload_to='aprendices/documentos/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='Documento Adicional (Opcional)',
        help_text='PDF o imagen de documento adicional'
    )
    
    estado = models.CharField(
        max_length=20,
        choices=[
            ('activo', 'Activo'),
            ('inactivo', 'Inactivo'),
            ('retirado', 'Retirado'),
        ],
        default='activo',
        verbose_name='Estado'
    )
    
    estado_doc = models.CharField(
        max_length=20,
        choices=[
            ('pendiente', 'Pendiente de revisión'),
            ('aprobado', 'Documentos aprobados'),
            ('rechazado', 'Documentos rechazados'),
        ],
        default='pendiente',
        verbose_name='Estado de Documentos'
    )
    
    observaciones_doc = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observaciones sobre Documentos',
        help_text='Observaciones del revisor sobre los documentos del aprendiz'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Aprendiz'
        verbose_name_plural = 'Aprendices'
        ordering = ['apellido', 'nombre']
        unique_together = ['ficha', 'numero_documento']
        db_table = 'aprendiz'
    
    def __str__(self):
        return f"{self.nombre} {self.apellido} - Ficha {self.ficha.numero}"
    
    def get_nombre_completo(self):
        """Retorna nombre completo del aprendiz"""
        return f"{self.nombre} {self.apellido}"