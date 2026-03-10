"""
App: gestion_visitas
Gestión administrativa de visitas - APIs para el panel administrativo
"""

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from visitaInterna.models import (
    VisitaInterna,
    AsistenteVisitaInterna,
    HistorialAccionVisitaInterna,
)
from visitaExterna.models import (
    VisitaExterna,
    AsistenteVisitaExterna,
    HistorialAccionVisitaExterna,
)
from documentos.models import DocumentoSubidoAsistente
from calendario.models import ReservaHorario
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse

ESTADOS_APROBADAS = [
    "aprobada_inicial",
    "documentos_enviados",
    "en_revision_documentos",
    "confirmada",
]


def es_coordinador(user):
    return user.groups.filter(name="coordinador").exists()


def es_administrador_panel(user):
    return user.is_superuser or (user.is_staff and not es_coordinador(user))


def tiene_aprobacion_previa_coordinacion(visita, tipo):
    if tipo == "interna":
        return HistorialAccionVisitaInterna.objects.filter(
            visita=visita,
            tipo_accion="aprobacion",
            usuario__groups__name="coordinador",
        ).exists()

    return HistorialAccionVisitaExterna.objects.filter(
        visita=visita,
        tipo_accion="aprobacion",
        usuario__groups__name="coordinador",
    ).exists()


@login_required(login_url="usuarios:login")
def api_listar_visitas(request):
    """API para listar visitas internas y externas"""
    if not es_administrador_panel(request.user):
        return JsonResponse({"success": False, "error": "No autorizado"}, status=403)

    tipo = request.GET.get("tipo", "internas")
    estado = request.GET.get("estado", "todos")
    buscar = request.GET.get("buscar", "")

    visitas_data = []

    if tipo == "internas":
        visitas = VisitaInterna.objects.all().order_by("-fecha_solicitud", "-id")

        if estado == "aprobadas":
            visitas = visitas.filter(estado__in=ESTADOS_APROBADAS)
        elif estado != "todos":
            visitas = visitas.filter(estado=estado)

        if buscar:
            visitas = visitas.filter(
                Q(responsable__icontains=buscar)
                | Q(nombre_programa__icontains=buscar)
                | Q(correo_responsable__icontains=buscar)
            )

        for v in visitas:
            visitas_data.append(
                {
                    "id": v.id,
                    "tipo": "interna",
                    "tipo_display": "Interna (SENA)",
                    "responsable": v.responsable,
                    "institucion": v.nombre_programa or "N/A",
                    "correo": v.correo_responsable,
                    "telefono": v.telefono_responsable,
                    "fecha_visita": (
                        v.fecha_solicitud.strftime("%d/%m/%Y")
                        if v.fecha_solicitud
                        else "N/A"
                    ),
                    "cantidad": v.cantidad_aprendices,
                    "estado": v.estado,
                    "tiene_rechazos": v.asistentes.filter(
                        estado="documentos_rechazados"
                    ).exists(),
                    "puede_confirmar": (
                        v.asistentes.exists()
                        and not v.asistentes.exclude(
                            estado="documentos_aprobados"
                        ).exists()
                    ),
                    "fecha_solicitud": (
                        v.fecha_solicitud.strftime("%d/%m/%Y %H:%M")
                        if v.fecha_solicitud
                        else "N/A"
                    ),
                }
            )

        docs_int = AsistenteVisitaInterna.objects.exclude(
            visita__estado__in=["aprobada_inicial", "pendiente", "enviada_coordinacion"]
        )
        stats = {
            "pendientes": VisitaInterna.objects.filter(estado="pendiente").count(),
            "aprobadas_inicial": VisitaInterna.objects.filter(
                estado="aprobada_inicial"
            ).count(),
            "aprobadas_total": VisitaInterna.objects.filter(
                estado__in=ESTADOS_APROBADAS
            ).count(),
            "documentos_enviados": VisitaInterna.objects.filter(
                estado="documentos_enviados"
            ).count(),
            "en_revision": VisitaInterna.objects.filter(
                estado="en_revision_documentos"
            ).count(),
            "confirmadas": VisitaInterna.objects.filter(estado="confirmada").count(),
            "rechazadas": VisitaInterna.objects.filter(estado="rechazada").count(),
            "docs_pendientes_revision": docs_int.filter(
                estado="pendiente_documentos"
            ).count(),
            "docs_aprobados": docs_int.filter(estado="documentos_aprobados").count(),
            "docs_rechazados": docs_int.filter(estado="documentos_rechazados").count(),
            "docs_total": docs_int.count(),
        }
    else:
        visitas = VisitaExterna.objects.all().order_by("-fecha_solicitud", "-id")

        if estado == "aprobadas":
            visitas = visitas.filter(estado__in=ESTADOS_APROBADAS)
        elif estado != "todos":
            visitas = visitas.filter(estado=estado)

        if buscar:
            visitas = visitas.filter(
                Q(nombre_responsable__icontains=buscar)
                | Q(nombre__icontains=buscar)
                | Q(correo_responsable__icontains=buscar)
            )

        for v in visitas:
            visitas_data.append(
                {
                    "id": v.id,
                    "tipo": "externa",
                    "tipo_display": "Externa (Institución)",
                    "responsable": v.nombre_responsable,
                    "institucion": v.nombre or "N/A",
                    "correo": v.correo_responsable,
                    "telefono": v.telefono_responsable,
                    "fecha_visita": (
                        v.fecha_solicitud.strftime("%d/%m/%Y")
                        if v.fecha_solicitud
                        else "N/A"
                    ),
                    "cantidad": v.cantidad_visitantes,
                    "estado": v.estado,
                    "tiene_rechazos": v.asistentes.filter(
                        estado="documentos_rechazados"
                    ).exists(),
                    "puede_confirmar": (
                        v.asistentes.exists()
                        and not v.asistentes.exclude(
                            estado="documentos_aprobados"
                        ).exists()
                    ),
                    "fecha_solicitud": (
                        v.fecha_solicitud.strftime("%d/%m/%Y %H:%M")
                        if v.fecha_solicitud
                        else "N/A"
                    ),
                }
            )

        docs_ext = AsistenteVisitaExterna.objects.exclude(
            visita__estado__in=["aprobada_inicial", "pendiente", "enviada_coordinacion"]
        )
        stats = {
            "pendientes": VisitaExterna.objects.filter(estado="pendiente").count(),
            "aprobadas_inicial": VisitaExterna.objects.filter(
                estado="aprobada_inicial"
            ).count(),
            "aprobadas_total": VisitaExterna.objects.filter(
                estado__in=ESTADOS_APROBADAS
            ).count(),
            "documentos_enviados": VisitaExterna.objects.filter(
                estado="documentos_enviados"
            ).count(),
            "en_revision": VisitaExterna.objects.filter(
                estado="en_revision_documentos"
            ).count(),
            "confirmadas": VisitaExterna.objects.filter(estado="confirmada").count(),
            "rechazadas": VisitaExterna.objects.filter(estado="rechazada").count(),
            "docs_pendientes_revision": docs_ext.filter(
                estado="pendiente_documentos"
            ).count(),
            "docs_aprobados": docs_ext.filter(estado="documentos_aprobados").count(),
            "docs_rechazados": docs_ext.filter(estado="documentos_rechazados").count(),
            "docs_total": docs_ext.count(),
        }

    return JsonResponse(
        {
            "visitas": visitas_data,
            "stats": stats,
        }
    )


@login_required(login_url="usuarios:login")
def api_detalle_visita(request, tipo, visita_id):
    """API para obtener detalle de una visita"""
    if not es_administrador_panel(request.user):
        return JsonResponse({"success": False, "error": "No autorizado"}, status=403)

    if tipo == "interna":
        visita = get_object_or_404(VisitaInterna, pk=visita_id)
        asistentes = []
        if visita.estado not in [
            "aprobada_inicial",
            "pendiente",
            "enviada_coordinacion",
        ]:
            for a in visita.asistentes.all():
                asistentes.append(
                    {
                        "id": a.id,
                        "nombre_completo": a.nombre_completo,
                        "tipo_documento": a.tipo_documento,
                        "numero_documento": a.numero_documento,
                        "correo": a.correo,
                        "telefono": a.telefono,
                        "estado": a.estado,
                        "documento_identidad": (
                            a.documento_identidad.url if a.documento_identidad else None
                        ),
                        "documento_adicional": (
                            a.documento_adicional.url if a.documento_adicional else None
                        ),
                        "formato_autorizacion_padres": (
                            a.formato_autorizacion_padres.url
                            if a.formato_autorizacion_padres
                            else None
                        ),
                        "estado_autorizacion_padres": (
                            a.estado_autorizacion_padres
                            if a.formato_autorizacion_padres
                            else None
                        ),
                        "observaciones_autorizacion_padres": (
                            a.observaciones_autorizacion_padres
                            if a.formato_autorizacion_padres
                            else None
                        ),
                        "observaciones_revision": a.observaciones_revision,
                        "documentos_subidos": [
                            {
                                "id": ds.id,
                                "titulo": ds.documento_requerido.titulo,
                                "categoria": ds.documento_requerido.get_categoria_display(),
                                "url": f"/documentos/ver-asistente/{ds.id}/",
                                "download_url": f"/documentos/descargar-asistente/{ds.id}/",
                                "estado": ds.estado,
                                "observaciones_revision": ds.observaciones_revision
                                or "",
                                "nombre_archivo": ds.nombre_archivo,
                                "fecha_subida": (
                                    ds.fecha_subida.strftime("%d/%m/%Y %H:%M")
                                    if ds.fecha_subida
                                    else None
                                ),
                            }
                            for ds in a.documentos_subidos.select_related(
                                "documento_requerido"
                            ).all()
                        ],
                    }
                )

        historial = list(
            HistorialAccionVisitaInterna.objects.filter(visita=visita)
            .order_by("-fecha_hora")
            .values("tipo_accion", "descripcion", "fecha_hora", "usuario__username")[
                :10
            ]
        )

        data = {
            "id": visita.id,
            "tipo": "interna",
            "responsable": visita.responsable,
            "correo": visita.correo_responsable,
            "telefono": visita.telefono_responsable,
            "programa": visita.nombre_programa,
            "ficha": visita.numero_ficha,
            "cantidad": visita.cantidad_aprendices,
            "fecha_visita": (
                visita.fecha_solicitud.strftime("%d/%m/%Y")
                if visita.fecha_solicitud
                else "N/A"
            ),
            "estado": visita.estado,
            "observaciones": visita.observaciones or "",
            "fecha_solicitud": (
                visita.fecha_solicitud.strftime("%d/%m/%Y %H:%M")
                if visita.fecha_solicitud
                else "N/A"
            ),
            "asistentes": asistentes,
            "asistentes_count": len(asistentes),
            "historial": historial,
        }
    else:
        visita = get_object_or_404(VisitaExterna, pk=visita_id)
        asistentes = []
        if visita.estado not in [
            "aprobada_inicial",
            "pendiente",
            "enviada_coordinacion",
        ]:
            for a in visita.asistentes.all():
                asistentes.append(
                    {
                        "id": a.id,
                        "nombre_completo": a.nombre_completo,
                        "tipo_documento": a.tipo_documento,
                        "numero_documento": a.numero_documento,
                        "correo": a.correo,
                        "telefono": a.telefono,
                        "estado": a.estado,
                        "documento_identidad": (
                            a.documento_identidad.url if a.documento_identidad else None
                        ),
                        "documento_adicional": (
                            a.documento_adicional.url if a.documento_adicional else None
                        ),
                        "formato_autorizacion_padres": (
                            a.formato_autorizacion_padres.url
                            if a.formato_autorizacion_padres
                            else None
                        ),
                        "observaciones_revision": a.observaciones_revision,
                        "documentos_subidos": [
                            {
                                "id": ds.id,
                                "titulo": ds.documento_requerido.titulo,
                                "categoria": ds.documento_requerido.get_categoria_display(),
                                "url": f"/documentos/ver-asistente/{ds.id}/",
                                "download_url": f"/documentos/descargar-asistente/{ds.id}/",
                                "estado": ds.estado,
                                "observaciones_revision": ds.observaciones_revision
                                or "",
                                "nombre_archivo": ds.nombre_archivo,
                                "fecha_subida": (
                                    ds.fecha_subida.strftime("%d/%m/%Y %H:%M")
                                    if ds.fecha_subida
                                    else None
                                ),
                            }
                            for ds in a.documentos_subidos.select_related(
                                "documento_requerido"
                            ).all()
                        ],
                    }
                )

        historial = list(
            HistorialAccionVisitaExterna.objects.filter(visita=visita)
            .order_by("-fecha_hora")
            .values("tipo_accion", "descripcion", "fecha_hora", "usuario__username")[
                :10
            ]
        )

        data = {
            "id": visita.id,
            "tipo": "externa",
            "responsable": visita.nombre_responsable,
            "correo": visita.correo_responsable,
            "telefono": visita.telefono_responsable,
            "institucion": visita.nombre,
            "cantidad": visita.cantidad_visitantes,
            "fecha_visita": (
                visita.fecha_solicitud.strftime("%d/%m/%Y")
                if visita.fecha_solicitud
                else "N/A"
            ),
            "estado": visita.estado,
            "observaciones": visita.observacion or "",
            "fecha_solicitud": (
                visita.fecha_solicitud.strftime("%d/%m/%Y %H:%M")
                if visita.fecha_solicitud
                else "N/A"
            ),
            "asistentes": asistentes,
            "asistentes_count": len(asistentes),
            "historial": historial,
        }

    return JsonResponse(data)


@login_required(login_url="usuarios:login")
def api_accion_visita(request, tipo, visita_id, accion):
    """API para ejecutar acciones sobre una visita"""

    if tipo == "interna":
        visita = get_object_or_404(VisitaInterna, pk=visita_id)

        def registrar_accion(tipo_accion, descripcion):
            HistorialAccionVisitaInterna.objects.create(
                visita=visita,
                usuario=request.user,
                tipo_accion=tipo_accion,
                descripcion=descripcion,
                ip_address=request.META.get("REMOTE_ADDR"),
            )

    else:
        visita = get_object_or_404(VisitaExterna, pk=visita_id)

        def registrar_accion(tipo_accion, descripcion):
            HistorialAccionVisitaExterna.objects.create(
                visita=visita,
                usuario=request.user,
                tipo_accion=tipo_accion,
                descripcion=descripcion,
                ip_address=request.META.get("REMOTE_ADDR"),
            )

    if accion == "aprobar":
        if es_coordinador(request.user):
            if visita.estado != "enviada_coordinacion":
                return JsonResponse(
                    {
                        "success": False,
                        "error": "La visita no está pendiente de revisión por coordinación",
                    }
                )

            visita.estado = "pendiente"
            visita.save()
            registrar_accion(
                "aprobacion",
                f"Solicitud aprobada por coordinación ({request.user.username}). Pendiente aprobación administrativa.",
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": "✅ Solicitud aprobada por coordinación. Ahora está pendiente de aprobación del administrador.",
                }
            )

        if not es_administrador_panel(request.user):
            return JsonResponse(
                {"success": False, "error": "No autorizado para aprobar esta visita"},
                status=403,
            )

        if visita.estado != "pendiente":
            return JsonResponse(
                {
                    "success": False,
                    "error": "La visita debe estar pendiente de aprobación administrativa",
                }
            )

        if not tiene_aprobacion_previa_coordinacion(visita, tipo):
            return JsonResponse(
                {
                    "success": False,
                    "error": "La visita debe ser aprobada primero por coordinación antes de la aprobación administrativa.",
                }
            )

        visita.estado = "aprobada_inicial"
        visita.save()

        # Enviar correo al responsable notificando la aprobación inicial y link al panel
        try:
            if tipo == "interna":
                panel_path = reverse("panel_instructor_interno:mis_visitas")
            else:
                panel_path = reverse("panel_instructor_externo:panel")
            panel_url = request.build_absolute_uri(panel_path)

            subject = "Su visita ha sido aprobada inicialmente"
            context = {
                "responsable_nombre": getattr(
                    visita, "responsable", getattr(visita, "nombre_responsable", "")
                ),
                "panel_url": panel_url,
            }
            if tipo == "interna":
                html_content = render_to_string(
                    "emails/aprobada_visita_interna.html", context
                )
            else:
                html_content = render_to_string(
                    "emails/aprobada_visita_externa.html", context
                )
            text_content = strip_tags(html_content)
            msg = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [visita.correo_responsable],
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=True)
        except Exception:
            pass

        # Crear reserva de horario para bloquear el día/horario
        if tipo == "interna":
            ReservaHorario.crear_reserva_interna(visita)
        else:
            ReservaHorario.crear_reserva_externa(visita)

        registrar_accion(
            "aprobacion",
            f"Visita aprobada administrativamente por {request.user.username}",
        )
        return JsonResponse(
            {
                "success": True,
                "message": "✅ Visita aprobada inicialmente. El responsable puede registrar asistentes.",
            }
        )

    elif accion == "rechazar":
        observaciones = request.POST.get("observaciones", "")

        if es_coordinador(request.user):
            if visita.estado != "enviada_coordinacion":
                return JsonResponse(
                    {
                        "success": False,
                        "error": "La visita no está pendiente de revisión por coordinación",
                    }
                )
        elif es_administrador_panel(request.user):
            if visita.estado != "pendiente":
                return JsonResponse(
                    {
                        "success": False,
                        "error": "La visita no está pendiente de aprobación administrativa",
                    }
                )
        else:
            return JsonResponse(
                {"success": False, "error": "No autorizado para rechazar esta visita"},
                status=403,
            )

        visita.estado = "rechazada"
        visita.save()
        registrar_accion(
            "rechazo",
            (
                f"Visita rechazada por {request.user.username}. Motivo: {observaciones}"
                if observaciones
                else f"Visita rechazada por {request.user.username}"
            ),
        )
        return JsonResponse({"success": True, "message": "❌ Visita rechazada"})

    elif accion == "iniciar_revision":
        if not es_administrador_panel(request.user):
            return JsonResponse(
                {"success": False, "error": "No autorizado para esta acción"},
                status=403,
            )

        if visita.estado != "documentos_enviados":
            return JsonResponse(
                {
                    "success": False,
                    "error": "La visita no está en estado documentos_enviados",
                }
            )
        visita.estado = "en_revision_documentos"
        visita.save()
        registrar_accion(
            "inicio_revision",
            f"Revisión de documentos iniciada por {request.user.username}",
        )
        return JsonResponse(
            {
                "success": True,
                "message": " ✔️ Se ha finalizado la revisión de documentos",
            }
        )

    elif accion == "confirmar_visita":
        if not es_administrador_panel(request.user):
            return JsonResponse(
                {"success": False, "error": "No autorizado para esta acción"},
                status=403,
            )

        if visita.estado not in ["documentos_enviados", "en_revision_documentos"]:
            return JsonResponse(
                {
                    "success": False,
                    "error": "La visita debe estar en revisión de documentos para confirmarla",
                }
            )

        # Verificar que todos los asistentes tengan documentos aprobados
        asistentes_sin_aprobar = visita.asistentes.exclude(
            estado="documentos_aprobados"
        ).count()
        if asistentes_sin_aprobar > 0:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"No se puede confirmar la visita. Hay {asistentes_sin_aprobar} asistente(s) con documentos pendientes o rechazados.",
                }
            )

        visita.estado = "confirmada"
        visita.save()

        # Confirmar la reserva de horario (cambiar a estado 'confirmada')
        ReservaHorario.confirmar_reserva(visita, tipo)

        # Enviar correo al responsable notificando confirmación y detalles
        try:
            if tipo == "interna":
                template_name = "emails/visita_confirmada_interna.html"
                panel_path = reverse("panel_instructor_interno:mis_visitas")
            else:
                template_name = "emails/visita_confirmada_externa.html"
                panel_path = reverse("panel_instructor_externo:panel")

            panel_url = request.build_absolute_uri(panel_path)

            # Construir contexto con detalles de la visita
            context = {
                "responsable_nombre": getattr(
                    visita, "responsable", getattr(visita, "nombre_responsable", "")
                ),
                "fecha_visita": (
                    visita.fecha_visita.strftime("%d/%m/%Y")
                    if getattr(visita, "fecha_visita", None)
                    else (
                        visita.fecha_solicitud.strftime("%d/%m/%Y")
                        if visita.fecha_solicitud
                        else "Por definir"
                    )
                ),
                "hora_programada": (
                    (
                        visita.hora_inicio.strftime("%I:%M %p")
                        + " - "
                        + visita.hora_fin.strftime("%I:%M %p")
                    )
                    if getattr(visita, "hora_inicio", None)
                    and getattr(visita, "hora_fin", None)
                    else "Por definir"
                ),
                "recomendaciones": "Por favor llegar 10 minutos antes; traer documento de identidad; seguir instrucciones de coordinación.",
                "panel_url": panel_url,
            }

            # Campos específicos
            if tipo == "interna":
                context.update(
                    {
                        "nombre_programa": visita.nombre_programa,
                        "numero_ficha": visita.numero_ficha,
                        "responsable": visita.responsable,
                    }
                )
            else:
                context.update(
                    {
                        "nombre": visita.nombre,
                        "nombre_responsable": visita.nombre_responsable,
                        "sede": getattr(visita, "sede", "No especificada"),
                    }
                )

            html_content = render_to_string(template_name, context)
            text_content = strip_tags(html_content)
            subject = "Visita confirmada exitosamente"
            msg = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [visita.correo_responsable],
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=True)
        except Exception:
            pass

        registrar_accion(
            "confirmacion",
            f"Visita confirmada definitivamente por {request.user.username}",
        )
        return JsonResponse(
            {"success": True, "message": "✅ Visita confirmada definitivamente"}
        )

    return JsonResponse({"success": False, "error": "Acción no válida"})


@login_required(login_url="usuarios:login")
def api_revisar_autorizacion_padres(request, tipo, asistente_id, accion):
    """API para revisar específicamente el documento de autorización de padres"""
    if not es_administrador_panel(request.user):
        return JsonResponse({"success": False, "error": "No autorizado"}, status=403)

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"})

    if tipo == "interna":
        asistente = get_object_or_404(AsistenteVisitaInterna, pk=asistente_id)
    else:
        asistente = get_object_or_404(AsistenteVisitaExterna, pk=asistente_id)

    # Verificar que tenga el archivo
    if not asistente.formato_autorizacion_padres:
        return JsonResponse(
            {
                "success": False,
                "error": "Este asistente no tiene formato de autorización de padres",
            }
        )

    observaciones = request.POST.get("observaciones", "")

    if accion == "aprobar":
        asistente.estado_autorizacion_padres = "aprobado"
        asistente.observaciones_autorizacion_padres = observaciones
        asistente.save()
        return JsonResponse(
            {
                "success": True,
                "message": f"✅ Autorización de padres aprobada para {asistente.nombre_completo}",
            }
        )
    elif accion == "rechazar":
        if not observaciones:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Debe proporcionar observaciones al rechazar",
                }
            )
        asistente.estado_autorizacion_padres = "rechazado"
        asistente.observaciones_autorizacion_padres = observaciones
        asistente.save()
        return JsonResponse(
            {
                "success": True,
                "message": f"❌ Autorización de padres rechazada para {asistente.nombre_completo}",
            }
        )

    return JsonResponse({"success": False, "error": "Acción no válida"})


@login_required(login_url="usuarios:login")
def api_revisar_documento_asistente(request, tipo, asistente_id, accion):
    """API para revisar documentos de asistentes"""
    if not es_administrador_panel(request.user):
        return JsonResponse({"success": False, "error": "No autorizado"}, status=403)

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"})

    if tipo == "interna":
        asistente = get_object_or_404(AsistenteVisitaInterna, pk=asistente_id)
    else:
        asistente = get_object_or_404(AsistenteVisitaExterna, pk=asistente_id)

    observaciones = request.POST.get("observaciones", "")

    if accion == "aprobar":
        # Restricción: No se puede aprobar masivamente si hay rechazos parciales
        if asistente.documentos_subidos.filter(estado="rechazado").exists():
            return JsonResponse(
                {
                    "success": False,
                    "error": "No se puede aprobar masivamente porque hay documentos rechazados. Corrija o apruebe individualmente.",
                }
            )

        # Restricción: Debe haber al menos un documento aprobado individualmente
        if not asistente.documentos_subidos.filter(estado="aprobado").exists():
            return JsonResponse(
                {
                    "success": False,
                    "error": "Debe revisar y aprobar al menos un documento individualmente antes de aprobar el resto.",
                }
            )

        asistente.estado = "documentos_aprobados"
        asistente.observaciones_revision = observaciones
        asistente.save()
        return JsonResponse(
            {
                "success": True,
                "message": f"✅ Documentos de {asistente.nombre_completo} aprobados",
                "nuevo_estado": "documentos_aprobados",
            }
        )

    elif accion == "rechazar":
        if not observaciones:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Debe proporcionar observaciones al rechazar",
                }
            )
        asistente.estado = "documentos_rechazados"
        asistente.observaciones_revision = observaciones
        asistente.save()
        return JsonResponse(
            {
                "success": True,
                "message": f"❌ Documentos de {asistente.nombre_completo} rechazados",
                "nuevo_estado": "documentos_rechazados",
            }
        )

    return JsonResponse({"success": False, "error": "Acción no válida"})


@login_required(login_url="usuarios:login")
def api_visitas_aprobadas(request):
    """API para listar visitas aprobadas (para mostrarVisitasAprobadas en el JS)"""
    if not es_administrador_panel(request.user):
        return JsonResponse({"success": False, "error": "No autorizado"}, status=403)

    tipo = request.GET.get("tipo", "internas")
    visitas_data = []

    if tipo == "internas":
        visitas = VisitaInterna.objects.filter(estado__in=ESTADOS_APROBADAS).order_by(
            "-fecha_solicitud", "-id"
        )
        for v in visitas:
            visitas_data.append(
                {
                    "id": v.id,
                    "tipo": "interna",
                    "tipo_display": "Interna (SENA)",
                    "responsable": v.responsable,
                    "institucion": v.nombre_programa or "N/A",
                    "correo": v.correo_responsable,
                    "fecha_visita": (
                        v.fecha_solicitud.strftime("%d/%m/%Y")
                        if v.fecha_solicitud
                        else "N/A"
                    ),
                    "cantidad": v.cantidad_aprendices,
                    "estado": v.estado,
                }
            )
    else:
        visitas = VisitaExterna.objects.filter(estado__in=ESTADOS_APROBADAS).order_by(
            "-fecha_solicitud", "-id"
        )
        for v in visitas:
            visitas_data.append(
                {
                    "id": v.id,
                    "tipo": "externa",
                    "tipo_display": "Externa (Institución)",
                    "responsable": v.nombre_responsable,
                    "institucion": v.nombre or "N/A",
                    "correo": v.correo_responsable,
                    "fecha_visita": (
                        v.fecha_solicitud.strftime("%d/%m/%Y")
                        if v.fecha_solicitud
                        else "N/A"
                    ),
                    "cantidad": v.cantidad_visitantes,
                    "estado": v.estado,
                }
            )

    return JsonResponse({"visitas": visitas_data})


@login_required(login_url="usuarios:login")
def api_documentos_revision(request):
    """API que devuelve todos los asistentes con sus documentos, filtrando por tipo y estado_asistente"""
    if not es_administrador_panel(request.user):
        return JsonResponse({"success": False, "error": "No autorizado"}, status=403)

    tipo = request.GET.get("tipo", "internas")
    estado_asistente = request.GET.get("estado_asistente", "")

    documentos_data = []

    if tipo == "internas":
        qs = AsistenteVisitaInterna.objects.select_related("visita").all()
        if estado_asistente:
            qs = qs.filter(estado=estado_asistente)
        for a in qs:
            documentos_data.append(
                {
                    "asistente_id": a.id,
                    "visita_id": a.visita.id,
                    "visita_tipo": "interna",
                    "visita_responsable": a.visita.responsable,
                    "visita_programa": a.visita.nombre_programa or "N/A",
                    "visita_estado": a.visita.estado,
                    "visita_estado_display": a.visita.get_estado_display(),
                    "visita_fecha": (
                        a.visita.fecha_solicitud.strftime("%d/%m/%Y")
                        if a.visita.fecha_solicitud
                        else "N/A"
                    ),
                    "nombre_completo": a.nombre_completo,
                    "tipo_documento": a.tipo_documento,
                    "numero_documento": a.numero_documento,
                    "estado": a.estado,
                    "documento_identidad": (
                        a.documento_identidad.url if a.documento_identidad else None
                    ),
                    "documento_adicional": (
                        a.documento_adicional.url if a.documento_adicional else None
                    ),
                    "estado_autorizacion_padres": (
                        a.estado_autorizacion_padres
                        if a.formato_autorizacion_padres
                        else None
                    ),
                    "observaciones_autorizacion_padres": (
                        a.observaciones_autorizacion_padres
                        if a.formato_autorizacion_padres
                        else None
                    ),
                    "observaciones_revision": a.observaciones_revision,
                    "documentos_subidos": [
                        {
                            "id": ds.id,
                            "titulo": ds.documento_requerido.titulo,
                            "categoria": ds.documento_requerido.get_categoria_display(),
                            "url": f"/documentos/ver-asistente/{ds.id}/",
                            "download_url": f"/documentos/descargar-asistente/{ds.id}/",
                            "estado": ds.estado,
                            "observaciones_revision": ds.observaciones_revision or "",
                            "nombre_archivo": ds.nombre_archivo,
                            "fecha_subida": (
                                ds.fecha_subida.strftime("%d/%m/%Y %H:%M")
                                if ds.fecha_subida
                                else None
                            ),
                        }
                        for ds in a.documentos_subidos.select_related(
                            "documento_requerido"
                        ).all()
                    ],
                }
            )
    else:
        qs = AsistenteVisitaExterna.objects.select_related("visita").all()
        if estado_asistente:
            qs = qs.filter(estado=estado_asistente)
        for a in qs:
            documentos_data.append(
                {
                    "asistente_id": a.id,
                    "visita_id": a.visita.id,
                    "visita_tipo": "externa",
                    "visita_responsable": a.visita.nombre_responsable,
                    "visita_programa": a.visita.nombre or "N/A",
                    "visita_estado": a.visita.estado,
                    "visita_estado_display": a.visita.get_estado_display(),
                    "visita_fecha": (
                        a.visita.fecha_solicitud.strftime("%d/%m/%Y")
                        if a.visita.fecha_solicitud
                        else "N/A"
                    ),
                    "nombre_completo": a.nombre_completo,
                    "tipo_documento": a.tipo_documento,
                    "numero_documento": a.numero_documento,
                    "estado": a.estado,
                    "documento_identidad": (
                        a.documento_identidad.url if a.documento_identidad else None
                    ),
                    "documento_adicional": (
                        a.documento_adicional.url if a.documento_adicional else None
                    ),
                    "observaciones_revision": a.observaciones_revision,
                    "documentos_subidos": [
                        {
                            "id": ds.id,
                            "titulo": ds.documento_requerido.titulo,
                            "categoria": ds.documento_requerido.get_categoria_display(),
                            "url": f"/documentos/ver-asistente/{ds.id}/",
                            "download_url": f"/documentos/descargar-asistente/{ds.id}/",
                            "estado": ds.estado,
                            "observaciones_revision": ds.observaciones_revision or "",
                            "nombre_archivo": ds.nombre_archivo,
                            "fecha_subida": (
                                ds.fecha_subida.strftime("%d/%m/%Y %H:%M")
                                if ds.fecha_subida
                                else None
                            ),
                        }
                        for ds in a.documentos_subidos.select_related(
                            "documento_requerido"
                        ).all()
                    ],
                }
            )

    return JsonResponse({"documentos": documentos_data})
