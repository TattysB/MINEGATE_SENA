from django.urls import path
from . import views

app_name = "usuarios"

urlpatterns = [
    # Autenticación
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("bienvenida/", views.bienvenida_view, name="bienvenida"),
    # Recuperación de contraseña
    path(
        "recuperar_contrasena/",
        views.password_reset_request_view,
        name="solicitar_recuperacion",
    ),
    path(
        "recuperar_contrasena/correo_enviado/",
        views.password_reset_done_view,
        name="correo_enviado",
    ),
    path(
        "recuperar_contrasena/<uidb64>/<token>/",
        views.password_reset_confirm_view,
        name="restablecer_contraseña",
    ),
    path(
        "recuperar_contrasena/completado/",
        views.password_reset_complete_view,
        name="contraseña_actualizada",
    ),
    path("recuperar_contraseña/", views.password_reset_request_view),
    path("recuperar_contraseña/correo_enviado/", views.password_reset_done_view),
    path("recuperar_contraseña/<uidb64>/<token>/", views.password_reset_confirm_view),
    path("recuperar_contraseña/completado/", views.password_reset_complete_view),
    path("recuperar-contraseña/", views.password_reset_request_view),
    path("recuperar-contraseña/correo-enviado/", views.password_reset_done_view),
    path("recuperar-contraseña/<uidb64>/<token>/", views.password_reset_confirm_view),
    path("recuperar-contraseña/completado/", views.password_reset_complete_view),
    # Perfil de usuario
    path("perfil/", views.perfil_view, name="perfil"),
    path(
        "configuracion-perfil/",
        views.configuracion_perfil_view,
        name="configuracion_perfil",
    ),
    path(
        "cambiar-contraseña/",
        views.cambiar_contraseña_view,
        name="cambiar_contraseña",
    ),
    # Perfil de administrador
    path("usuarios/", views.lista_usuarios_view, name="lista_usuario"),
    path("usuarios/crear/", views.crear_usuario_view, name="crear_usuario"),
    path(
        "usuarios/<int:user_id>/editar/",
        views.editar_usuario_view,
        name="editar_usuario",
    ),
    path(
        "usuarios/<int:user_id>/eliminar/",
        views.eliminar_usuario_view,
        name="eliminar_usuario",
    ),
    path("perfil/", views.perfil_view, name="perfil"),
    # Panel de administración
    path("usuarios/", views.lista_usuarios_view, name="lista_usuario"),
    path("usuarios/crear/", views.crear_usuario_view, name="crear_usuario"),
    path(
        "usuarios/<int:user_id>/editar/",
        views.editar_usuario_view,
        name="editar_usuario",
    ),
    path(
        "usuarios/<int:user_id>/eliminar/",
        views.eliminar_usuario_view,
        name="eliminar_usuario",
    ),
    # Gestión de permisos
    path(
        "gestionar-permisos/", views.gestionar_permisos_view, name="gestionar_permisos"
    ),
    path(
        "gestionar-permisos/ajax/",
        views.gestionar_permisos_ajax_view,
        name="gestionar_permisos_ajax",
    ),
    path(
        "eliminar-usuario-permisos/<int:usuario_id>/",
        views.eliminar_usuario_permisos_view,
        name="eliminar_usuario_permisos",
    ),
    # Nuevas rutas de gestión de permisos
    path(
        "gestionar-permisos/crear/",
        views.crear_usuario_permisos_view,
        name="crear_usuario_permisos",
    ),
    path(
        "gestionar-permisos/detalle/<int:usuario_id>/",
        views.detalle_usuario_permisos_view,
        name="detalle_usuario_permisos",
    ),
    path(
        "gestionar-permisos/editar-ajax/<int:usuario_id>/",
        views.editar_usuario_ajax_view,
        name="editar_usuario_ajax",
    ),
    path(
        "gestionar-permisos/toggle-estado/<int:usuario_id>/",
        views.toggle_estado_usuario_view,
        name="toggle_estado_usuario",
    ),
]
