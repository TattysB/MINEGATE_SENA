from django.db import models

class VisitaExterna(models.Model):
    id = models.AutoField(primary_key=True, verbose_name="ID")
    nombre = models.CharField(max_length=200, verbose_name="Nombre de la institución")
    nombre_responsable = models.CharField(max_length=200, verbose_name=" nombre Responsable")
    tipo_documento_responsable = [
        ('CC', 'Cédula de Ciudadanía'),
        ('CE', 'Cédula de Extranjería'),
        ('TI', 'Tarjeta de Identidad'),
        ('PPT', 'Permiso Especial de Permanencia'),
        ('PP', 'Pasaporte'),
    ]
    tipo_documento_responsable = models.CharField(max_length=3, choices=tipo_documento_responsable, verbose_name="Tipo de Documento del responsable")
    documento_responsable = models.CharField(max_length=50, verbose_name="Documento del responsable")
    correo_responsable = models.EmailField(verbose_name="Correo Electrónico del responsable")
    telefono_responsable = models.CharField(max_length=20, verbose_name="Teléfono del responsable")
    cantidad_visitantes = models.IntegerField(verbose_name="Cantidad de Visitantes")
    observacion = models.TextField(verbose_name="Observación", blank=True)
    
    class Meta:
        verbose_name = "Visita Externa"
        verbose_name_plural = "Visitas Externas"  
    
    def __str__(self):
        return f"{self.nombre} - {self.nombre_responsable}"