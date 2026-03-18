from django.contrib import admin
from .models import Availability, ReservaHorario


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ('date', 'time', 'end_time', 'created_at')
    list_filter = ('date',)
    ordering = ('-date', 'time')


@admin.register(ReservaHorario)
class ReservaHorarioAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'hora_inicio', 'hora_fin', 'estado', 'get_tipo_visita', 'created_at')
    list_filter = ('estado', 'fecha')
    ordering = ('-fecha', 'hora_inicio')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_tipo_visita(self, obj):
        if obj.visita_interna:
            return f"Interna #{obj.visita_interna.id}"
        elif obj.visita_externa:
            return f"Externa #{obj.visita_externa.id}"
        return "-"
    get_tipo_visita.short_description = "Visita"
