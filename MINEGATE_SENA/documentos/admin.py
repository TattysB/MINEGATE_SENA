from django.contrib import admin
from .models import Documento, DocumentoSubidoAsistente, DocumentoSubidoAprendiz


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


@admin.register(DocumentoSubidoAsistente)
class DocumentoSubidoAsistenteAdmin(admin.ModelAdmin):
    """Admin para documentos subidos por asistentes en visitas"""
    list_display = (
        "get_asistente_nombre",
        "documento_requerido",
        "fecha_subida",
        "nombre_archivo"
    )
    list_filter = ("fecha_subida", "documento_requerido__categoria")
    search_fields = (
        "asistente_interna__nombre",
        "asistente_interna__apellido",
        "asistente_externa__nombre",
        "asistente_externa__apellido",
        "documento_requerido__titulo"
    )
    readonly_fields = ("fecha_subida", "get_archivo_preview")
    fields = (
        "documento_requerido",
        "asistente_interna",
        "asistente_externa",
        "archivo",
        "get_archivo_preview",
        "fecha_subida"
    )
    
    def get_asistente_nombre(self, obj):
        if obj.asistente_interna:
            return f"{obj.asistente_interna.nombre} {obj.asistente_interna.apellido} (Interna)"
        elif obj.asistente_externa:
            return f"{obj.asistente_externa.nombre} {obj.asistente_externa.apellido} (Externa)"
        return "N/A"
    get_asistente_nombre.short_description = "Asistente"
    
    def get_archivo_preview(self, obj):
        if obj.archivo:
            from django.utils.html import format_html
            return format_html(
                '<a href="{}" target="_blank">Ver archivo</a>',
                obj.archivo.url
            )
        return "No hay archivo"
    get_archivo_preview.short_description = "Vista Previa"


@admin.register(DocumentoSubidoAprendiz)
class DocumentoSubidoAprendizAdmin(admin.ModelAdmin):
    """Admin para documentos subidos por aprendices para revisión admin"""
    list_display = (
        "aprendiz",
        "documento_requerido",
        "fecha_subida",
        "nombre_archivo"
    )
    list_filter = ("fecha_subida", "documento_requerido__categoria")
    search_fields = (
        "aprendiz__nombre",
        "aprendiz__apellido",
        "aprendiz__numero_documento",
        "documento_requerido__titulo"
    )
    readonly_fields = ("fecha_subida", "get_archivo_preview")
    fields = (
        "aprendiz",
        "documento_requerido",
        "archivo",
        "get_archivo_preview",
        "fecha_subida"
    )
    
    def get_archivo_preview(self, obj):
        if obj.archivo:
            from django.utils.html import format_html
            return format_html(
                '<a href="{}" target="_blank">Ver archivo</a>',
                obj.archivo.url
            )
        return "No hay archivo"
    get_archivo_preview.short_description = "Vista Previa"
