"""
App: gestion_visitas
Gestión administrativa de visitas - APIs para el panel administrativo
"""
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

from visitaInterna.models import (
    VisitaInterna, 
    AsistenteVisitaInterna, 
    HistorialAccionVisitaInterna,
    RegistroEnvioCoordinacionInterna
)
from visitaExterna.models import (
    VisitaExterna, 
    AsistenteVisitaExterna,
    HistorialAccionVisitaExterna,
    RegistroEnvioCoordinacionExterna
)


@login_required(login_url='usuarios:login')
def api_listar_visitas(request):
    """API para listar visitas internas y externas"""
    tipo = request.GET.get('tipo', 'internas')
    estado = request.GET.get('estado', 'todos')
    buscar = request.GET.get('buscar', '')
    
    visitas_data = []
    
    if tipo == 'internas':
        visitas = VisitaInterna.objects.all().order_by('-fecha_solicitud', '-id')
        
        if estado != 'todos':
            visitas = visitas.filter(estado=estado)
        
        if buscar:
            visitas = visitas.filter(
                Q(responsable__icontains=buscar) |
                Q(nombre_programa__icontains=buscar) |
                Q(correo_responsable__icontains=buscar)
            )
        
        for v in visitas:
            visitas_data.append({
                'id': v.id,
                'tipo': 'interna',
                'tipo_display': 'Interna (SENA)',
                'responsable': v.responsable,
                'institucion': v.nombre_programa or 'N/A',
                'correo': v.correo_responsable,
                'telefono': v.telefono_responsable,
                'fecha_visita': v.fecha_solicitud.strftime('%d/%m/%Y') if v.fecha_solicitud else 'N/A',
                'cantidad': v.cantidad_aprendices,
                'estado': v.estado,
                'fecha_solicitud': v.fecha_solicitud.strftime('%d/%m/%Y %H:%M') if v.fecha_solicitud else 'N/A',
            })
        
        stats = {
            'pendientes': VisitaInterna.objects.filter(estado='pendiente').count(),
            'coordinacion': VisitaInterna.objects.filter(estado='enviada_coordinacion').count(),
            'aprobadas_inicial': VisitaInterna.objects.filter(estado='aprobada_inicial').count(),
            'documentos_enviados': VisitaInterna.objects.filter(estado='documentos_enviados').count(),
            'en_revision': VisitaInterna.objects.filter(estado='en_revision_documentos').count(),
            'confirmadas': VisitaInterna.objects.filter(estado='confirmada').count(),
            'rechazadas': VisitaInterna.objects.filter(estado='rechazada').count(),
        }
    else:
        visitas = VisitaExterna.objects.all().order_by('-fecha_solicitud', '-id')
        
        if estado != 'todos':
            visitas = visitas.filter(estado=estado)
        
        if buscar:
            visitas = visitas.filter(
                Q(nombre_responsable__icontains=buscar) |
                Q(nombre__icontains=buscar) |
                Q(correo_responsable__icontains=buscar)
            )
        
        for v in visitas:
            visitas_data.append({
                'id': v.id,
                'tipo': 'externa',
                'tipo_display': 'Externa (Institución)',
                'responsable': v.nombre_responsable,
                'institucion': v.nombre or 'N/A',
                'correo': v.correo_responsable,
                'telefono': v.telefono_responsable,
                'fecha_visita': v.fecha_solicitud.strftime('%d/%m/%Y') if v.fecha_solicitud else 'N/A',
                'cantidad': v.cantidad_visitantes,
                'estado': v.estado,
                'fecha_solicitud': v.fecha_solicitud.strftime('%d/%m/%Y %H:%M') if v.fecha_solicitud else 'N/A',
            })
        
        stats = {
            'pendientes': VisitaExterna.objects.filter(estado='pendiente').count(),
            'coordinacion': VisitaExterna.objects.filter(estado='enviada_coordinacion').count(),
            'aprobadas_inicial': VisitaExterna.objects.filter(estado='aprobada_inicial').count(),
            'documentos_enviados': VisitaExterna.objects.filter(estado='documentos_enviados').count(),
            'en_revision': VisitaExterna.objects.filter(estado='en_revision_documentos').count(),
            'confirmadas': VisitaExterna.objects.filter(estado='confirmada').count(),
            'rechazadas': VisitaExterna.objects.filter(estado='rechazada').count(),
        }
    
    return JsonResponse({
        'visitas': visitas_data,
        'stats': stats,
    })


@login_required(login_url='usuarios:login')
def api_detalle_visita(request, tipo, visita_id):
    """API para obtener detalle de una visita"""
    if tipo == 'interna':
        visita = get_object_or_404(VisitaInterna, pk=visita_id)
        asistentes = []
        for a in visita.asistentes.all():
            asistentes.append({
                'id': a.id,
                'nombre_completo': a.nombre_completo,
                'tipo_documento': a.tipo_documento,
                'numero_documento': a.numero_documento,
                'correo': a.correo,
                'telefono': a.telefono,
                'estado': a.estado,
                'documento_identidad': a.documento_identidad.url if a.documento_identidad else None,
                'documento_adicional': a.documento_adicional.url if a.documento_adicional else None,
                'observaciones_revision': a.observaciones_revision,
            })
        
        historial = list(HistorialAccionVisitaInterna.objects.filter(visita=visita).order_by('-fecha_hora').values(
            'tipo_accion', 'descripcion', 'fecha_hora', 'usuario__username'
        )[:10])
        
        data = {
            'id': visita.id,
            'tipo': 'interna',
            'responsable': visita.responsable,
            'correo': visita.correo_responsable,
            'telefono': visita.telefono_responsable,
            'programa': visita.nombre_programa,
            'ficha': visita.numero_ficha,
            'cantidad': visita.cantidad_aprendices,
            'fecha_visita': visita.fecha_solicitud.strftime('%d/%m/%Y') if visita.fecha_solicitud else 'N/A',
            'estado': visita.estado,
            'observaciones': visita.observaciones or '',
            'fecha_solicitud': visita.fecha_solicitud.strftime('%d/%m/%Y %H:%M') if visita.fecha_solicitud else 'N/A',
            'asistentes': asistentes,
            'asistentes_count': len(asistentes),
            'historial': historial,
        }
    else:
        visita = get_object_or_404(VisitaExterna, pk=visita_id)
        asistentes = []
        for a in visita.asistentes.all():
            asistentes.append({
                'id': a.id,
                'nombre_completo': a.nombre_completo,
                'tipo_documento': a.tipo_documento,
                'numero_documento': a.numero_documento,
                'correo': a.correo,
                'telefono': a.telefono,
                'estado': a.estado,
                'documento_identidad': a.documento_identidad.url if a.documento_identidad else None,
                'documento_adicional': a.documento_adicional.url if a.documento_adicional else None,
                'observaciones_revision': a.observaciones_revision,
            })
        
        historial = list(HistorialAccionVisitaExterna.objects.filter(visita=visita).order_by('-fecha_hora').values(
            'tipo_accion', 'descripcion', 'fecha_hora', 'usuario__username'
        )[:10])
        
        data = {
            'id': visita.id,
            'tipo': 'externa',
            'responsable': visita.nombre_responsable,
            'correo': visita.correo_responsable,
            'telefono': visita.telefono_responsable,
            'institucion': visita.nombre,
            'cantidad': visita.cantidad_visitantes,
            'fecha_visita': visita.fecha_solicitud.strftime('%d/%m/%Y') if visita.fecha_solicitud else 'N/A',
            'estado': visita.estado,
            'observaciones': visita.observacion or '',
            'fecha_solicitud': visita.fecha_solicitud.strftime('%d/%m/%Y %H:%M') if visita.fecha_solicitud else 'N/A',
            'asistentes': asistentes,
            'asistentes_count': len(asistentes),
            'historial': historial,
        }
    
    return JsonResponse(data)


@login_required(login_url='usuarios:login')
def api_accion_visita(request, tipo, visita_id, accion):
    """API para ejecutar acciones sobre una visita"""
    
    if tipo == 'interna':
        visita = get_object_or_404(VisitaInterna, pk=visita_id)
        
        def registrar_accion(tipo_accion, descripcion):
            HistorialAccionVisitaInterna.objects.create(
                visita=visita,
                usuario=request.user,
                tipo_accion=tipo_accion,
                descripcion=descripcion,
                ip_address=request.META.get('REMOTE_ADDR')
            )
    else:
        visita = get_object_or_404(VisitaExterna, pk=visita_id)
        
        def registrar_accion(tipo_accion, descripcion):
            HistorialAccionVisitaExterna.objects.create(
                visita=visita,
                usuario=request.user,
                tipo_accion=tipo_accion,
                descripcion=descripcion,
                ip_address=request.META.get('REMOTE_ADDR')
            )
    
    if accion == 'aprobar':
        visita.estado = 'aprobada_inicial'
        visita.save()
        registrar_accion('aprobacion_inicial', f'Visita aprobada inicialmente por {request.user.username}')
        return JsonResponse({'success': True, 'message': '✅ Visita aprobada inicialmente. El responsable puede registrar asistentes.'})
    
    elif accion == 'rechazar':
        visita.estado = 'rechazada'
        visita.save()
        registrar_accion('rechazo', f'Visita rechazada por {request.user.username}')
        return JsonResponse({'success': True, 'message': '❌ Visita rechazada'})
    
    elif accion == 'iniciar_revision':
        if visita.estado != 'documentos_enviados':
            return JsonResponse({'success': False, 'error': 'La visita no está en estado documentos_enviados'})
        visita.estado = 'en_revision_documentos'
        visita.save()
        registrar_accion('inicio_revision', f'Revisión de documentos iniciada por {request.user.username}')
        return JsonResponse({'success': True, 'message': '🔍 Revisión de documentos iniciada'})
    
    elif accion == 'confirmar_visita':
        if visita.estado not in ['documentos_enviados', 'en_revision_documentos']:
            return JsonResponse({'success': False, 'error': 'La visita debe estar en revisión de documentos para confirmarla'})
        visita.estado = 'confirmada'
        visita.save()
        registrar_accion('confirmacion', f'Visita confirmada definitivamente por {request.user.username}')
        return JsonResponse({'success': True, 'message': '✅ Visita confirmada definitivamente'})
    
    elif accion == 'enviar_coordinacion':
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'Método no permitido'})
        
        correo = request.POST.get('correo_coordinacion')
        if not correo:
            return JsonResponse({'success': False, 'error': 'Debe ingresar un correo de destino'})
        
        try:
            if tipo == 'interna':
                contexto = {
                    'tipo_visita': 'Visita Interna (SENA)',
                    'visita': visita,
                    'responsable': visita.responsable,
                    'correo_responsable': visita.correo_responsable,
                    'telefono_responsable': visita.telefono_responsable,
                    'cantidad': visita.cantidad_aprendices,
                    'programa': visita.nombre_programa,
                }
            else:
                contexto = {
                    'tipo_visita': 'Visita Externa (Institución)',
                    'visita': visita,
                    'responsable': visita.nombre_responsable,
                    'correo_responsable': visita.correo_responsable,
                    'telefono_responsable': visita.telefono_responsable,
                    'cantidad': visita.cantidad_visitantes,
                    'institucion': visita.nombre,
                }
            
            html_message = render_to_string('email_coordinacion_visita.html', contexto)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=f'📋 Solicitud de visita #{visita.id} - Requiere aprobación - MineGate SENA',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[correo],
                html_message=html_message,
                fail_silently=False,
            )
            
            visita.estado = 'enviada_coordinacion'
            visita.save()
            
            registrar_accion('envio_coordinacion', f'Enviado a coordinación ({correo}) por {request.user.username}')
            
            # Guardar registro de envío
            if tipo == 'interna':
                RegistroEnvioCoordinacionInterna.objects.create(
                    visita=visita,
                    correo_destino=correo,
                    usuario_remitente=request.user,
                    estado_resultado='enviado',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            else:
                RegistroEnvioCoordinacionExterna.objects.create(
                    visita=visita,
                    correo_destino=correo,
                    usuario_remitente=request.user,
                    estado_resultado='enviado',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            return JsonResponse({'success': True, 'message': f'✅ Enviado a coordinación ({correo})'})
        
        except Exception as e:
            # Guardar registro de fallo
            if tipo == 'interna':
                RegistroEnvioCoordinacionInterna.objects.create(
                    visita=visita,
                    correo_destino=correo,
                    usuario_remitente=request.user,
                    estado_resultado='fallido',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            else:
                RegistroEnvioCoordinacionExterna.objects.create(
                    visita=visita,
                    correo_destino=correo,
                    usuario_remitente=request.user,
                    estado_resultado='fallido',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            return JsonResponse({'success': False, 'error': f'Error al enviar: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'Acción no válida'})


@login_required(login_url='usuarios:login')
def api_revisar_documento_asistente(request, tipo, asistente_id, accion):
    """API para revisar documentos de asistentes"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    if tipo == 'interna':
        asistente = get_object_or_404(AsistenteVisitaInterna, pk=asistente_id)
    else:
        asistente = get_object_or_404(AsistenteVisitaExterna, pk=asistente_id)
    
    observaciones = request.POST.get('observaciones', '')
    
    if accion == 'aprobar':
        asistente.estado = 'documentos_aprobados'
        asistente.observaciones_revision = observaciones
        asistente.save()
        return JsonResponse({
            'success': True, 
            'message': f'✅ Documentos de {asistente.nombre_completo} aprobados',
            'nuevo_estado': 'documentos_aprobados'
        })
    
    elif accion == 'rechazar':
        if not observaciones:
            return JsonResponse({'success': False, 'error': 'Debe proporcionar observaciones al rechazar'})
        asistente.estado = 'documentos_rechazados'
        asistente.observaciones_revision = observaciones
        asistente.save()
        return JsonResponse({
            'success': True, 
            'message': f'❌ Documentos de {asistente.nombre_completo} rechazados',
            'nuevo_estado': 'documentos_rechazados'
        })
    
    return JsonResponse({'success': False, 'error': 'Acción no válida'})
