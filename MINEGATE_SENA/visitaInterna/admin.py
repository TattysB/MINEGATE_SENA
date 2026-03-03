from django.contrib import admin
from .models import VisitaInterna, AsistenteVisitaInterna, HistorialAccionVisitaInterna


@admin.register(VisitaInterna)
class VisitaInternaAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre_programa', 'responsable', 'estado', 'fecha_solicitud']
    list_filter = ['estado', 'fecha_solicitud']
    search_fields = ['nombre_programa', 'responsable', 'correo_responsable']


@admin.register(AsistenteVisitaInterna)
class AsistenteVisitaInternaAdmin(admin.ModelAdmin):
    list_display = ['nombre_completo', 'visita', 'numero_documento', 'estado', 'fecha_registro']
    list_filter = ['estado', 'visita']
    search_fields = ['nombre_completo', 'numero_documento']


@admin.register(HistorialAccionVisitaInterna)
class HistorialAccionVisitaInternaAdmin(admin.ModelAdmin):
    list_display = ['visita', 'tipo_accion', 'usuario', 'fecha_hora']
    list_filter = ['tipo_accion', 'fecha_hora']
