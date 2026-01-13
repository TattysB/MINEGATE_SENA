from django.http import HttpResponse
from django.template import loader
from django.shortcuts import redirect
from .models import VisitaInterna
from .forms import VisitaInternaForm

def visita_interna(request):
  visitas = VisitaInterna.objects.all().values()
  
  # Filtrar por nombre
  nombre = request.GET.get('nombre', '')
  if nombre:
    visitas = visitas.filter(nombre__icontains=nombre)
  
  # Filtrar por ID
  visita_id = request.GET.get('id', '')
  if visita_id:
    visitas = visitas.filter(id=visita_id)
  
  # Filtrar por estado
  estado = request.GET.get('estado', '')
  if estado:
    visitas = visitas.filter(estado=estado)
  
  template = loader.get_template('lista_visitas_internas.html')
  context = {
    'visitas': visitas,
  }
  return HttpResponse(template.render(context, request))

# Vista para crear una nueva visita interna
def crear_visita(request):
  if request.method == 'POST':
    form = VisitaInternaForm(request.POST)
    if form.is_valid():
      form.save()
      return redirect('visita_interna')
  else:
    form = VisitaInternaForm()
  
  template = loader.get_template('crear_visita_interna.html')
  context = {
    'form': form,
  }
  return HttpResponse(template.render(context, request))

# Vista para editar una visita interna
def editar_visita(request, id):
  visita = VisitaInterna.objects.get(id=id)
  if request.method == 'POST':
    form = VisitaInternaForm(request.POST, instance=visita)
    if form.is_valid():
      form.save()
      return redirect('visita_interna')
  else:
    form = VisitaInternaForm(instance=visita)
  
  template = loader.get_template('editar_visita_interna.html')
  context = {
    'form': form,
    'visita': visita,
  }
  return HttpResponse(template.render(context, request))

# Vista para ver los detalles de una visita interna
def details(request, id):
  visita = VisitaInterna.objects.get(id=id)
  template = loader.get_template('detalle_visita_interna.html')
  context = {
    'visita': visita,
  }
  return HttpResponse(template.render(context, request))

# Vista para eliminar una visita interna
def eliminar_visita(request, id):
  visita = VisitaInterna.objects.get(id=id)
  if request.method == 'POST':
    visita.delete()
    return redirect('visita_interna')
  
  template = loader.get_template('eliminar_visita_interna.html')
  context = {
    'visita': visita,
  }
  return HttpResponse(template.render(context, request))
