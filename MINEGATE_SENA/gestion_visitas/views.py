"""
App: gestion_visitas
Gestión administrativa de visitas - APIs para el panel administrativo
"""

import threading
from types import SimpleNamespace

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db import close_old_connections

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
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from gestion_visitas.services import GeneradorQRPDF
from core.sanitization import sanitize_text, sanitize_token

ESTADOS_APROBADAS = [
    "aprobada_inicial",
    "documentos_enviados",
    "en_revision_documentos",
    "confirmada",
]


def _enviar_qr_asistentes_confirmados(visita, tipo):
    for asistente in visita.asistentes.filter(estado="documentos_aprobados"):
        if asistente.qr_generado or asistente.email_qr_enviado:
            continue

        if not asistente.correo:
            continue

        try:
            generador_qr = GeneradorQRPDF(
                asistente=asistente,
                visita=visita,
                tipo_visita=tipo,
            )
            if generador_qr.enviar_por_email():
                asistente.qr_generado = True
                asistente.email_qr_enviado = True
                asistente.fecha_envio_qr = timezone.now()
                asistente.save(
                    update_fields=[
                        "qr_generado",
                        "email_qr_enviado",
                        "fecha_envio_qr",
                    ]
                )
        except Exception:
            continue


def _enviar_qr_responsable_confirmado(visita, tipo):
    correo = (getattr(visita, "correo_responsable", "") or "").strip()
    documento = (getattr(visita, "documento_responsable", "") or "").strip()
    if not correo or not documento:
        return

    if tipo == "interna":
        nombre_responsable = (getattr(visita, "responsable", "") or "").strip()
    else:
        nombre_responsable = (
            getattr(visita, "nombre_responsable", "") or ""
        ).strip()

    if not nombre_responsable:
        return

    try:
        responsable_virtual = SimpleNamespace(
            nombre_completo=nombre_responsable,
            numero_documento=documento,
            correo=correo,
        )
        generador_qr = GeneradorQRPDF(
            asistente=responsable_virtual,
            visita=visita,
            tipo_visita=tipo,
        )
        generador_qr.enviar_por_email()
    except Exception:
        pass


def _enviar_correo_confirmacion_responsable(visita, tipo, panel_url):
    try:
        if tipo == "interna":
            template_name = "emails/visita_confirmada_interna.html"
        else:
            template_name = "emails/visita_confirmada_externa.html"

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


def _enviar_correo_correccion_documentos_asistente(request, asistente, tipo, observaciones):
    """Notifica al responsable que debe corregir documentos de un asistente."""
    try:
        visita = asistente.visita
        correo_destino = (getattr(visita, "correo_responsable", "") or "").strip()
        if not correo_destino:
            return

        if getattr(visita, "token_acceso", None):
            panel_path = reverse(
                "documentos:registro_publico_interna" if tipo == "interna" else "documentos:registro_publico_externa",
                kwargs={"token": visita.token_acceso},
            )
        else:
            panel_path = reverse(
                "panel_instructor_interno:panel" if tipo == "interna" else "panel_instructor_externo:panel"
            )

        context = {
            "responsable_nombre": (
                getattr(visita, "responsable", "")
                if tipo == "interna"
                else getattr(visita, "nombre_responsable", "")
            )
            or "Responsable",
            "tipo_visita": "Interna" if tipo == "interna" else "Externa",
            "visita_id": visita.id,
            "asistente_nombre": asistente.nombre_completo,
            "documento_titulo": "Documentos del asistente",
            "observaciones": observaciones or "Sin observaciones registradas.",
            "fecha_revision": timezone.now().strftime("%d/%m/%Y %H:%M"),
            "panel_url": request.build_absolute_uri(panel_path),
        }

        html_content = render_to_string("emails/documento_rechazado_correccion.html", context)
        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(
            f"Accion requerida: correccion de documentos ({context['tipo_visita']})",
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [correo_destino],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=True)
    except Exception:
        pass


def _procesar_confirmacion_visita_async(visita_id, tipo, panel_url):
    close_old_connections()
    try:
        visita_model = VisitaInterna if tipo == "interna" else VisitaExterna
        visita = visita_model.objects.prefetch_related("asistentes").get(id=visita_id)
        _enviar_qr_asistentes_confirmados(visita, tipo)
        _enviar_qr_responsable_confirmado(visita, tipo)
        _enviar_correo_confirmacion_responsable(visita, tipo, panel_url)
    except Exception:
        pass
    finally:
        close_old_connections()


def es_coordinador(user):
    return user.groups.filter(name="coordinador").exists()


def es_usuario_sst(user):
    return user.is_staff and not user.is_superuser and not es_coordinador(user)


def es_administrador_panel(user):
    return user.is_superuser or (user.is_staff and not es_coordinador(user))


def devolver_visita_a_agendador(visita):
    """Retorna la visita a estado editable para permitir correcciones y reenvío."""
    if visita.estado in ["documentos_enviados", "en_revision_documentos"]:
        visita.estado = "aprobada_inicial"
        visita.save(update_fields=["estado"])


def _documentos_subidos_actuales(asistente):
    """Retorna la última versión por documento y metadatos de reenvío."""
    docs = asistente.documentos_subidos.select_related("documento_requerido").order_by(
        "documento_requerido_id", "-fecha_subida", "-id"
    )
    latest_por_documento = {}
    conteo_por_documento = {}
    for ds in docs:
        conteo_por_documento[ds.documento_requerido_id] = (
            conteo_por_documento.get(ds.documento_requerido_id, 0) + 1
        )
        if ds.documento_requerido_id not in latest_por_documento:
            latest_por_documento[ds.documento_requerido_id] = ds

    documentos_actuales = []
    for doc_id, ds in latest_por_documento.items():
        versiones_envio = conteo_por_documento.get(doc_id, 1)
        documentos_actuales.append(
            {
                "ds": ds,
                "versiones_envio": versiones_envio,
                "es_reenvio": versiones_envio > 1,
            }
        )
    return documentos_actuales


def _normalizar_categoria_documento(categoria):
    return (
        str(categoria or "")
        .strip()
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )


def _es_categoria_archivo_final(categoria):
    categoria_normalizada = _normalizar_categoria_documento(categoria)
    return categoria_normalizada in {
        "ats",
        "formato induccion y reinduccion",
        "charla de seguridad y calestenia",
        "charla de seguridad y calistenia",
    }


def _serializar_documento_subido(ds, versiones_envio=1, es_reenvio=False):
    return {
        "id": ds.id,
        "titulo": ds.documento_requerido.titulo,
        "categoria": ds.documento_requerido.get_categoria_display(),
        "url": f"/documentos/ver-asistente/{ds.id}/",
        "download_url": f"/documentos/descargar-asistente/{ds.id}/",
        "estado": ds.estado,
        "observaciones_revision": ds.observaciones_revision or "",
        "nombre_archivo": ds.nombre_archivo,
        "fecha_subida": (
            ds.fecha_subida.strftime("%d/%m/%Y %H:%M") if ds.fecha_subida else None
        ),
        "versiones_envio": versiones_envio,
        "es_reenvio": es_reenvio,
    }


def _calcular_estado_revision_asistente(asistente):
    """Calcula estado agregado del asistente en función de sus últimos documentos."""
    documentos_actuales = _documentos_subidos_actuales(asistente)
    documentos_personales = [
        doc_actual
        for doc_actual in documentos_actuales
        if not _es_categoria_archivo_final(
            doc_actual["ds"].documento_requerido.categoria
        )
    ]
    tiene_docs = bool(documentos_personales)
    tiene_rechazos = any(
        doc_actual["ds"].estado == "rechazado" for doc_actual in documentos_personales
    )
    todos_aprobados = tiene_docs and all(
        doc_actual["ds"].estado == "aprobado" for doc_actual in documentos_personales
    )

    tiene_autorizacion_padres = bool(
        getattr(asistente, "formato_autorizacion_padres", None)
    )
    if tiene_autorizacion_padres:
        estado_autorizacion = getattr(
            asistente, "estado_autorizacion_padres", "pendiente"
        )
        if estado_autorizacion == "rechazado":
            tiene_rechazos = True
        elif estado_autorizacion != "aprobado":
            todos_aprobados = False

    if tiene_rechazos:
        estado = "documentos_rechazados"
    elif todos_aprobados and (tiene_docs or tiene_autorizacion_padres):
        estado = "documentos_aprobados"
    else:
        estado = "pendiente_documentos"

    return {
        "estado": estado,
        "tiene_rechazos": tiene_rechazos,
        "todos_aprobados": todos_aprobados,
    }


def _sincronizar_estado_asistente(asistente, observacion_rechazo=""):
    """Sincroniza el estado agregado del asistente con el estado real de sus documentos."""
    revision = _calcular_estado_revision_asistente(asistente)
    update_fields = []

    if asistente.estado != revision["estado"]:
        asistente.estado = revision["estado"]
        update_fields.append("estado")

    if revision["estado"] == "documentos_rechazados":
        nueva_observacion = (observacion_rechazo or "").strip() or (
            asistente.observaciones_revision or ""
        )
        if nueva_observacion and asistente.observaciones_revision != nueva_observacion:
            asistente.observaciones_revision = nueva_observacion
            update_fields.append("observaciones_revision")
    elif asistente.observaciones_revision:
        asistente.observaciones_revision = ""
        update_fields.append("observaciones_revision")

    if update_fields:
        asistente.save(update_fields=update_fields)

    return revision


def _marcar_documentos_actuales(asistente, estado, observaciones=""):
    """Marca la última versión de cada documento subido por el asistente."""
    for doc_actual in _documentos_subidos_actuales(asistente):
        ds = doc_actual["ds"]
        ds.estado = estado
        ds.observaciones_revision = observaciones if estado == "rechazado" else ""
        ds.save(update_fields=["estado", "observaciones_revision"])


def _formatear_fecha_visita(visita, incluir_hora=False):
    """Retorna la fecha programada real de la visita (incluye reprogramaciones)."""
    fecha_programada = getattr(visita, "fecha_visita", None)
    if fecha_programada:
        fecha_txt = fecha_programada.strftime("%d/%m/%Y")
    elif getattr(visita, "fecha_solicitud", None):
        fecha_txt = visita.fecha_solicitud.strftime("%d/%m/%Y")
    else:
        return "N/A"

    if incluir_hora:
        hora_inicio = getattr(visita, "hora_inicio", None)
        hora_fin = getattr(visita, "hora_fin", None)
        if hora_inicio and hora_fin:
            return (
                f"{fecha_txt} "
                f"{hora_inicio.strftime('%H:%M')} - {hora_fin.strftime('%H:%M')}"
            )
        if hora_inicio:
            return f"{fecha_txt} {hora_inicio.strftime('%H:%M')}"

    return fecha_txt


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

    tipo = sanitize_token(request.GET.get("tipo", "internas"), max_length=20) or "internas"
    estado = sanitize_token(request.GET.get("estado", "todos"), max_length=30) or "todos"
    buscar = sanitize_text(request.GET.get("buscar", ""), max_length=100, allow_newlines=False)

    visitas_data = []

    if tipo == "todas":
        visitas_internas = VisitaInterna.objects.all().order_by("-fecha_solicitud", "-id")
        visitas_externas = VisitaExterna.objects.all().order_by("-fecha_solicitud", "-id")

        if estado == "aprobadas":
            visitas_internas = visitas_internas.filter(estado__in=ESTADOS_APROBADAS)
            visitas_externas = visitas_externas.filter(estado__in=ESTADOS_APROBADAS)
        elif estado in ["en_revision_documentos", "pendiente_revision"]:
            estados_revision = ["documentos_enviados", "en_revision_documentos"]
            visitas_internas = visitas_internas.filter(estado__in=estados_revision)
            visitas_externas = visitas_externas.filter(estado__in=estados_revision)
        elif estado != "todos":
            visitas_internas = visitas_internas.filter(estado=estado)
            visitas_externas = visitas_externas.filter(estado=estado)

        if buscar:
            visitas_internas = visitas_internas.filter(
                Q(responsable__icontains=buscar)
                | Q(nombre_programa__icontains=buscar)
                | Q(correo_responsable__icontains=buscar)
            )
            visitas_externas = visitas_externas.filter(
                Q(nombre_responsable__icontains=buscar)
                | Q(nombre__icontains=buscar)
                | Q(correo_responsable__icontains=buscar)
            )

        for v in visitas_internas:
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
                        v.fecha_visita.strftime("%d/%m/%Y")
                        if v.fecha_visita
                        else (
                            v.fecha_solicitud.strftime("%d/%m/%Y")
                            if v.fecha_solicitud
                            else "N/A"
                        )
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
                    "_orden": v.fecha_solicitud.isoformat() if v.fecha_solicitud else "",
                }
            )

        for v in visitas_externas:
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
                        v.fecha_visita.strftime("%d/%m/%Y")
                        if v.fecha_visita
                        else (
                            v.fecha_solicitud.strftime("%d/%m/%Y")
                            if v.fecha_solicitud
                            else "N/A"
                        )
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
                    "_orden": v.fecha_solicitud.isoformat() if v.fecha_solicitud else "",
                }
            )

        visitas_data.sort(key=lambda item: item.get("_orden", ""), reverse=True)
        for item in visitas_data:
            item.pop("_orden", None)

        docs_int = AsistenteVisitaInterna.objects.exclude(
            visita__estado__in=["aprobada_inicial", "pendiente", "enviada_coordinacion"]
        )
        docs_ext = AsistenteVisitaExterna.objects.exclude(
            visita__estado__in=["aprobada_inicial", "pendiente", "enviada_coordinacion"]
        )

        stats = {
            "pendientes": (
                VisitaInterna.objects.filter(estado="pendiente").count()
                + VisitaExterna.objects.filter(estado="pendiente").count()
            ),
            "aprobadas_inicial": (
                VisitaInterna.objects.filter(estado="aprobada_inicial").count()
                + VisitaExterna.objects.filter(estado="aprobada_inicial").count()
            ),
            "aprobadas_total": (
                VisitaInterna.objects.filter(estado__in=ESTADOS_APROBADAS).count()
                + VisitaExterna.objects.filter(estado__in=ESTADOS_APROBADAS).count()
            ),
            "documentos_enviados": (
                VisitaInterna.objects.filter(estado="documentos_enviados").count()
                + VisitaExterna.objects.filter(estado="documentos_enviados").count()
            ),
            "en_revision": (
                VisitaInterna.objects.filter(estado="en_revision_documentos").count()
                + VisitaExterna.objects.filter(estado="en_revision_documentos").count()
            ),
            "confirmadas": (
                VisitaInterna.objects.filter(estado="confirmada").count()
                + VisitaExterna.objects.filter(estado="confirmada").count()
            ),
            "rechazadas": (
                VisitaInterna.objects.filter(estado="rechazada").count()
                + VisitaExterna.objects.filter(estado="rechazada").count()
            ),
            "docs_pendientes_revision": (
                docs_int.filter(estado="pendiente_documentos").count()
                + docs_ext.filter(estado="pendiente_documentos").count()
            ),
            "docs_aprobados": (
                docs_int.filter(estado="documentos_aprobados").count()
                + docs_ext.filter(estado="documentos_aprobados").count()
            ),
            "docs_rechazados": (
                docs_int.filter(estado="documentos_rechazados").count()
                + docs_ext.filter(estado="documentos_rechazados").count()
            ),
            "docs_total": docs_int.count() + docs_ext.count(),
            "total": len(visitas_data),
        }

        return JsonResponse(
            {
                "visitas": visitas_data,
                "stats": stats,
            }
        )

    if tipo == "internas":
        visitas = VisitaInterna.objects.all().order_by("-fecha_solicitud", "-id")

        if estado == "aprobadas":
            visitas = visitas.filter(estado__in=ESTADOS_APROBADAS)
        elif estado in ["en_revision_documentos", "pendiente_revision"]:
            visitas = visitas.filter(
                estado__in=["documentos_enviados", "en_revision_documentos"]
            )
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
                        v.fecha_visita.strftime("%d/%m/%Y")
                        if v.fecha_visita
                        else (
                            v.fecha_solicitud.strftime("%d/%m/%Y")
                            if v.fecha_solicitud
                            else "N/A"
                        )
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
        elif estado in ["en_revision_documentos", "pendiente_revision"]:
            visitas = visitas.filter(
                estado__in=["documentos_enviados", "en_revision_documentos"]
            )
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
                        v.fecha_visita.strftime("%d/%m/%Y")
                        if v.fecha_visita
                        else (
                            v.fecha_solicitud.strftime("%d/%m/%Y")
                            if v.fecha_solicitud
                            else "N/A"
                        )
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
                documentos_actuales = _documentos_subidos_actuales(a)
                revision = _sincronizar_estado_asistente(a)
                asistentes.append(
                    {
                        "id": a.id,
                        "nombre_completo": a.nombre_completo,
                        "tipo_documento": a.tipo_documento,
                        "numero_documento": a.numero_documento,
                        "correo": a.correo,
                        "telefono": a.telefono,
                        "estado": revision["estado"],
                        "documento_identidad": (
                            reverse(
                                "documentos:ver_campo_asistente_inline",
                                kwargs={
                                    "tipo": "interna",
                                    "asistente_id": a.id,
                                    "campo": "documento_identidad",
                                },
                            )
                            if a.documento_identidad
                            else None
                        ),
                        "documento_identidad_nombre": (
                            a.documento_identidad.name.split("/")[-1]
                            if a.documento_identidad
                            else None
                        ),
                        "documento_adicional": (
                            reverse(
                                "documentos:ver_campo_asistente_inline",
                                kwargs={
                                    "tipo": "interna",
                                    "asistente_id": a.id,
                                    "campo": "documento_adicional",
                                },
                            )
                            if a.documento_adicional
                            else None
                        ),
                        "documento_adicional_nombre": (
                            a.documento_adicional.name.split("/")[-1]
                            if a.documento_adicional
                            else None
                        ),
                        "formato_autorizacion_padres": (
                            reverse(
                                "documentos:ver_campo_asistente_inline",
                                kwargs={
                                    "tipo": "interna",
                                    "asistente_id": a.id,
                                    "campo": "formato_autorizacion_padres",
                                },
                            )
                            if a.formato_autorizacion_padres
                            else None
                        ),
                        "formato_autorizacion_padres_nombre": (
                            a.formato_autorizacion_padres.name.split("/")[-1]
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
                        "observaciones_revision": (
                            a.observaciones_revision
                            if revision["estado"] == "documentos_rechazados"
                            else ""
                        ),
                        "tiene_rechazos": revision["tiene_rechazos"],
                        "todos_aprobados": revision["todos_aprobados"],
                        "documentos_subidos": [
                            _serializar_documento_subido(
                                doc_actual["ds"],
                                versiones_envio=doc_actual["versiones_envio"],
                                es_reenvio=doc_actual["es_reenvio"],
                            )
                            for doc_actual in documentos_actuales
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
                visita.fecha_visita.strftime("%d/%m/%Y")
                if visita.fecha_visita
                else (
                    visita.fecha_solicitud.strftime("%d/%m/%Y")
                    if visita.fecha_solicitud
                    else "N/A"
                )
            ),
            "estado": visita.estado,
            "observaciones": visita.observaciones or "",
            "fecha_solicitud": (
                visita.fecha_solicitud.strftime("%d/%m/%Y %H:%M")
                if visita.fecha_solicitud
                else "N/A"
            ),
            "fecha_registro": (
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
                documentos_actuales = _documentos_subidos_actuales(a)
                revision = _sincronizar_estado_asistente(a)
                asistentes.append(
                    {
                        "id": a.id,
                        "nombre_completo": a.nombre_completo,
                        "tipo_documento": a.tipo_documento,
                        "numero_documento": a.numero_documento,
                        "correo": a.correo,
                        "telefono": a.telefono,
                        "estado": revision["estado"],
                        "documento_identidad": (
                            reverse(
                                "documentos:ver_campo_asistente_inline",
                                kwargs={
                                    "tipo": "externa",
                                    "asistente_id": a.id,
                                    "campo": "documento_identidad",
                                },
                            )
                            if a.documento_identidad
                            else None
                        ),
                        "documento_identidad_nombre": (
                            a.documento_identidad.name.split("/")[-1]
                            if a.documento_identidad
                            else None
                        ),
                        "documento_adicional": (
                            reverse(
                                "documentos:ver_campo_asistente_inline",
                                kwargs={
                                    "tipo": "externa",
                                    "asistente_id": a.id,
                                    "campo": "documento_adicional",
                                },
                            )
                            if a.documento_adicional
                            else None
                        ),
                        "documento_adicional_nombre": (
                            a.documento_adicional.name.split("/")[-1]
                            if a.documento_adicional
                            else None
                        ),
                        "formato_autorizacion_padres": (
                            reverse(
                                "documentos:ver_campo_asistente_inline",
                                kwargs={
                                    "tipo": "externa",
                                    "asistente_id": a.id,
                                    "campo": "formato_autorizacion_padres",
                                },
                            )
                            if a.formato_autorizacion_padres
                            else None
                        ),
                        "formato_autorizacion_padres_nombre": (
                            a.formato_autorizacion_padres.name.split("/")[-1]
                            if a.formato_autorizacion_padres
                            else None
                        ),
                        "observaciones_revision": (
                            a.observaciones_revision
                            if revision["estado"] == "documentos_rechazados"
                            else ""
                        ),
                        "tiene_rechazos": revision["tiene_rechazos"],
                        "todos_aprobados": revision["todos_aprobados"],
                        "documentos_subidos": [
                            _serializar_documento_subido(
                                doc_actual["ds"],
                                versiones_envio=doc_actual["versiones_envio"],
                                es_reenvio=doc_actual["es_reenvio"],
                            )
                            for doc_actual in documentos_actuales
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
                visita.fecha_visita.strftime("%d/%m/%Y")
                if visita.fecha_visita
                else (
                    visita.fecha_solicitud.strftime("%d/%m/%Y")
                    if visita.fecha_solicitud
                    else "N/A"
                )
            ),
            "estado": visita.estado,
            "observaciones": visita.observacion or "",
            "fecha_solicitud": (
                visita.fecha_solicitud.strftime("%d/%m/%Y %H:%M")
                if visita.fecha_solicitud
                else "N/A"
            ),
            "fecha_registro": (
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

    if es_usuario_sst(request.user):
        return JsonResponse(
            {
                "success": False,
                "error": "El rol SST solo puede revisar documentos. No puede aprobar, rechazar, reprogramar ni confirmar visitas.",
            },
            status=403,
        )

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
                panel_path = reverse("panel_instructor_interno:panel")
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
        observaciones = sanitize_text(
            request.POST.get("observaciones", ""),
            max_length=1000,
            allow_newlines=True,
        )

        if es_coordinador(request.user):
            if visita.estado != "enviada_coordinacion":
                return JsonResponse(
                    {
                        "success": False,
                        "error": "La visita no está pendiente de revisión por coordinación",
                    }
                )
        elif es_administrador_panel(request.user):
            if visita.estado not in [
                "pendiente",
                "documentos_enviados",
                "en_revision_documentos",
            ]:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "La visita no está en un estado válido para rechazo (pendiente o en revisión de documentos)",
                    }
                )
        else:
            return JsonResponse(
                {"success": False, "error": "No autorizado para rechazar esta visita"},
                status=403,
            )

        visita.estado = "rechazada"
        visita.save()
        ReservaHorario.liberar_reserva(visita, tipo)
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

        if tipo == "interna":
            panel_path = reverse("panel_instructor_interno:panel")
        else:
            panel_path = reverse("panel_instructor_externo:panel")

        panel_url = request.build_absolute_uri(panel_path)

        threading.Thread(
            target=_procesar_confirmacion_visita_async,
            args=(visita.id, tipo, panel_url),
            daemon=True,
        ).start()

        registrar_accion(
            "confirmacion",
            f"Visita confirmada definitivamente por {request.user.username}",
        )
        return JsonResponse(
            {
                "success": True,
                "message": "✅ Visita confirmada exitosamente.",
            }
        )

    elif accion == "devolver_correccion":
        if not es_administrador_panel(request.user):
            return JsonResponse(
                {"success": False, "error": "No autorizado para esta acción"},
                status=403,
            )

        if visita.estado not in ["documentos_enviados", "en_revision_documentos"]:
            return JsonResponse(
                {
                    "success": False,
                    "error": "La visita debe estar en revisión de documentos para devolverla a corrección",
                }
            )

        asistentes_rechazados = visita.asistentes.filter(
            estado="documentos_rechazados"
        ).count()
        if asistentes_rechazados == 0:
            return JsonResponse(
                {
                    "success": False,
                    "error": "No hay aprendices con documentos rechazados para devolver a corrección.",
                }
            )

        devolver_visita_a_agendador(visita)
        registrar_accion(
            "devolucion_correccion",
            f"Visita devuelta a corrección por {request.user.username}. Aprendices con rechazo: {asistentes_rechazados}.",
        )
        return JsonResponse(
            {
                "success": True,
                "message": f"⚠️ Se devolvió la visita al instructor para corregir y volver a subir documentos ({asistentes_rechazados} aprendiz(es) con rechazo).",
            }
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

    observaciones = sanitize_text(
        request.POST.get("observaciones", ""),
        max_length=1000,
        allow_newlines=True,
    )

    if asistente.estado_autorizacion_padres != "pendiente":
        return JsonResponse(
            {
                "success": False,
                "error": "La autorización de padres ya fue revisada. Solo puede gestionar documentos en revisión.",
            },
            status=409,
        )

    if accion == "aprobar":
        asistente.estado_autorizacion_padres = "aprobado"
        asistente.observaciones_autorizacion_padres = observaciones
        asistente.save(
            update_fields=[
                "estado_autorizacion_padres",
                "observaciones_autorizacion_padres",
            ]
        )
        revision = _sincronizar_estado_asistente(asistente)
        return JsonResponse(
            {
                "success": True,
                "message": f"✅ Autorización de padres aprobada para {asistente.nombre_completo}",
                "nuevo_estado": revision["estado"],
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
        asistente.save(
            update_fields=[
                "estado_autorizacion_padres",
                "observaciones_autorizacion_padres",
            ]
        )
        revision = _sincronizar_estado_asistente(
            asistente,
            observacion_rechazo=f"Autorización de padres rechazada: {observaciones}",
        )
        _enviar_correo_correccion_documentos_asistente(
            request,
            asistente,
            tipo,
            f"Autorizacion de padres rechazada: {observaciones}",
        )
        return JsonResponse(
            {
                "success": True,
                "message": f"❌ Autorización de padres rechazada para {asistente.nombre_completo}. Queda pendiente de corrección.",
                "nuevo_estado": revision["estado"],
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

    observaciones = sanitize_text(
        request.POST.get("observaciones", ""),
        max_length=1000,
        allow_newlines=True,
    )

    if accion == "aprobar":
        documentos_actuales = _documentos_subidos_actuales(asistente)

        if not documentos_actuales and not asistente.formato_autorizacion_padres:
            return JsonResponse(
                {
                    "success": False,
                    "error": "El asistente no tiene documentos cargados para aprobar.",
                }
            )

        # Restricción: No se puede aprobar masivamente si la última versión tiene rechazos
        if any(
            doc_actual["ds"].estado == "rechazado" for doc_actual in documentos_actuales
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": "No se puede aprobar masivamente porque hay documentos rechazados. Corrija o apruebe individualmente.",
                }
            )

        if any(
            doc_actual["ds"].estado != "aprobado" for doc_actual in documentos_actuales
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Debe aprobar individualmente todos los documentos antes de la aprobación final del asistente.",
                }
            )

        if (
            asistente.formato_autorizacion_padres
            and asistente.estado_autorizacion_padres != "aprobado"
        ):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Debe revisar y aprobar la autorización de padres antes de aprobar al asistente.",
                }
            )

        asistente.estado = "documentos_aprobados"
        asistente.observaciones_revision = ""
        asistente.save(update_fields=["estado", "observaciones_revision"])
        revision = _sincronizar_estado_asistente(asistente)
        return JsonResponse(
            {
                "success": True,
                "message": f"✅ Documentos de {asistente.nombre_completo} aprobados",
                "nuevo_estado": revision["estado"],
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

        documentos_actuales = _documentos_subidos_actuales(asistente)
        if not documentos_actuales and not asistente.formato_autorizacion_padres:
            return JsonResponse(
                {
                    "success": False,
                    "error": "El asistente no tiene documentos cargados para rechazar.",
                }
            )

        _marcar_documentos_actuales(asistente, "rechazado", observaciones)

        if (
            asistente.formato_autorizacion_padres
            and asistente.estado_autorizacion_padres != "aprobado"
        ):
            asistente.estado_autorizacion_padres = "rechazado"
            asistente.observaciones_autorizacion_padres = observaciones
            asistente.save(
                update_fields=[
                    "estado_autorizacion_padres",
                    "observaciones_autorizacion_padres",
                ]
            )

        revision = _sincronizar_estado_asistente(
            asistente,
            observacion_rechazo=observaciones,
        )
        _enviar_correo_correccion_documentos_asistente(
            request,
            asistente,
            tipo,
            observaciones,
        )
        return JsonResponse(
            {
                "success": True,
                "message": f"❌ Documentos de {asistente.nombre_completo} rechazados. Queda pendiente de corrección.",
                "nuevo_estado": revision["estado"],
            }
        )

    return JsonResponse({"success": False, "error": "Acción no válida"})


@login_required(login_url="usuarios:login")
def api_visitas_aprobadas(request):
    """API para listar visitas aprobadas (para mostrarVisitasAprobadas en el JS)"""
    if not es_administrador_panel(request.user):
        return JsonResponse({"success": False, "error": "No autorizado"}, status=403)

    tipo = sanitize_token(request.GET.get("tipo", "internas"), max_length=20) or "internas"
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

    tipo = sanitize_token(request.GET.get("tipo", "internas"), max_length=20) or "internas"
    estado_asistente = sanitize_token(request.GET.get("estado_asistente", ""), max_length=40)

    documentos_data = []

    if tipo == "internas":
        qs = AsistenteVisitaInterna.objects.select_related("visita").all()
        if estado_asistente:
            if estado_asistente == "revision_activa":
                qs = qs.filter(
                    estado__in=["pendiente_documentos", "documentos_rechazados"]
                )
            else:
                qs = qs.filter(estado=estado_asistente)
        for a in qs:
            documentos_actuales = _documentos_subidos_actuales(a)
            revision = _sincronizar_estado_asistente(a)
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
                    "estado": revision["estado"],
                    "documento_identidad": (
                        reverse(
                            "documentos:ver_campo_asistente_inline",
                            kwargs={
                                "tipo": "interna",
                                "asistente_id": a.id,
                                "campo": "documento_identidad",
                            },
                        )
                        if a.documento_identidad
                        else None
                    ),
                    "documento_identidad_nombre": (
                        a.documento_identidad.name.split("/")[-1]
                        if a.documento_identidad
                        else None
                    ),
                    "documento_adicional": (
                        reverse(
                            "documentos:ver_campo_asistente_inline",
                            kwargs={
                                "tipo": "interna",
                                "asistente_id": a.id,
                                "campo": "documento_adicional",
                            },
                        )
                        if a.documento_adicional
                        else None
                    ),
                    "documento_adicional_nombre": (
                        a.documento_adicional.name.split("/")[-1]
                        if a.documento_adicional
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
                    "observaciones_revision": (
                        a.observaciones_revision
                        if revision["estado"] == "documentos_rechazados"
                        else ""
                    ),
                    "tiene_rechazos": revision["tiene_rechazos"],
                    "todos_aprobados": revision["todos_aprobados"],
                    "documentos_subidos": [
                        _serializar_documento_subido(
                            doc_actual["ds"],
                            versiones_envio=doc_actual["versiones_envio"],
                            es_reenvio=doc_actual["es_reenvio"],
                        )
                        for doc_actual in documentos_actuales
                    ],
                }
            )
    else:
        qs = AsistenteVisitaExterna.objects.select_related("visita").all()
        if estado_asistente:
            if estado_asistente == "revision_activa":
                qs = qs.filter(
                    estado__in=["pendiente_documentos", "documentos_rechazados"]
                )
            else:
                qs = qs.filter(estado=estado_asistente)
        for a in qs:
            documentos_actuales = _documentos_subidos_actuales(a)
            revision = _sincronizar_estado_asistente(a)
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
                    "estado": revision["estado"],
                    "documento_identidad": (
                        reverse(
                            "documentos:ver_campo_asistente_inline",
                            kwargs={
                                "tipo": "externa",
                                "asistente_id": a.id,
                                "campo": "documento_identidad",
                            },
                        )
                        if a.documento_identidad
                        else None
                    ),
                    "documento_identidad_nombre": (
                        a.documento_identidad.name.split("/")[-1]
                        if a.documento_identidad
                        else None
                    ),
                    "documento_adicional": (
                        reverse(
                            "documentos:ver_campo_asistente_inline",
                            kwargs={
                                "tipo": "externa",
                                "asistente_id": a.id,
                                "campo": "documento_adicional",
                            },
                        )
                        if a.documento_adicional
                        else None
                    ),
                    "documento_adicional_nombre": (
                        a.documento_adicional.name.split("/")[-1]
                        if a.documento_adicional
                        else None
                    ),
                    "observaciones_revision": (
                        a.observaciones_revision
                        if revision["estado"] == "documentos_rechazados"
                        else ""
                    ),
                    "tiene_rechazos": revision["tiene_rechazos"],
                    "todos_aprobados": revision["todos_aprobados"],
                    "documentos_subidos": [
                        _serializar_documento_subido(
                            doc_actual["ds"],
                            versiones_envio=doc_actual["versiones_envio"],
                            es_reenvio=doc_actual["es_reenvio"],
                        )
                        for doc_actual in documentos_actuales
                    ],
                }
            )

    return JsonResponse({"documentos": documentos_data})
