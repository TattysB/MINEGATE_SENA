from django.contrib import admin
from .models import PreguntaFrecuente


@admin.register(PreguntaFrecuente)
class PreguntaFrecuenteAdmin(admin.ModelAdmin):
	list_display = ("pregunta", "activa", "prioridad", "actualizado_en")
	list_filter = ("activa",)
	search_fields = ("pregunta", "respuesta", "palabras_clave")
