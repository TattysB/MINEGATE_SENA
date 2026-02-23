from django.urls import path
from . import views

app_name = 'panel_instructor_interno'

urlpatterns = [
    # Panel principal
    path('', views.panel_instructor_interno, name='panel'),

    # Módulo: Reservar visita interna
    path('reservar/', views.reservar_visita_interna, name='reservar_visita'),
    path('mis-visitas/', views.mis_visitas_internas, name='mis_visitas'),
    path('mis-visitas/<int:pk>/', views.detalle_visita_interna, name='detalle_visita'),

    # Módulo: Gestionar Programas
    path('programas/', views.gestionar_programas, name='gestionar_programas'),
    path('programas/crear/', views.crear_programa, name='crear_programa'),
    path('programas/<int:pk>/editar/', views.editar_programa, name='editar_programa'),
    path('programas/<int:pk>/eliminar/', views.eliminar_programa, name='eliminar_programa'),

    # Módulo: Gestionar Fichas
    path('fichas/', views.gestionar_fichas, name='gestionar_fichas'),
    path('fichas/crear/', views.crear_ficha, name='crear_ficha'),
    path('fichas/<int:pk>/editar/', views.editar_ficha, name='editar_ficha'),
    path('fichas/<int:pk>/eliminar/', views.eliminar_ficha, name='eliminar_ficha'),
]
