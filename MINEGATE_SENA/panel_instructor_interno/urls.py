from django.urls import path
from . import views

app_name = "panel_instructor_interno"

urlpatterns = [
    # Panel principal
    path("", views.panel_instructor_interno, name="panel"),
    # Módulo: Reservar visita interna
    path("reservar/", views.reservar_visita_interna, name="reservar_visita"),
    path("mis-visitas/<int:pk>/", views.detalle_visita_interna, name="detalle_visita"),
    # Módulo: Gestionar Programas
    path("programas/", views.gestionar_programas, name="gestionar_programas"),
    path("programas/crear/", views.crear_programa, name="crear_programa"),
    path("programas/<int:pk>/editar/", views.editar_programa, name="editar_programa"),
    path(
        "programas/<int:pk>/eliminar/",
        views.eliminar_programa,
        name="eliminar_programa",
    ),
    # Módulo: Gestionar Fichas
    path("fichas/", views.gestionar_fichas, name="gestionar_fichas"),
    path("fichas/crear/", views.crear_ficha, name="crear_ficha"),
    path("fichas/<int:pk>/editar/", views.editar_ficha, name="editar_ficha"),
    path("fichas/<int:pk>/eliminar/", views.eliminar_ficha, name="eliminar_ficha"),
    # Módulo: Gestionar Aprendices por Ficha
    path(
        "aprendices/", views.listar_fichas_aprendices, name="listar_fichas_aprendices"
    ),
    path(
        "aprendices/<int:pk>/",
        views.detalle_aprendices_ficha,
        name="detalle_aprendices_ficha",
    ),
    path(
        "aprendices/crear/<int:ficha_id>/", views.crear_aprendiz, name="crear_aprendiz"
    ),
    path("aprendices/<int:pk>/editar/", views.editar_aprendiz, name="editar_aprendiz"),
    path(
        "aprendices/<int:pk>/eliminar/",
        views.eliminar_aprendiz,
        name="eliminar_aprendiz",
    ),
    path(
        "aprendices/<int:aprendiz_id>/ver-doc/<str:campo>/",
        views.ver_documento_aprendiz_inline,
        name="ver_documento_aprendiz_inline",
    ),
    # Módulo: Integración con Visitas - Aprendices
    path(
        "api/ficha/<int:ficha_id>/aprendices/",
        views.obtener_aprendices_ficha_json,
        name="api_aprendices_ficha",
    ),
    path(
        "visita/<int:visita_id>/registrar-aprendices/",
        views.registrar_aprendices_visita,
        name="registrar_aprendices_visita",
    ),
    path(
        "visita/<int:visita_id>/asistente/<int:asistente_id>/eliminar/<str:tipo>/",
        views.eliminar_asistente_visita,
        name="eliminar_asistente_visita",
    ),
]
