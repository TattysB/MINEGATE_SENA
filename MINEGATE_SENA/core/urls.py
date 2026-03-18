from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.index, name="index"),
    path(
        "panel_administrativo/gestion_pagina_informativa/galeria-json/",
        views.api_galeria_informativa,
        name="api_galeria_informativa",
    ),
    path(
        "panel_administrativo/", views.panel_administrativo, name="panel_administrativo"
    ),
    path(
        "panel_administrativo/<slug:seccion>/",
        views.panel_administrativo_seccion,
        name="panel_administrativo_seccion",
    ),
    path("gestionar_permisos/", views.gestionar_permisos, name="gestionar_permisos"),
    path(
        "aprobar_usuario/<int:usuario_id>/",
        views.aprobar_usuario,
        name="aprobar_usuario",
    ),
    path(
        "rechazar_usuario/<int:usuario_id>/",
        views.rechazar_usuario,
        name="rechazar_usuario",
    ),
    path("protocolos/", views.protocolos, name="protocolos"),
    path("visitas/", views.visitas, name="visitas"),
]
