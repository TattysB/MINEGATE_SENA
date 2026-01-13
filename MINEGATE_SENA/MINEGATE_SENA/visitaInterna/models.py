from django.db import models

class VisitaInterna(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('realizada', 'Realizada'),
        ('cancelada', 'Cancelada'),
    ]
    
    id = models.AutoField(primary_key=True, verbose_name="ID")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    responsable = models.CharField(max_length=200, verbose_name="Responsable")
    telefono = models.CharField(max_length=20, verbose_name="Teléfono")
    cantidad = models.IntegerField(verbose_name="Cantidad")
    fecha = models.DateField(verbose_name="Fecha")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', verbose_name="Estado")
    
    # Campos adicionales útiles
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Actualización")
    
    class Meta:
        verbose_name = "Visita Interna"
        verbose_name_plural = "Visitas Internas"
        ordering = ['-fecha'] 
    
    def __str__(self):
        return f"{self.nombre} - {self.fecha}"
