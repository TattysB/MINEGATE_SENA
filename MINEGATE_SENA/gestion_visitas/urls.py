from django.urls import path
from . import views

app_name = "gestion_visitas"

urlpatterns = [
    # Endpoints de gestión de visitas en el panel administrativo
    path("visitas/", views.api_listar_visitas, name="api_listar_visitas"),
    path(
        "visitas/<str:tipo>/<int:visita_id>/",
        views.api_detalle_visita,
        name="api_detalle_visita",
    ),
    path(
        "visitas/<str:tipo>/<int:visita_id>/<str:accion>/",
        views.api_accion_visita,
        name="api_accion_visita",
    ),
    path(
        "asistentes/<str:tipo>/<int:asistente_id>/<str:accion>/",
        views.api_revisar_documento_asistente,
        name="api_revisar_documento_asistente",
    ),
    # Nuevos endpoints requeridos por el panel
    path(
        "visitas-aprobadas/",
        views.api_visitas_aprobadas,
        name="api_visitas_aprobadas",
    ),
    path(
        "documentos-revision/",
        views.api_documentos_revision,
        name="api_documentos_revision",
    ),
    # Compatibilidad temporal: soporta URLs antiguas con prefijo /api/
    path("api/visitas/", views.api_listar_visitas, name="api_listar_visitas_legacy"),
    path(
        "api/visitas/<str:tipo>/<int:visita_id>/",
        views.api_detalle_visita,
        name="api_detalle_visita_legacy",
    ),
    path(
        "api/visitas/<str:tipo>/<int:visita_id>/<str:accion>/",
        views.api_accion_visita,
        name="api_accion_visita_legacy",
    ),
    path(
        "api/asistentes/<str:tipo>/<int:asistente_id>/<str:accion>/",
        views.api_revisar_documento_asistente,
        name="api_revisar_documento_asistente_legacy",
    ),
    path(
        "api/visitas-aprobadas/",
        views.api_visitas_aprobadas,
        name="api_visitas_aprobadas_legacy",
    ),
    path(
        "api/documentos-revision/",
        views.api_documentos_revision,
        name="api_documentos_revision_legacy",
    ),
]
