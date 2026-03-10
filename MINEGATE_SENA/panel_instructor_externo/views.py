from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from visitaExterna.models import VisitaExterna
from .forms import VisitaExternaInstructorForm
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


# ==================== AUTENTICACIÓN POR SESIÓN ====================


def get_sesion_instructor(request):
    """
    Lee los datos de sesión del panel_visitante.
    Retorna (correo, documento) o (None, None) si no está autenticado como externo.
    """
    if not request.session.get("responsable_autenticado"):
        return None, None
    if request.session.get("responsable_rol") != "externo":
        return None, None
    correo = request.session.get("responsable_correo")
    documento = request.session.get("responsable_documento")
    if not correo or not documento:
        return None, None
    return correo, documento


def instructor_externo_required(view_func):
    """
    Decorador: verifica sesión de panel_visitante con rol externo.
    """

    def wrapper(request, *args, **kwargs):
        correo, documento = get_sesion_instructor(request)
        if not correo:
            messages.warning(
                request,
                "Debes iniciar sesión como usuario externo para acceder a este panel.",
            )
            return redirect("panel_visitante:login_responsable")
        return view_func(request, *args, **kwargs)

    return wrapper


# ==================== PANEL PRINCIPAL ====================


@instructor_externo_required
def panel_instructor_externo(request):
    correo, documento = get_sesion_instructor(request)
    visitas = VisitaExterna.objects.filter(correo_responsable__iexact=correo).order_by(
        "-fecha_solicitud"
    )
    context = {
        "correo": correo,
        "documento": documento,
        "nombre": request.session.get("responsable_nombre", ""),
        "apellido": request.session.get("responsable_apellido", ""),
        "visitas": visitas,
        "total_visitas": visitas.count(),
        "visitas_pendientes": visitas.filter(estado="pendiente").count(),
        "visitas_confirmadas": visitas.filter(estado="confirmada").count(),
    }
    return render(request, "panel_instructor_externo/panel.html", context)


# ==================== MÓDULO: RESERVAR VISITA EXTERNA ====================


@instructor_externo_required
def reservar_visita_externa(request):
    correo, documento = get_sesion_instructor(request)

    # Obtener datos adicionales de la sesión
    nombre = request.session.get("responsable_nombre", "")
    apellido = request.session.get("responsable_apellido", "")
    tipo_documento = request.session.get("responsable_tipo_documento", "CC")
    telefono = request.session.get("responsable_telefono", "")
    nombre_completo = f"{nombre} {apellido}".strip()

    if request.method == "POST":
        form = VisitaExternaInstructorForm(request.POST)
        if form.is_valid():
            visita = form.save(commit=False)
            visita.correo_responsable = correo
            visita.documento_responsable = documento
            visita.estado = "enviada_coordinacion"
            visita.save()
            # Enviar correo HTML de confirmación al responsable
            try:
                subject = "Confirmación: solicitud de visita enviada"
                context = {
                    "responsable_nombre": nombre_completo,
                    "nombre_responsable": visita.nombre_responsable,
                    "documento_responsable": visita.documento_responsable,
                    "nombre": visita.nombre,
                    "fecha_solicitud": visita.fecha_solicitud.strftime(
                        "%d/%m/%Y %H:%M"
                    ),
                    "hora_programada": (
                        (
                            visita.hora_inicio.strftime("%I:%M %p")
                            + " - "
                            + visita.hora_fin.strftime("%I:%M %p")
                        )
                        if visita.hora_inicio and visita.hora_fin
                        else "Por definir"
                    ),
                    "sede": getattr(visita, "sede", "No especificada"),
                }
                html_content = render_to_string(
                    "emails/solicitud_visita_externa.html", context
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

            messages.success(
                request,
                "✅ Solicitud de visita externa enviada. Queda pendiente de aprobación por coordinación.",
            )
            return redirect("panel_instructor_externo:panel")
    else:
        form = VisitaExternaInstructorForm(
            initial={
                "nombre_responsable": nombre_completo,
                "tipo_documento_responsable": tipo_documento,
                "documento_responsable": documento,
                "correo_responsable": correo,
                "telefono_responsable": telefono,
            }
        )
    context = {"form": form, "correo": correo, "titulo": "Reservar Visita Externa"}
    return render(request, "panel_instructor_externo/reservar_visita.html", context)


@instructor_externo_required
def detalle_visita_externa(request, pk):
    correo, _ = get_sesion_instructor(request)
    visita = get_object_or_404(VisitaExterna, pk=pk, correo_responsable__iexact=correo)

    # Obtener documentos disponibles para descargar, agrupados por categoría
    from documentos.models import Documento

    documentos_disponibles = Documento.objects.all().order_by(
        "categoria", "-fecha_subida"
    )
    documentos_por_categoria = {}
    for doc in documentos_disponibles:
        cat_display = doc.get_categoria_display()
        if cat_display not in documentos_por_categoria:
            documentos_por_categoria[cat_display] = []
        documentos_por_categoria[cat_display].append(doc)

    return render(
        request,
        "panel_instructor_externo/detalle_visita.html",
        {
            "visita": visita,
            "correo": correo,
            "documentos_por_categoria": documentos_por_categoria,
        },
    )
