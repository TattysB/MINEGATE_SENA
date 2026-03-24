from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from visitaExterna.models import (
    HistorialReprogramacion,
    HistorialAccionVisitaExterna,
    VisitaExterna,
)
from .forms import VisitaExternaInstructorForm
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from calendario.models import ReservaHorario
from documentos.models import Documento, DocumentoSubidoAsistente


CATEGORIA_DOC_SALUD = "Formato Auto Reporte Condiciones de Salud"
CATEGORIAS_ARCHIVOS_FINALES = [
    "ATS",
    "Formato Inducción y Reinducción",
    "Charla de Seguridad y Calestenia",
]
MARCADOR_SOLICITUD_FINAL_ENVIADA = "[SOLICITUD_FINAL_ENVIADA]"


def _normalizar_categoria_texto(value):
    return (
        str(value or "")
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )


def construir_reporte_documental_visita(visita, tipo_visita):
    """Genera un resumen de faltantes y rechazos por asistente y archivos finales."""
    doc_salud_ids = set(
        Documento.objects.filter(categoria=CATEGORIA_DOC_SALUD).values_list(
            "id", flat=True
        )
    )
    docs_finales_requeridos = list(
        Documento.objects.filter(categoria__in=CATEGORIAS_ARCHIVOS_FINALES).order_by(
            "categoria", "titulo"
        )
    )

    filtros_finales_visita = {
        "documento_requerido__categoria__in": CATEGORIAS_ARCHIVOS_FINALES
    }
    if tipo_visita == "interna":
        filtros_finales_visita["asistente_interna__visita"] = visita
    else:
        filtros_finales_visita["asistente_externa__visita"] = visita

    existe_archivo_final_subido = DocumentoSubidoAsistente.objects.filter(
        **filtros_finales_visita
    ).exists()
    mostrar_faltantes_finales_como_alerta = (
        visita.estado in ["documentos_enviados", "en_revision_documentos", "confirmada"]
        or existe_archivo_final_subido
    )

    asistentes_con_alertas = []
    asistentes = visita.asistentes.prefetch_related(
        "documentos_subidos__documento_requerido"
    )
    for asistente in asistentes:
        incidencias = []
        # Tomar solo la version vigente (ultima subida) por documento requerido.
        latest_por_documento = {}
        for ds in asistente.documentos_subidos.all():
            doc_id = ds.documento_requerido_id
            actual = latest_por_documento.get(doc_id)
            if not actual or (ds.fecha_subida, ds.id) > (
                actual.fecha_subida,
                actual.id,
            ):
                latest_por_documento[doc_id] = ds

        documentos_personales = [
            ds
            for ds in latest_por_documento.values()
            if ds.documento_requerido.categoria not in CATEGORIAS_ARCHIVOS_FINALES
        ]

        documentos_salud = [
            ds
            for ds in documentos_personales
            if ds.documento_requerido_id in doc_salud_ids
        ]
        if doc_salud_ids and not documentos_salud:
            incidencias.append(
                {
                    "tipo": "faltante",
                    "detalle": "Falta el archivo de auto reporte de condiciones de salud.",
                }
            )

        for doc_subido in documentos_personales:
            if doc_subido.estado == "rechazado":
                incidencias.append(
                    {
                        "tipo": "rechazado",
                        "documento_subido_id": doc_subido.id,
                        "detalle": (
                            f"{doc_subido.documento_requerido.titulo}: "
                            f"{doc_subido.observaciones_revision or 'Documento mal diligenciado.'}"
                        ),
                    }
                )

        if getattr(
            asistente, "estado_autorizacion_padres", ""
        ) == "rechazado" and getattr(
            asistente, "observaciones_autorizacion_padres", ""
        ):
            incidencias.append(
                {
                    "tipo": "rechazado",
                    "detalle": (
                        "Autorización de padres: "
                        f"{asistente.observaciones_autorizacion_padres}"
                    ),
                }
            )

        if incidencias:
            asistentes_con_alertas.append(
                {
                    "id": asistente.id,
                    "nombre": asistente.nombre_completo,
                    "documento": f"{asistente.get_tipo_documento_display()} {asistente.numero_documento}",
                    "incidencias": incidencias,
                }
            )

    archivos_finales_estado = []
    for doc_final in docs_finales_requeridos:
        filtros = {"documento_requerido": doc_final}
        if tipo_visita == "interna":
            filtros["asistente_interna__visita"] = visita
        else:
            filtros["asistente_externa__visita"] = visita

        ultimo_archivo = (
            DocumentoSubidoAsistente.objects.filter(**filtros)
            .order_by("-fecha_subida")
            .first()
        )

        if not ultimo_archivo:
            estado = "faltante"
            detalle = "No se ha cargado este archivo final."
        elif ultimo_archivo.estado == "rechazado":
            estado = "rechazado"
            detalle = (
                ultimo_archivo.observaciones_revision or "Archivo final rechazado."
            )
        elif ultimo_archivo.estado == "pendiente":
            estado = "pendiente"
            detalle = "Archivo final cargado y en revisión."
        else:
            estado = "aprobado"
            detalle = "Archivo final aprobado."

        archivos_finales_estado.append(
            {
                "documento_requerido_id": doc_final.id,
                "titulo": doc_final.titulo,
                "categoria": doc_final.get_categoria_display(),
                "estado": estado,
                "detalle": detalle,
            }
        )

    archivos_finales_con_alerta = [
        a
        for a in archivos_finales_estado
        if a["estado"] == "rechazado"
        or (a["estado"] == "faltante" and mostrar_faltantes_finales_como_alerta)
    ]
    archivos_finales_rechazados = [
        a for a in archivos_finales_estado if a["estado"] == "rechazado"
    ]
    mostrar_estado_archivos_finales = any(
        a["estado"] != "aprobado" for a in archivos_finales_estado
    )
    total_incidencias_asistentes = sum(
        len(item["incidencias"]) for item in asistentes_con_alertas
    )

    return {
        "asistentes_con_alertas": asistentes_con_alertas,
        "archivos_finales_estado": archivos_finales_estado,
        "archivos_finales_con_alerta": archivos_finales_con_alerta,
        "archivos_finales_rechazados": archivos_finales_rechazados,
        "mostrar_estado_archivos_finales": mostrar_estado_archivos_finales,
        "total_alertas": total_incidencias_asistentes
        + len(archivos_finales_con_alerta),
        "hay_alertas": bool(asistentes_con_alertas or archivos_finales_con_alerta),
    }


def _solicitud_final_historica_externa(visita):
    """Indica si la visita ya fue enviada al menos una vez para revision final."""
    if visita.estado in ["documentos_enviados", "en_revision_documentos", "confirmada"]:
        return True

    if HistorialAccionVisitaExterna.objects.filter(
        visita=visita,
        descripcion__icontains=MARCADOR_SOLICITUD_FINAL_ENVIADA,
    ).exists():
        return True

    if HistorialAccionVisitaExterna.objects.filter(
        visita=visita,
        tipo_accion__in=["inicio_revision", "devolucion_correccion", "confirmacion"],
    ).exists():
        return True

    if visita.asistentes.filter(
        estado__in=["documentos_aprobados", "documentos_rechazados"]
    ).exists():
        return True

    return DocumentoSubidoAsistente.objects.filter(
        asistente_externa__visita=visita,
        estado__in=["aprobado", "rechazado"],
    ).exists()


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
    reprogramacion_pendiente = (
        HistorialReprogramacion.objects.filter(visita_externa=visita, completada=False)
        .order_by("-fecha_solicitud")
        .first()
    )

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

    # Tomar un único documento por cada categoría final requerida para descarga.
    documentos_finales_requeridos = []
    categorias_finales_agregadas = set()
    for doc in documentos_disponibles:
        categoria_norm = _normalizar_categoria_texto(doc.categoria)
        clave_categoria = None
        etiqueta = doc.categoria

        if "ats" in categoria_norm:
            clave_categoria = "ats"
            etiqueta = "ATS"
        elif "induccion y reinduccion" in categoria_norm:
            clave_categoria = "induccion"
            etiqueta = "Formato Inducción y Reinducción"
        elif "charla de seguridad" in categoria_norm and (
            "calestenia" in categoria_norm or "calistenia" in categoria_norm
        ):
            clave_categoria = "charla"
            etiqueta = "Charla de Seguridad y Calistenia"

        if not clave_categoria or clave_categoria in categorias_finales_agregadas:
            continue

        doc.etiqueta_requerida = etiqueta
        documentos_finales_requeridos.append(doc)
        categorias_finales_agregadas.add(clave_categoria)

    reporte_documental = construir_reporte_documental_visita(visita, "externa")
    documentos_finales_rechazados_ids = [
        item.get("documento_requerido_id")
        for item in reporte_documental.get("archivos_finales_rechazados", [])
        if item.get("documento_requerido_id") is not None
    ]
    hay_alertas_documentales = bool(reporte_documental.get("hay_alertas"))
    estados_finales = reporte_documental.get("archivos_finales_estado", [])
    archivos_finales_faltantes = sum(
        1 for item in estados_finales if item.get("estado") == "faltante"
    )
    archivos_finales_completos = archivos_finales_faltantes == 0
    mostrar_boton_corregir_archivos_finales = any(
        item.get("estado") == "rechazado" for item in estados_finales
    )

    enviar_final_habilitado = (
        visita.estado == "aprobada_inicial"
        and visita.asistentes.exists()
        and archivos_finales_completos
        and not hay_alertas_documentales
    )

    mostrar_boton_subir_archivos_finales = (
        visita.estado == "aprobada_inicial"
        and visita.asistentes.exists()
        and not archivos_finales_completos
    )

    solicitud_final_historica = _solicitud_final_historica_externa(visita)
    # En externo se permite actualizar datos mientras la visita siga editable
    # en el estado actual, incluso si hubo un envio final historico.
    permite_editar_asistentes = visita.estado == "aprobada_inicial"
    permite_eliminar_asistentes = visita.estado == "aprobada_inicial"

    return render(
        request,
        "panel_instructor_externo/detalle_visita.html",
        {
            "visita": visita,
            "correo": correo,
            "documentos_por_categoria": documentos_por_categoria,
            "documentos_finales_requeridos": documentos_finales_requeridos,
            "documentos_finales_rechazados_ids": documentos_finales_rechazados_ids,
            "reporte_documental": reporte_documental,
            "reprogramacion_pendiente": reprogramacion_pendiente,
            "enviar_final_habilitado": enviar_final_habilitado,
            "mostrar_boton_subir_archivos_finales": mostrar_boton_subir_archivos_finales,
            "mostrar_boton_corregir_archivos_finales": mostrar_boton_corregir_archivos_finales,
            "solicitud_final_historica": solicitud_final_historica,
            "permite_editar_asistentes": permite_editar_asistentes,
            "permite_eliminar_asistentes": permite_eliminar_asistentes,
        },
    )
