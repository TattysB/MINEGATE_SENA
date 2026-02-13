from django.urls import path
from . import views

app_name = 'notificaciones'

urlpatterns = [
    path('', views.center, name='center'),
    path('modal/', views.modal, name='modal'),
    path('count/', views.unread_count, name='count'),
    path('detail/<int:pk>/', views.detail, name='detail'),
    path('mark_read/<int:pk>/', views.mark_read, name='mark_read'),
    path('delete/<int:pk>/', views.delete_notification, name='delete'),
]
