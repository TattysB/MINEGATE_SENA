from django.http import HttpResponse
from django.template import loader
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from .models import VisitaInterna
from .forms import VisitaInternaForm

def visita_interna(request):
  visitas = VisitaInterna.objects.all()

  nombre_programa = request.GET.get('nombre_programa', '')
  if nombre_programa:
    visitas = visitas.filter(nombre_programa__icontains=nombre_programa)

  responsable = request.GET.get('responsable', '')
  if responsable:
    visitas = visitas.filter(responsable__icontains=responsable)

  numero_ficha = request.GET.get('numero_ficha', '')
  if numero_ficha:
    visitas = visitas.filter(numero_ficha=numero_ficha)

  documento_responsable = request.GET.get('documento_responsable', '')
  if documento_responsable:
    visitas = visitas.filter(documento_responsable__icontains=documento_responsable)
  
  template = loader.get_template('lista_visitas_internas.html')
  context = {
    'visitas': visitas,
  }
  return HttpResponse(template.render(context, request))

def crear_visita(request):
  if not request.session.get('responsable_autenticado'):
    return redirect('panel_visitante:login_responsable')
  
  correo_responsable = request.session.get('responsable_correo')
  documento_responsable = request.session.get('responsable_documento')
  
  if request.method == 'POST':
    form = VisitaInternaForm(request.POST)
    if form.is_valid():
      visita = form.save(commit=False)
      visita.correo_responsable = correo_responsable
      visita.documento_responsable = documento_responsable
      visita.estado = 'enviada_coordinacion'  # Primera revisión por coordinador
      visita.save()
      messages.success(request, '✅ Su solicitud de visita ha sido enviada y está pendiente de revisión por coordinación.')
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

def details(request, id):
  visita = VisitaInterna.objects.get(id=id)
  template = loader.get_template('detalle_visita_interna.html')
  context = {
    'visita': visita,
  }
  return HttpResponse(template.render(context, request))

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
