from django.contrib import admin
from .models import Programa, Ficha, Aprendiz


@admin.register(Programa)
class ProgramaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo', 'creado_por', 'fecha_creacion']
    list_filter = ['activo']
    search_fields = ['nombre']


@admin.register(Ficha)
class FichaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'programa', 'jornada', 'cantidad_aprendices', 'activa']
    list_filter = ['activa', 'jornada', 'programa']


@admin.register(Aprendiz)
class AprendizAdmin(admin.ModelAdmin):
    list_display = ['get_nombre_completo', 'numero_documento', 'correo', 'ficha', 'estado', 'fecha_creacion']
    list_filter = ['estado', 'ficha__programa', 'estado']
    search_fields = ['nombre', 'apellido', 'numero_documento', 'correo']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('ficha', 'nombre', 'apellido', 'tipo_documento', 'numero_documento')
        }),
        ('Información de Contacto', {
            'fields': ('correo', 'telefono')
        }),
        ('Estado', {
            'fields': ('estado',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def get_nombre_completo(self, obj):
        return obj.get_nombre_completo()
    get_nombre_completo.short_description = 'Nombre Completo'

    search_fields = ['numero', 'programa__nombre']
