from django.urls import path
from . import views

app_name = 'notificaciones'

urlpatterns = [
    path('', views.center, name='center'),
    path('count/', views.unread_count, name='count'),
    path('mark_read/<int:pk>/', views.mark_read, name='mark_read'),
    path('delete/<int:pk>/', views.delete_notification, name='delete'),
]
