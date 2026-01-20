from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('registro/', views.registro_view, name='registro'),
    path('logout/', views.logout_view, name='logout'),
    path('bienvenida/', views.bienvenida_view, name='bienvenida'),
    
    # Recuperación de contraseña
    path('recuperar-contraseña/', views.password_reset_request_view, name='solicitar_recuperacion'),
    path('recuperar-contraseña/correo-enviado/', views.password_reset_done_view, name='correo_enviado'),
    path('recuperar-contraseña/<uidb64>/<token>/', views.password_reset_confirm_view, name='restablecer_contraseña'),
    path('recuperar-contraseña/completado/', views.password_reset_complete_view, name='contraseña_actualizada'),
    
    # Perfil de usuario
    path('perfil/', views.perfil_view, name='perfil'),
    
    # Panel de administración
    path('usuarios/', views.lista_usuarios_view, name='lista_usuario'),
    path('usuarios/crear/', views.crear_usuario_view, name='crear_usuario'),
    path('usuarios/<int:user_id>/editar/', views.editar_usuario_view, name='editar_usuario'),
    path('usuarios/<int:user_id>/eliminar/', views.eliminar_usuario_view, name='eliminar_usuario'),
]
