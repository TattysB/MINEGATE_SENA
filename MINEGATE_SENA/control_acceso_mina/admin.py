from django.contrib import admin
from .models import RegistroAccesoMina


@admin.register(RegistroAccesoMina)
class RegistroAccesoMinaAdmin(admin.ModelAdmin):
    list_display = ['nombre_completo', 'documento', 'categoria', 'tipo', 'fecha_hora', 'registrado_por']
    list_filter = ['tipo', 'fecha_hora', 'categoria']
    search_fields = ['documento', 'nombre_completo', 'categoria']
    readonly_fields = ['documento', 'nombre_completo', 'categoria', 'tipo', 'fecha_hora', 'registrado_por']
    ordering = ['-fecha_hora']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
