from django.db import models

class VisitaExterna(models.Model):
    id = models.AutoField(primary_key=True, verbose_name="ID")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    responsable = models.CharField(max_length=200, verbose_name="Responsable")
    correo = models.EmailField(verbose_name="Correo Electrónico")
    telefono = models.CharField(max_length=20, verbose_name="Teléfono")
    articulacion = models.CharField(max_length=200, verbose_name="Articulación")
    cantidad = models.IntegerField(verbose_name="Cantidad")
    fecha = models.DateField(verbose_name="Fecha")
    hora = models.TimeField(verbose_name="Hora")
    
    # Campos adicionales 
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Actualización")
    
    class Meta:
        verbose_name = "Visita Externa"
        verbose_name_plural = "Visitas Externas"
        ordering = ['-fecha', '-hora']  
    
    def __str__(self):
        return f"{self.nombre} - {self.fecha}"