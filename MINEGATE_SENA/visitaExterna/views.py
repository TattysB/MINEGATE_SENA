from django.http import HttpResponse
from django.template import loader
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from .models import VisitaExterna
from .forms import VisitaExternaForm

def visita_externa(request):
  visitas = VisitaExterna.objects.all()
  
  # Filtrar por nombre de la institución
  nombre_institucion = request.GET.get('nombre_institucion', '')
  if nombre_institucion:
    visitas = visitas.filter(nombre__icontains=nombre_institucion)
  
  # Filtrar por nombre del responsable
  nombre_responsable = request.GET.get('nombre_responsable', '')
  if nombre_responsable:
    visitas = visitas.filter(nombre_responsable__icontains=nombre_responsable)

  # Filtrar por documento del responsable
  documento_responsable = request.GET.get('documento_responsable', '')
  if documento_responsable:
    visitas = visitas.filter(documento_responsable__icontains=documento_responsable)
  
  template = loader.get_template('lista_visitas.html')
  context = {
    'visitas': visitas,
  }
  return HttpResponse(template.render(context, request))

# Vista para crear una nueva visita externa
def crear_visita(request):
  # Verificar si el usuario está autenticado desde la sesión
  if not request.session.get('responsable_autenticado'):
    return redirect('panel_visitante:login_responsable')
  
  correo_responsable = request.session.get('responsable_correo')
  documento_responsable = request.session.get('responsable_documento')
  
  if request.method == 'POST':
    form = VisitaExternaForm(request.POST)
    if form.is_valid():
      # Crear la visita con estado pendiente (revisión admin)
      visita = form.save(commit=False)
      # Usar los datos de la sesión para correo y documento
      visita.correo_responsable = correo_responsable
      visita.documento_responsable = documento_responsable
      visita.estado = 'pendiente'  # Pendiente de revisión por administrador
      visita.save()
      messages.success(request, '✅ Su solicitud de visita ha sido enviada y está pendiente de revisión por el administrador.')
      return redirect('panel_visitante:panel_responsable')
  else:
    form = VisitaExternaForm()
    form.fields['documento_responsable'].initial = documento_responsable
    form.fields['correo_responsable'].initial = correo_responsable
  
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
      return redirect(reverse('visitaExterna:visita_externa'))
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
    return redirect(reverse('visitaExterna:visita_externa'))
  
  template = loader.get_template('eliminar_visita.html')
  context = {
    'visita': visita,
  }
  return HttpResponse(template.render(context, request))