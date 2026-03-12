from django.urls import path
from . import views

app_name = "documentos"

urlpatterns = [
    # Registro público con token
    path(
        "registro/interna/<str:token>/",
        views.registro_publico_asistentes,
        {"tipo": "interna"},
        name="registro_publico_interna",
    ),
    path(
        "registro/externa/<str:token>/",
        views.registro_publico_asistentes,
        {"tipo": "externa"},
        name="registro_publico_externa",
    ),
    # Eliminar asistente desde enlace público
    path(
        "eliminar/interna/<str:token>/<int:asistente_id>/",
        views.eliminar_asistente_publico,
        {"tipo": "interna"},
        name="eliminar_asistente_publico_interna",
    ),
    path(
        "eliminar/externa/<str:token>/<int:asistente_id>/",
        views.eliminar_asistente_publico,
        {"tipo": "externa"},
        name="eliminar_asistente_publico_externa",
    ),
    path(
        "actualizar/interna/<str:token>/<int:asistente_id>/",
        views.actualizar_asistente_publico,
        {"tipo": "interna"},
        name="actualizar_asistente_publico_interna",
    ),
    path(
        "actualizar/externa/<str:token>/<int:asistente_id>/",
        views.actualizar_asistente_publico,
        {"tipo": "externa"},
        name="actualizar_asistente_publico_externa",
    ),
    # API para gestión de documentos (panel admin)
    path("api/listar/", views.listar_documentos_api, name="api_listar_documentos"),
    path(
        "api/categorias-faltantes/",
        views.categorias_faltantes_api,
        name="api_categorias_faltantes",
    ),
    path("api/subir/", views.subir_documentos_api, name="api_subir_documentos"),
    path(
        "api/eliminar/<int:documento_id>/",
        views.eliminar_documento_api,
        name="api_eliminar_documento",
    ),
    # Descargar/servir documento
    path(
        "descargar/<int:documento_id>/",
        views.descargar_documento,
        name="descargar_documento",
    ),
    path(
        "ver/<int:documento_id>/",
        views.ver_documento_inline,
        name="ver_documento_inline",
    ),
    path(
        "descargar-publico/<int:documento_id>/",
        views.descargar_documento_publico,
        name="descargar_documento_publico",
    ),
    # Documentos subidos por asistentes
    path(
        "ver-asistente/<int:documento_subido_id>/",
        views.ver_documento_asistente_inline,
        name="ver_documento_asistente_inline",
    ),
    path(
        "descargar-asistente/<int:documento_subido_id>/",
        views.descargar_documento_asistente,
        name="descargar_documento_asistente",
    ),
    path(
        "api/revisar-asistente/<int:documento_subido_id>/",
        views.revisar_documento_asistente_api,
        name="api_revisar_documento_asistente",
    ),
    path(
        "enviar-solicitud/<str:token>/<str:tipo>/",
        views.enviar_solicitud_final,
        name="enviar_solicitud_final",
    ),
]
