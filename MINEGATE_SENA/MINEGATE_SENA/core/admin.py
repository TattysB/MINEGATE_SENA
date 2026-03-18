from django.contrib import admin
from .models import (
	ContenidoPaginaInformativa,
	ElementoEncabezadoInformativo,
	ElementoGaleriaInformativa,
)


@admin.register(ContenidoPaginaInformativa)
class ContenidoPaginaInformativaAdmin(admin.ModelAdmin):
	list_display = ("titulo_principal", "actualizado_en")


@admin.register(ElementoGaleriaInformativa)
class ElementoGaleriaInformativaAdmin(admin.ModelAdmin):
	list_display = ("titulo", "tipo", "orden", "activo", "actualizado_en")
	list_filter = ("tipo", "activo")
	search_fields = ("titulo", "descripcion")


@admin.register(ElementoEncabezadoInformativo)
class ElementoEncabezadoInformativoAdmin(admin.ModelAdmin):
	list_display = ("titulo", "orden", "activo", "actualizado_en")
	list_filter = ("activo",)
	search_fields = ("titulo", "texto")
