from django.http import HttpResponse
from django.template import loader
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from .models import VisitaInterna
from .forms import VisitaInternaForm

def visita_interna(request):
  visitas = VisitaInterna.objects.all()

  # Filtrar por nombre de programa
  nombre_programa = request.GET.get('nombre_programa', '')
  if nombre_programa:
    visitas = visitas.filter(nombre_programa__icontains=nombre_programa)

  # Filtrar por responsable
  responsable = request.GET.get('responsable', '')
  if responsable:
    visitas = visitas.filter(responsable__icontains=responsable)

  # Filtrar por número de ficha
  numero_ficha = request.GET.get('numero_ficha', '')
  if numero_ficha:
    visitas = visitas.filter(numero_ficha=numero_ficha)

  # Filtrar por documento del responsable
  documento_responsable = request.GET.get('documento_responsable', '')
  if documento_responsable:
    visitas = visitas.filter(documento_responsable__icontains=documento_responsable)
  
  template = loader.get_template('lista_visitas_internas.html')
  context = {
    'visitas': visitas,
  }
  return HttpResponse(template.render(context, request))

# Vista para crear una nueva visita interna
def crear_visita(request):
  # Verificar si el usuario está autenticado desde la sesión
  if not request.session.get('responsable_autenticado'):
    return redirect('panel_visitante:login_responsable')
  
  correo_responsable = request.session.get('responsable_correo')
  documento_responsable = request.session.get('responsable_documento')
  
  if request.method == 'POST':
    form = VisitaInternaForm(request.POST)
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
      print(f"Errores del formulario: {form.errors}")
  else:
    form = VisitaInternaForm()
    form.fields['documento_responsable'].initial = documento_responsable
    form.fields['correo_responsable'].initial = correo_responsable
  
  template = loader.get_template('crear_visita_interna.html')
  context = {
    'form': form,
    'correo_responsable': correo_responsable,
    'documento_responsable': documento_responsable,
  }
  return HttpResponse(template.render(context, request))

# Vista para editar una visita interna
def editar_visita(request, id):
  visita = VisitaInterna.objects.get(id=id)
  if request.method == 'POST':
    form = VisitaInternaForm(request.POST, instance=visita)
    if form.is_valid():
      form.save()
      return redirect(reverse('visitaInterna:visita_interna'))
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
    return redirect(reverse('visitaInterna:visita_interna'))
  
  template = loader.get_template('eliminar_visita_interna.html')
  context = {
    'visita': visita,
  }
  return HttpResponse(template.render(context, request))
