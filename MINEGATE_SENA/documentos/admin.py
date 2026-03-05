from django.contrib import admin
from .models import Documento


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "categoria",
        "subido_por",
        "fecha_subida",
        "tamaño_legible",
    )
    list_filter = ("categoria", "fecha_subida")
    search_fields = ("titulo", "descripcion")
