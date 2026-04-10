from django.db import models


class PreguntaFrecuente(models.Model):
	pregunta = models.CharField(max_length=280, unique=True)
	respuesta = models.TextField()
	palabras_clave = models.CharField(max_length=280, blank=True)
	activa = models.BooleanField(default=True)
	prioridad = models.PositiveSmallIntegerField(default=5)
	creado_en = models.DateTimeField(auto_now_add=True)
	actualizado_en = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ("-prioridad", "pregunta")
		verbose_name = "Pregunta frecuente"
		verbose_name_plural = "Preguntas frecuentes"

	def __str__(self):
		return self.pregunta
