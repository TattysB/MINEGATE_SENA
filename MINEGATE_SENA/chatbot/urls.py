from django.urls import path

from . import views

app_name = "chatbot"

urlpatterns = [
    path("responder/", views.responder_chatbot, name="responder"),
]
