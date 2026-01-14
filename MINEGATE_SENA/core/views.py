from django.shortcuts import render

# Create your views here.

def index (request):
    return render (request, 'core/index.html')


def panel_administrativo (request):
    return render (request, 'core/panel_administrativo.html')   