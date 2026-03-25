"""
Vistas para gestión de reprogramación de visitas
Maneja solicitudes y asignación de nuevas fechas
"""

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
from datetime import timedelta
from core.sanitization import sanitize_text

from visitaInterna.models import VisitaInterna, HistorialReprogramacion as HistorialReprogramacionInterna
from visitaExterna.models import VisitaExterna, HistorialReprogramacion as HistorialReprogramacionExterna
from calendario.models import ReservaHorario


def _enviar_correo_visita_reprogramada(request, visita, tipo, historial, fecha_hora_nueva):
    """Notifica al responsable que la visita fue reprogramada con una nueva fecha."""
    try:
        correo_destino = (getattr(visita, "correo_responsable", "") or "").strip()
        if not correo_destino:
            return

        es_interna = tipo == "interna"
        responsable_nombre = (
            getattr(visita, "responsable", "")
            if es_interna
            else getattr(visita, "nombre_responsable", "")
        )
        panel_path = reverse(
            "panel_instructor_interno:detalle_visita" if es_interna else "panel_instructor_externo:detalle_visita",
            kwargs={"pk": visita.id},
        )

        fecha_anterior = (
            historial.fecha_anterior.strftime("%d/%m/%Y %H:%M")
            if getattr(historial, "fecha_anterior", None)
            else "No disponible"
        )

        context = {
            "responsable_nombre": responsable_nombre or "Responsable",
            "tipo_visita": "Interna" if es_interna else "Externa",
            "visita_id": visita.id,
            "fecha_anterior": fecha_anterior,
            "nueva_fecha": fecha_hora_nueva.strftime("%d/%m/%Y %H:%M"),
            "motivo": historial.motivo or "Sin motivo registrado",
            "panel_url": request.build_absolute_uri(panel_path),
        }

        html_content = render_to_string("emails/visita_reprogramada.html", context)
        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(
            f"Visita reprogramada: nueva fecha asignada ({context['tipo_visita']})",
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [correo_destino],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=True)
    except Exception:
        pass


def es_coordinador(user):
    """Verifica si el usuario es coordinador"""
    return user.groups.filter(name="coordinador").exists()


def es_usuario_sst(user):
    return user.is_staff and not user.is_superuser and not es_coordinador(user)


def es_administrador_panel(user):
    """Verifica si el usuario es administrador del panel"""
    return user.is_superuser or (user.is_staff and not es_coordinador(user))


def puede_completar_reprogramacion(user, visita):
    """Permisos para que un instructor complete su reprogramación."""
    if not user.is_authenticated:
        return False

    if user.is_superuser or user.is_staff:
        return True

    if user.groups.filter(name__in=["instructor", "instructor_interno", "instructor_externo"]).exists():
        return True

    correo_visita = (getattr(visita, "correo_responsable", "") or "").strip().lower()
    correo_usuario = (getattr(user, "email", "") or "").strip().lower()
    return bool(correo_visita and correo_usuario and correo_visita == correo_usuario)


def sesion_responsable_valida(request, visita, rol_esperado):
    """Valida el acceso del responsable autenticado por sesión pública."""
    if not request.session.get("responsable_autenticado"):
        return False
    if request.session.get("responsable_rol") != rol_esperado:
        return False

    correo_sesion = (request.session.get("responsable_correo") or "").strip().lower()
    correo_visita = (getattr(visita, "correo_responsable", "") or "").strip().lower()
    return bool(correo_sesion and correo_visita and correo_sesion == correo_visita)


def puede_completar_reprogramacion_request(request, visita, rol_esperado):
    """Permite completar por usuario Django o por sesión válida del responsable."""
    if request.user.is_authenticated and puede_completar_reprogramacion(request.user, visita):
        return True

    return sesion_responsable_valida(request, visita, rol_esperado)


@login_required(login_url="usuarios:login")
@require_http_methods(["POST"])
def solicitar_reprogramacion(request, tipo, visita_id):
    """
    Coordinador o Administrador solicita reprogramación de una visita.
    Crea un historial de reprogramación y cambia el estado a REPROGRAMACION_SOLICITADA.
    """
    try:
        if es_usuario_sst(request.user):
            return JsonResponse({
                "success": False,
                "message": "El rol SST no tiene permitido solicitar reprogramaciones."
            }, status=403)

        motivo = sanitize_text(
            request.POST.get("motivo", ""),
            max_length=1000,
            allow_newlines=True,
        )
        
        if not motivo:
            return JsonResponse({
                "success": False,
                "message": "El motivo de la reprogramación es requerido"
            }, status=400)
        
        if tipo == "interna":
            visita = get_object_or_404(VisitaInterna, pk=visita_id)
            
            # Solo coordinador o administrador pueden solicitar reprogramación
            if not (es_coordinador(request.user) or es_administrador_panel(request.user)):
                return JsonResponse({
                    "success": False,
                    "message": "No tienes permiso para solicitar reprogramación"
                }, status=403)
            
            # Guardar fecha anterior
            fecha_anterior = timezone.datetime.combine(
                visita.fecha_visita,
                visita.hora_inicio
            ) if visita.fecha_visita and visita.hora_inicio else timezone.now()
            
            # Crear historial de reprogramación
            tipo_solicitud = "coordinador" if es_coordinador(request.user) else "administrador"
            historial = HistorialReprogramacionInterna.objects.create(
                visita_interna=visita,
                fecha_anterior=fecha_anterior,
                motivo=motivo,
                solicitado_por=request.user,
                tipo=tipo_solicitud,
                completada=False
            )
            
            # Cambiar estado de la visita
            visita.estado = "reprogramacion_solicitada"
            visita.save()
            
            return JsonResponse({
                "success": True,
                "message": f"Reprogramación solicitada. ID histórico: {historial.id}",
                "historial_id": historial.id
            })
        
        elif tipo == "externa":
            visita = get_object_or_404(VisitaExterna, pk=visita_id)
            
            # Solo coordinador o administrador pueden solicitar reprogramación
            if not (es_coordinador(request.user) or es_administrador_panel(request.user)):
                return JsonResponse({
                    "success": False,
                    "message": "No tienes permiso para solicitar reprogramación"
                }, status=403)
            
            # Guardar fecha anterior
            fecha_anterior = timezone.datetime.combine(
                visita.fecha_visita,
                visita.hora_inicio
            ) if visita.fecha_visita and visita.hora_inicio else timezone.now()
            
            # Crear historial de reprogramación
            tipo_solicitud = "coordinador" if es_coordinador(request.user) else "administrador"
            historial = HistorialReprogramacionExterna.objects.create(
                visita_externa=visita,
                fecha_anterior=fecha_anterior,
                motivo=motivo,
                solicitado_por=request.user,
                tipo=tipo_solicitud,
                completada=False
            )
            
            # Cambiar estado de la visita
            visita.estado = "reprogramacion_solicitada"
            visita.save()
            
            return JsonResponse({
                "success": True,
                "message": f"Reprogramación solicitada. ID histórico: {historial.id}",
                "historial_id": historial.id
            })
        
        else:
            return JsonResponse({
                "success": False,
                "message": "Tipo de visita no válido"
            }, status=400)
    
    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error: {str(e)}"
        }, status=500)


@require_http_methods(["POST"])
def completar_reprogramacion(request, tipo, visita_id):
    """
    Instructor actualiza la fecha de la visita desde el calendario.
    Marca el historial como completado y vuelve el estado a PENDIENTE.
    """
    try:
        if not request.user.is_authenticated and not request.session.get("responsable_autenticado"):
            return JsonResponse({
                "success": False,
                "message": "Sesión no válida. Inicie sesión nuevamente."
            }, status=401)

        nueva_fecha = sanitize_text(request.POST.get("fecha", ""), max_length=10, allow_newlines=False)
        nueva_hora = sanitize_text(request.POST.get("hora", ""), max_length=5, allow_newlines=False)
        nueva_hora_fin = sanitize_text(request.POST.get("hora_fin", ""), max_length=5, allow_newlines=False)
        historial_id = sanitize_text(request.POST.get("historial_id", ""), max_length=12, allow_newlines=False)
        
        if not nueva_fecha or not nueva_hora or not historial_id:
            return JsonResponse({
                "success": False,
                "message": "Fecha, hora e ID de historial son requeridos"
            }, status=400)
        
        # Parsear fecha y hora
        try:
            fecha_obj = timezone.datetime.strptime(nueva_fecha, "%Y-%m-%d").date()
            hora_obj = timezone.datetime.strptime(nueva_hora, "%H:%M").time()
            hora_fin_input = (
                timezone.datetime.strptime(nueva_hora_fin, "%H:%M").time()
                if nueva_hora_fin
                else None
            )
        except ValueError:
            return JsonResponse({
                "success": False,
                "message": "Formato de fecha u hora inválido"
            }, status=400)

        fecha_hora_fin = (
            timezone.datetime.combine(fecha_obj, hora_fin_input)
            if hora_fin_input
            else timezone.datetime.combine(fecha_obj, hora_obj) + timedelta(hours=2)
        )
        if fecha_hora_fin <= timezone.datetime.combine(fecha_obj, hora_obj):
            return JsonResponse({
                "success": False,
                "message": "La hora fin debe ser mayor que la hora inicio"
            }, status=400)

        hora_fin_visita = fecha_hora_fin.time()
        
        # Validar que la fecha sea en el futuro
        fecha_hora_nueva = timezone.datetime.combine(fecha_obj, hora_obj)
        if timezone.is_naive(fecha_hora_nueva) and timezone.is_aware(timezone.now()):
            fecha_hora_nueva = timezone.make_aware(fecha_hora_nueva, timezone.get_current_timezone())
        if fecha_hora_nueva < timezone.now():
            return JsonResponse({
                "success": False,
                "message": "La fecha y hora deben ser en el futuro"
            }, status=400)
        
        if tipo == "interna":
            visita = get_object_or_404(VisitaInterna, pk=visita_id)
            historial = get_object_or_404(HistorialReprogramacionInterna, pk=historial_id, visita_interna=visita)

            if historial.completada:
                return JsonResponse({
                    "success": False,
                    "message": "Esta solicitud de reprogramación ya fue completada"
                }, status=409)
            
            if not puede_completar_reprogramacion_request(request, visita, "interno"):
                return JsonResponse({
                    "success": False,
                    "message": "No tienes permiso para completar esta reprogramación"
                }, status=403)
            
            if not ReservaHorario.horario_disponible(fecha_obj, hora_obj, hora_fin_visita):
                return JsonResponse({
                    "success": False,
                    "message": "El horario seleccionado ya no está disponible"
                }, status=409)

            # Actualizar visita
            visita.fecha_visita = fecha_obj
            visita.hora_inicio = hora_obj
            visita.hora_fin = hora_fin_visita
            visita.estado = "enviada_coordinacion"
            visita.save()
            
            # Marcar histórico como completado
            historial.fecha_reprogramacion = fecha_hora_nueva
            historial.completada = True
            historial.save()
            
            # Recrear reserva de horario para la nueva fecha
            ReservaHorario.objects.update_or_create(
                visita_interna=visita,
                defaults={
                    "fecha": fecha_obj,
                    "hora_inicio": hora_obj,
                    "hora_fin": hora_fin_visita,
                    "estado": "pendiente",
                },
            )

            _enviar_correo_visita_reprogramada(request, visita, "interna", historial, fecha_hora_nueva)
            
            return JsonResponse({
                "success": True,
                "message": "✅ Visita reprogramada exitosamente. Nueva fecha: " + fecha_hora_nueva.strftime("%d/%m/%Y %H:%M")
            })
        
        elif tipo == "externa":
            visita = get_object_or_404(VisitaExterna, pk=visita_id)
            historial = get_object_or_404(HistorialReprogramacionExterna, pk=historial_id, visita_externa=visita)

            if historial.completada:
                return JsonResponse({
                    "success": False,
                    "message": "Esta solicitud de reprogramación ya fue completada"
                }, status=409)
            
            if not puede_completar_reprogramacion_request(request, visita, "externo"):
                return JsonResponse({
                    "success": False,
                    "message": "No tienes permiso para completar esta reprogramación"
                }, status=403)
            
            if not ReservaHorario.horario_disponible(fecha_obj, hora_obj, hora_fin_visita):
                return JsonResponse({
                    "success": False,
                    "message": "El horario seleccionado ya no está disponible"
                }, status=409)

            # Actualizar visita
            visita.fecha_visita = fecha_obj
            visita.hora_inicio = hora_obj
            visita.hora_fin = hora_fin_visita
            visita.estado = "enviada_coordinacion"
            visita.save()
            
            # Marcar histórico como completado
            historial.fecha_reprogramacion = fecha_hora_nueva
            historial.completada = True
            historial.save()
            
            # Recrear reserva de horario para la nueva fecha
            ReservaHorario.objects.update_or_create(
                visita_externa=visita,
                defaults={
                    "fecha": fecha_obj,
                    "hora_inicio": hora_obj,
                    "hora_fin": hora_fin_visita,
                    "estado": "pendiente",
                },
            )

            _enviar_correo_visita_reprogramada(request, visita, "externa", historial, fecha_hora_nueva)
            
            return JsonResponse({
                "success": True,
                "message": "✅ Visita reprogramada exitosamente. Nueva fecha: " + fecha_hora_nueva.strftime("%d/%m/%Y %H:%M")
            })
        
        else:
            return JsonResponse({
                "success": False,
                "message": "Tipo de visita no válido"
            }, status=400)
    
    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error: {str(e)}"
        }, status=500)


@login_required(login_url="usuarios:login")
@require_http_methods(["GET"])
def obtener_historial_reprogramaciones(request, tipo, visita_id):
    """
    Obtiene el historial de reprogramaciones de una visita.
    """
    try:
        if tipo == "interna":
            visita = get_object_or_404(VisitaInterna, pk=visita_id)
            reprogramaciones = HistorialReprogramacionInterna.objects.filter(
                visita_interna=visita
            ).order_by('-fecha_solicitud')
        
        elif tipo == "externa":
            visita = get_object_or_404(VisitaExterna, pk=visita_id)
            reprogramaciones = HistorialReprogramacionExterna.objects.filter(
                visita_externa=visita
            ).order_by('-fecha_solicitud')
        
        else:
            return JsonResponse({
                "success": False,
                "message": "Tipo de visita no válido"
            }, status=400)
        
        datos = []
        for rep in reprogramaciones:
            datos.append({
                "id": rep.id,
                "fecha_anterior": rep.fecha_anterior.strftime("%d/%m/%Y %H:%M"),
                "motivo": rep.motivo,
                "solicitado_por": rep.solicitado_por.username if rep.solicitado_por else "Sistema",
                "tipo": rep.get_tipo_display(),
                "completada": rep.completada,
                "fecha_reprogramacion": rep.fecha_reprogramacion.strftime("%d/%m/%Y %H:%M") if rep.fecha_reprogramacion else None,
                "fecha_solicitud": rep.fecha_solicitud.strftime("%d/%m/%Y %H:%M"),
            })
        
        return JsonResponse({
            "success": True,
            "reprogramaciones": datos
        })
    
    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error: {str(e)}"
        }, status=500)


@login_required(login_url="usuarios:login")
@require_http_methods(["GET"])
def obtener_reprogramaciones_pendientes_instructor(request):
    """
    Obtiene las visitas que requieren reprogramación para el instructor actual.
    Filtra visitas con estado REPROGRAMACION_SOLICITADA.
    """
    try:
        # Asumiendo que el instructor es identificado por el usuario actual
        # En una mejor implementación, se podría tener una relación User -> Instructor
        
        visitas_internas = VisitaInterna.objects.filter(
            estado="reprogramacion_solicitada"
        ).order_by('-fecha_solicitud')
        
        visitas_externas = VisitaExterna.objects.filter(
            estado="reprogramacion_solicitada"
        ).order_by('-fecha_solicitud')
        
        datos = []
        
        for v in visitas_internas:
            rep_pendiente = HistorialReprogramacionInterna.objects.filter(
                visita_interna=v,
                completada=False
            ).first()
            
            datos.append({
                "id": v.id,
                "tipo": "interna",
                "nombre_programa": v.nombre_programa,
                "responsable": v.responsable,
                "fecha_solicitud": v.fecha_solicitud.strftime("%d/%m/%Y"),
                "motivo": rep_pendiente.motivo if rep_pendiente else "N/A",
                "historial_id": rep_pendiente.id if rep_pendiente else None,
            })
        
        for v in visitas_externas:
            rep_pendiente = HistorialReprogramacionExterna.objects.filter(
                visita_externa=v,
                completada=False
            ).first()
            
            datos.append({
                "id": v.id,
                "tipo": "externa",
                "nombre": v.nombre,
                "responsable": v.nombre_responsable,
                "fecha_solicitud": v.fecha_solicitud.strftime("%d/%m/%Y"),
                "motivo": rep_pendiente.motivo if rep_pendiente else "N/A",
                "historial_id": rep_pendiente.id if rep_pendiente else None,
            })
        
        return JsonResponse({
            "success": True,
            "reprogramaciones_pendientes": datos
        })
    
    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error: {str(e)}"
        }, status=500)
