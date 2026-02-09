from django.db import models
from django.core.validators import MaxValueValidator

class VisitaInterna(models.Model):
     
    id = models.AutoField(primary_key=True, verbose_name="ID")
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
    

    class Meta:
        verbose_name = "Visita Interna"
        verbose_name_plural = "Visitas Internas"
        ordering = ['-id']

    def __str__(self):
        return f"{self.nombre_programa}"
