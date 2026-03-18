from django.contrib import admin
from .models import VisitaExterna, AsistenteVisitaExterna, HistorialAccionVisitaExterna


@admin.register(VisitaExterna)
class VisitaExternaAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'nombre_responsable', 'estado', 'fecha_solicitud']
    list_filter = ['estado', 'fecha_solicitud']
    search_fields = ['nombre', 'nombre_responsable', 'correo_responsable']


@admin.register(AsistenteVisitaExterna)
class AsistenteVisitaExternaAdmin(admin.ModelAdmin):
    list_display = ['nombre_completo', 'visita', 'numero_documento', 'estado', 'fecha_registro']
    list_filter = ['estado', 'visita']
    search_fields = ['nombre_completo', 'numero_documento']


@admin.register(HistorialAccionVisitaExterna)
class HistorialAccionVisitaExternaAdmin(admin.ModelAdmin):
    list_display = ['visita', 'tipo_accion', 'usuario', 'fecha_hora']
    list_filter = ['tipo_accion', 'fecha_hora']
