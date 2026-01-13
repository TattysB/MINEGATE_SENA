from django.http import HttpResponse
from django.template import loader
from django.shortcuts import redirect
from .models import VisitaExterna
from .forms import VisitaExternaForm

def visita_externa(request):
  visitas = VisitaExterna.objects.all().values()
  
  # Filtrar por nombre
  nombre = request.GET.get('nombre', '')
  if nombre:
    visitas = visitas.filter(nombre__icontains=nombre)
  
  # Filtrar por ID
  visita_id = request.GET.get('id', '')
  if visita_id:
    visitas = visitas.filter(id=visita_id)
  
  template = loader.get_template('lista_visitas.html')
  context = {
    'visitas': visitas,
  }
  return HttpResponse(template.render(context, request))

 # Vista para crear una nueva visita externa
def crear_visita(request):
  if request.method == 'POST':
    form = VisitaExternaForm(request.POST)
    if form.is_valid():
      form.save()
      return redirect('visita_externa')
  else:
    form = VisitaExternaForm()
  
  template = loader.get_template('crear_visita.html')
  context = {
    'form': form,
  }
  return HttpResponse(template.render(context, request))

# Vista para editar una visita externa
def editar_visita(request, id):
  visita = VisitaExterna.objects.get(id=id)
  if request.method == 'POST':
    form = VisitaExternaForm(request.POST, instance=visita)
    if form.is_valid():
      form.save()
      return redirect('visita_externa')
  else:
    form = VisitaExternaForm(instance=visita)
  
  template = loader.get_template('editar_visita.html')
  context = {
    'form': form,
    'visita': visita,
  }
  return HttpResponse(template.render(context, request))

# Vista para ver los detalles de una visita externa
def details(request, id):
  mymember = VisitaExterna.objects.get(id=id)
  template = loader.get_template('detalle_visita.html')
  context = {
    'visita': mymember,
  }
  return HttpResponse(template.render(context, request))
  
# Vista para eliminar una visita externa
def eliminar_visita(request, id):
  visita = VisitaExterna.objects.get(id=id)
  if request.method == 'POST':
    visita.delete()
    return redirect('visita_externa')
  
  template = loader.get_template('eliminar_visita.html')
  context = {
    'visita': visita,
  }
  return HttpResponse(template.render(context, request))