from django.db import models
from django.conf import settings


class AprobacionRegistro(models.Model):
	VISITA_TIPOS = (("interna", "Interna"), ("externa", "Externa"))

	visita_id = models.IntegerField()
	visita_tipo = models.CharField(max_length=10, choices=VISITA_TIPOS)
	responsable = models.CharField(max_length=255)
	institucion = models.CharField(max_length=255, blank=True, null=True)
	correo = models.CharField(max_length=255, blank=True, null=True)
	cantidad = models.IntegerField(blank=True, null=True)
	aprobado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
	fecha_aprobacion = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-fecha_aprobacion"]

	def __str__(self):
		return f"{self.get_visita_tipo_display()} #{self.visita_id} - {self.responsable} ({self.fecha_aprobacion:%Y-%m-%d %H:%M})"

# Create your models here.
