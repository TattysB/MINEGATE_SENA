from django.contrib import admin
from .models import Programa, Ficha


@admin.register(Programa)
class ProgramaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo', 'creado_por', 'fecha_creacion']
    list_filter = ['activo']
    search_fields = ['nombre']


@admin.register(Ficha)
class FichaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'programa', 'jornada', 'cantidad_aprendices', 'activa']
    list_filter = ['activa', 'jornada', 'programa']
    search_fields = ['numero', 'programa__nombre']
