from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db import IntegrityError
from django.db import transaction
import os
from visitaInterna.models import VisitaInterna
from .models import Ficha, Programa
from .forms import VisitaInternaInstructorForm, ProgramaForm, FichaForm
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from calendario.models import ReservaHorario

from django.http import JsonResponse
from visitaInterna.models import HistorialReprogramacion, VisitaInterna, AsistenteVisitaInterna
from .models import Ficha, Programa, Aprendiz
from .forms import VisitaInternaInstructorForm, ProgramaForm, FichaForm, AprendizForm
from documentos.models import Documento, DocumentoSubidoAsistente
from documentos.models import Documento, DocumentoSubidoAprendiz, DocumentoSubidoAsistente

CATEGORIA_DOC_SALUD = "Formato Auto Reporte Condiciones de Salud"
CATEGORIAS_ARCHIVOS_FINALES = [
    "ATS",
    "Formato Inducción y Reinducción",
    "Charla de Seguridad y Calestenia",
]
EXTENSIONES_DOCUMENTOS_APRENDIZ = {".pdf", ".doc", ".docx"}


def validar_archivos_documentos_aprendiz(files):
    """Valida que los documentos dinámicos del aprendiz solo sean PDF o Word."""
    errores = []

    for campo, archivo in files.items():
        if not campo.startswith("documento_") or not archivo:
            continue

        extension = os.path.splitext(archivo.name)[1].lower()
        if extension not in EXTENSIONES_DOCUMENTOS_APRENDIZ:
            errores.append(
                f'❌ El archivo "{archivo.name}" no es válido. Solo se permiten PDF o Word (.doc, .docx).'
            )

    return errores


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


def _es_categoria_archivo_final(categoria):
    cat = _normalizar_categoria_texto(categoria)
    if "ats" in cat:
        return True
    if "induccion y reinduccion" in cat:
        return True
    return "charla de seguridad" in cat and (
        "calestenia" in cat or "calistenia" in cat
    )


def construir_reporte_documental_visita(visita, tipo_visita):
    """Genera un resumen de faltantes y rechazos por asistente y archivos finales."""
    doc_salud_ids = set(
        Documento.objects.filter(categoria=CATEGORIA_DOC_SALUD).values_list("id", flat=True)
    )
    docs_finales_requeridos = list(
        Documento.objects.filter(categoria__in=CATEGORIAS_ARCHIVOS_FINALES).order_by(
            "categoria", "titulo"
        )
    )

    asistentes_con_alertas = []
    asistentes = visita.asistentes.prefetch_related("documentos_subidos__documento_requerido")
    for asistente in asistentes:
        incidencias = []
        # Tomar solo la version vigente (ultima subida) por documento requerido.
        latest_por_documento = {}
        for ds in asistente.documentos_subidos.all():
            doc_id = ds.documento_requerido_id
            actual = latest_por_documento.get(doc_id)
            if not actual or (ds.fecha_subida, ds.id) > (actual.fecha_subida, actual.id):
                latest_por_documento[doc_id] = ds

        documentos_personales = [
            ds
            for ds in latest_por_documento.values()
            if not _es_categoria_archivo_final(ds.documento_requerido.categoria)
        ]

        documentos_salud = [
            ds for ds in documentos_personales if ds.documento_requerido_id in doc_salud_ids
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

        if (
            getattr(asistente, "estado_autorizacion_padres", "") == "rechazado"
            and getattr(asistente, "observaciones_autorizacion_padres", "")
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
            detalle = ultimo_archivo.observaciones_revision or "Archivo final rechazado."
        elif ultimo_archivo.estado == "pendiente":
            estado = "pendiente"
            detalle = "Archivo final cargado y en revisión."
        else:
            estado = "aprobado"
            detalle = "Archivo final aprobado."

        archivos_finales_estado.append(
            {
                "titulo": doc_final.titulo,
                "categoria": doc_final.get_categoria_display(),
                "estado": estado,
                "detalle": detalle,
            }
        )

    archivos_finales_con_alerta = [
        a for a in archivos_finales_estado if a["estado"] in ["faltante", "rechazado"]
    ]
    archivos_finales_rechazados = [
        a for a in archivos_finales_estado if a["estado"] == "rechazado"
    ]
    total_incidencias_asistentes = sum(
        len(item["incidencias"]) for item in asistentes_con_alertas
    )

    return {
        "asistentes_con_alertas": asistentes_con_alertas,
        "archivos_finales_estado": archivos_finales_estado,
        "archivos_finales_con_alerta": archivos_finales_con_alerta,
        "archivos_finales_rechazados": archivos_finales_rechazados,
        "total_alertas": total_incidencias_asistentes + len(archivos_finales_con_alerta),
        "hay_alertas": bool(asistentes_con_alertas or archivos_finales_con_alerta),
    }


# ==================== AUTENTICACIÓN POR SESIÓN ====================


def get_sesion_instructor(request):
    """
    Lee los datos de sesión del panel_visitante.
    Retorna (correo, documento) o (None, None) si no está autenticado como interno.
    """
    if not request.session.get("responsable_autenticado"):
        return None, None
    if request.session.get("responsable_rol") != "interno":
        return None, None
    correo = request.session.get("responsable_correo")
    documento = request.session.get("responsable_documento")
    if not correo or not documento:
        return None, None
    return correo, documento


def instructor_interno_required(view_func):
    """
    Decorador: verifica sesión de panel_visitante con rol interno.
    """

    def wrapper(request, *args, **kwargs):
        correo, documento = get_sesion_instructor(request)
        if not correo:
            messages.warning(
                request,
                "Debes iniciar sesión como usuario interno para acceder a este panel.",
            )
            return redirect("panel_visitante:login_responsable")
        return view_func(request, *args, **kwargs)

    return wrapper


# ==================== PANEL PRINCIPAL ====================


@instructor_interno_required
def panel_instructor_interno(request):
    correo, documento = get_sesion_instructor(request)
    visitas = VisitaInterna.objects.filter(correo_responsable__iexact=correo).order_by(
        "-fecha_solicitud"
    )
    context = {
        "correo": correo,
        "documento": documento,
        "nombre": request.session.get("responsable_nombre", ""),
        "apellido": request.session.get("responsable_apellido", ""),
        "visitas": visitas[:5],
        "total_programas": Programa.objects.filter(activo=True).count(),
        "total_fichas": Ficha.objects.filter(activa=True).count(),
        "total_visitas": visitas.count(),
    }
    return render(request, "panel_instructor_interno/panel.html", context)


# ==================== MÓDULO: RESERVAR VISITA INTERNA ====================


@instructor_interno_required
def reservar_visita_interna(request):
    correo, documento = get_sesion_instructor(request)

    # Obtener datos adicionales de la sesión
    nombre = request.session.get("responsable_nombre", "")
    apellido = request.session.get("responsable_apellido", "")
    tipo_documento = request.session.get("responsable_tipo_documento", "CC")
    telefono = request.session.get("responsable_telefono", "")
    nombre_completo = f"{nombre} {apellido}".strip()

    if request.method == "POST":
        form = VisitaInternaInstructorForm(request.POST)
        if form.is_valid():
            numero_ficha = form.cleaned_data.get("numero_ficha")
            ficha = (
                Ficha.objects.select_related("programa")
                .filter(numero=numero_ficha, activa=True, programa__activo=True)
                .first()
            )

            if not ficha:
                form.add_error(
                    "numero_ficha",
                    "La ficha seleccionada no es válida o está inactiva.",
                )
                context = {
                    "form": form,
                    "fichas": Ficha.objects.filter(activa=True).select_related("programa"),
                    "correo": correo,
                    "titulo": "Reservar Visita Interna",
                }
                return render(request, "panel_instructor_interno/reservar_visita.html", context)

            visita = form.save(commit=False)
            visita.nombre_programa = ficha.programa.nombre
            visita.numero_ficha = ficha.numero
            visita.correo_responsable = correo
            visita.documento_responsable = documento
            visita.estado = "enviada_coordinacion"

            if not (visita.fecha_visita and visita.hora_inicio and visita.hora_fin):
                form.add_error(
                    None,
                    "Debes seleccionar fecha y horario antes de enviar la solicitud.",
                )
            elif visita.hora_inicio >= visita.hora_fin:
                form.add_error(None, "El horario seleccionado no es válido.")
            else:
                try:
                    with transaction.atomic():
                        visita.save()

                        if not ReservaHorario.horario_disponible(
                            visita.fecha_visita,
                            visita.hora_inicio,
                            visita.hora_fin,
                        ):
                            raise ValueError(
                                "El horario seleccionado ya no está disponible. Por favor elige otro horario."
                            )

                        reserva = ReservaHorario.crear_reserva_interna(visita)
                        if not reserva:
                            raise ValueError(
                                "No fue posible bloquear el horario seleccionado. Intenta nuevamente."
                            )
                except ValueError as exc:
                    form.add_error(None, str(exc))
                else:
                    # Enviar correo HTML de confirmación al responsable
                    try:
                        subject = "Confirmación: solicitud de visita interna enviada"
                        context = {
                            "responsable_nombre": nombre_completo,
                            "responsable": visita.responsable,
                            "documento_responsable": visita.documento_responsable,
                            "nombre_programa": visita.nombre_programa,
                            "numero_ficha": visita.numero_ficha,
                            "fecha_visita": (
                                visita.fecha_visita.strftime("%d/%m/%Y")
                                if visita.fecha_visita
                                else "Por definir"
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
                        }
                        html_content = render_to_string(
                            "emails/solicitud_visita_interna.html", context
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
                        "✅ Solicitud enviada. El horario quedó bloqueado y está pendiente de aprobación por coordinación.",
                    )
                    return redirect("panel_instructor_interno:mis_visitas")
    else:
        form = VisitaInternaInstructorForm(
            initial={
                "responsable": nombre_completo,
                "tipo_documento_responsable": tipo_documento,
                "documento_responsable": documento,
                "correo_responsable": correo,
                "telefono_responsable": telefono,
            }
        )
    fichas = Ficha.objects.filter(activa=True).select_related("programa")
    context = {
        "form": form,
        "fichas": fichas,
        "correo": correo,
        "titulo": "Reservar Visita Interna",
    }
    return render(request, "panel_instructor_interno/reservar_visita.html", context)


@instructor_interno_required
def mis_visitas_internas(request):
    correo, _ = get_sesion_instructor(request)
    visitas = VisitaInterna.objects.filter(correo_responsable__iexact=correo).order_by(
        "-fecha_solicitud"
    )
    estado = request.GET.get("estado", "")
    if estado:
        visitas = visitas.filter(estado=estado)
    buscar = request.GET.get("buscar", "")
    if buscar:
        visitas = visitas.filter(
            Q(nombre_programa__icontains=buscar) | Q(numero_ficha__icontains=buscar)
        )
    context = {
        "visitas": visitas,
        "correo": correo,
        "estado_filtrado": estado,
        "buscar": buscar,
        "estados": VisitaInterna.ESTADO_CHOICES,
    }
    return render(request, "panel_instructor_interno/mis_visitas.html", context)


@instructor_interno_required
def detalle_visita_interna(request, pk):
    correo, _ = get_sesion_instructor(request)
    visita = get_object_or_404(VisitaInterna, pk=pk, correo_responsable__iexact=correo)
    reprogramacion_pendiente = (
        HistorialReprogramacion.objects.filter(visita_interna=visita, completada=False)
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

    reporte_documental = construir_reporte_documental_visita(visita, "interna")

    return render(
        request,
        "panel_instructor_interno/detalle_visita.html",
        {
            "visita": visita,
            "correo": correo,
            "documentos_por_categoria": documentos_por_categoria,
            "reporte_documental": reporte_documental,
            "reprogramacion_pendiente": reprogramacion_pendiente,
        },
    )


# ==================== MÓDULO: GESTIONAR PROGRAMAS ====================


@instructor_interno_required
def gestionar_programas(request):
    correo, _ = get_sesion_instructor(request)
    programas = Programa.objects.all().order_by("nombre")
    buscar = request.GET.get("buscar", "")
    if buscar:
        programas = programas.filter(nombre__icontains=buscar)
    return render(
        request,
        "panel_instructor_interno/gestionar_programas.html",
        {
            "programas": programas,
            "buscar": buscar,
            "total": programas.count(),
            "correo": correo,
        },
    )


@instructor_interno_required
def crear_programa(request):
    correo, _ = get_sesion_instructor(request)
    is_ajax = (
        request.GET.get("ajax") == "true"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )

    if request.method == "POST":
        form = ProgramaForm(request.POST)
        if form.is_valid():
            programa = form.save()
            if is_ajax:
                return JsonResponse(
                    {
                        "success": True,
                        "message": f'✅ Programa "{programa.nombre}" creado correctamente.',
                    }
                )
            else:
                messages.success(
                    request, f'✅ Programa "{programa.nombre}" creado correctamente.'
                )
                return redirect("panel_instructor_interno:gestionar_programas")
        else:
            if is_ajax:
                # Retornar formulario con errores para mostrar en el modal
                html = render(
                    request,
                    "panel_instructor_interno/form_programa_modal.html",
                    {
                        "form": form,
                        "titulo": "Crear Programa",
                        "accion": "Crear",
                        "correo": correo,
                    },
                ).content.decode("utf-8")
                return JsonResponse({"success": False, "html": html})
            # Para requests normales con errores, mostrar la página completa
            return render(
                request,
                "panel_instructor_interno/form_programa.html",
                {
                    "form": form,
                    "titulo": "Crear Programa",
                    "accion": "Crear",
                    "correo": correo,
                },
            )
    else:
        form = ProgramaForm()

    if is_ajax:
        # Para AJAX GET, retornar solo el formulario sin headers/footers
        html = render(
            request,
            "panel_instructor_interno/form_programa_modal.html",
            {
                "form": form,
                "titulo": "Crear Programa",
                "accion": "Crear",
                "correo": correo,
            },
        ).content.decode("utf-8")
        return JsonResponse({"html": html})
    else:
        # Para requests normales, retornar la página completa
        return render(
            request,
            "panel_instructor_interno/form_programa.html",
            {
                "form": form,
                "titulo": "Crear Programa",
                "accion": "Crear",
                "correo": correo,
            },
        )


@instructor_interno_required
def editar_programa(request, pk):
    correo, _ = get_sesion_instructor(request)
    programa = get_object_or_404(Programa, pk=pk)
    is_ajax = (
        request.GET.get("ajax") == "true"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )

    if request.method == "POST":
        form = ProgramaForm(request.POST, instance=programa)
        if form.is_valid():
            form.save()
            if is_ajax:
                return JsonResponse(
                    {
                        "success": True,
                        "message": f'✅ Programa "{programa.nombre}" actualizado.',
                    }
                )
            else:
                messages.success(
                    request, f'✅ Programa "{programa.nombre}" actualizado.'
                )
                return redirect("panel_instructor_interno:gestionar_programas")
        else:
            if is_ajax:
                # Retornar formulario con errores para mostrar en el modal
                html = render(
                    request,
                    "panel_instructor_interno/form_programa_modal.html",
                    {
                        "form": form,
                        "titulo": "Editar Programa",
                        "accion": "Actualizar",
                        "correo": correo,
                    },
                ).content.decode("utf-8")
                return JsonResponse({"success": False, "html": html})
            # Para requests normales con errores
            return render(
                request,
                "panel_instructor_interno/form_programa.html",
                {
                    "form": form,
                    "programa": programa,
                    "titulo": "Editar Programa",
                    "accion": "Actualizar",
                    "correo": correo,
                },
            )
    else:
        form = ProgramaForm(instance=programa)

    if is_ajax:
        # Para AJAX GET, retornar solo el formulario
        html = render(
            request,
            "panel_instructor_interno/form_programa_modal.html",
            {
                "form": form,
                "titulo": "Editar Programa",
                "accion": "Actualizar",
                "correo": correo,
            },
        ).content.decode("utf-8")
        return JsonResponse({"html": html})
    else:
        # Para requests normales
        return render(
            request,
            "panel_instructor_interno/form_programa.html",
            {
                "form": form,
                "programa": programa,
                "titulo": "Editar Programa",
                "accion": "Actualizar",
                "correo": correo,
            },
        )


@instructor_interno_required
def eliminar_programa(request, pk):
    correo, _ = get_sesion_instructor(request)
    programa = get_object_or_404(Programa, pk=pk)
    is_ajax = (
        request.GET.get("ajax") == "true"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )

    if request.method == "POST":
        nombre = programa.nombre
        try:
            programa.delete()
            if is_ajax:
                return JsonResponse(
                    {"success": True, "message": f'🗑️ Programa "{nombre}" eliminado.'}
                )
            else:
                messages.success(request, f'🗑️ Programa "{nombre}" eliminado.')
        except Exception:
            if is_ajax:
                return JsonResponse(
                    {
                        "success": False,
                        "message": f'❌ No se puede eliminar "{nombre}" porque tiene fichas asociadas.',
                    }
                )
            else:
                messages.error(
                    request,
                    f'❌ No se puede eliminar "{nombre}" porque tiene fichas asociadas.',
                )
        return redirect("panel_instructor_interno:gestionar_programas")

    if is_ajax:
        return JsonResponse(
            {
                "nombre": programa.nombre,
                "descripcion": programa.descripcion or "Sin descripción",
            }
        )
    else:
        return render(
            request,
            "panel_instructor_interno/confirmar_eliminar_programa.html",
            {
                "programa": programa,
                "correo": correo,
            },
        )


# ==================== MÓDULO: GESTIONAR FICHAS ====================


@instructor_interno_required
def gestionar_fichas(request):
    correo, _ = get_sesion_instructor(request)
    fichas = Ficha.objects.select_related("programa").all()
    buscar = request.GET.get("buscar", "")
    if buscar:
        fichas = fichas.filter(
            Q(numero__icontains=buscar) | Q(programa__nombre__icontains=buscar)
        )
    return render(
        request,
        "panel_instructor_interno/gestionar_fichas.html",
        {
            "fichas": fichas,
            "buscar": buscar,
            "total": fichas.count(),
            "correo": correo,
        },
    )


@instructor_interno_required
def crear_ficha(request):
    correo, _ = get_sesion_instructor(request)
    is_ajax = (
        request.GET.get("ajax") == "true"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )

    if request.method == "POST":
        form = FichaForm(request.POST)
        if form.is_valid():
            ficha = form.save()
            if is_ajax:
                return JsonResponse(
                    {
                        "success": True,
                        "message": f"✅ Ficha {ficha.numero} creada correctamente.",
                    }
                )
            else:
                messages.success(
                    request, f"✅ Ficha {ficha.numero} creada correctamente."
                )
                return redirect("panel_instructor_interno:gestionar_fichas")
        else:
            if is_ajax:
                # Retornar formulario con errores para mostrar en el modal
                html = render(
                    request,
                    "panel_instructor_interno/form_ficha_modal.html",
                    {
                        "form": form,
                        "titulo": "Crear Ficha",
                        "accion": "Crear",
                        "correo": correo,
                    },
                ).content.decode("utf-8")
                return JsonResponse({"success": False, "html": html})
            # Para requests normales con errores, mostrar la página completa
            return render(
                request,
                "panel_instructor_interno/form_ficha.html",
                {
                    "form": form,
                    "titulo": "Crear Ficha",
                    "accion": "Crear",
                    "correo": correo,
                },
            )
    else:
        form = FichaForm()

    if is_ajax:
        # Para AJAX GET, retornar solo el formulario sin headers/footers
        html = render(
            request,
            "panel_instructor_interno/form_ficha_modal.html",
            {
                "form": form,
                "titulo": "Crear Ficha",
                "accion": "Crear",
                "correo": correo,
            },
        ).content.decode("utf-8")
        return JsonResponse({"html": html})
    else:
        # Para requests normales, retornar la página completa
        return render(
            request,
            "panel_instructor_interno/form_ficha.html",
            {
                "form": form,
                "titulo": "Crear Ficha",
                "accion": "Crear",
                "correo": correo,
            },
        )


@instructor_interno_required
def editar_ficha(request, pk):
    correo, _ = get_sesion_instructor(request)
    ficha = get_object_or_404(Ficha, pk=pk)
    is_ajax = (
        request.GET.get("ajax") == "true"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )

    if request.method == "POST":
        form = FichaForm(request.POST, instance=ficha)
        if form.is_valid():
            form.save()
            if is_ajax:
                return JsonResponse(
                    {
                        "success": True,
                        "message": f"✅ Ficha {ficha.numero} actualizada.",
                    }
                )
            else:
                messages.success(request, f"✅ Ficha {ficha.numero} actualizada.")
                return redirect("panel_instructor_interno:gestionar_fichas")
        else:
            if is_ajax:
                # Retornar formulario con errores para mostrar en el modal
                html = render(
                    request,
                    "panel_instructor_interno/form_ficha_modal.html",
                    {
                        "form": form,
                        "titulo": "Editar Ficha",
                        "accion": "Actualizar",
                        "correo": correo,
                    },
                ).content.decode("utf-8")
                return JsonResponse({"success": False, "html": html})
            # Para requests normales con errores
            return render(
                request,
                "panel_instructor_interno/form_ficha.html",
                {
                    "form": form,
                    "ficha": ficha,
                    "titulo": "Editar Ficha",
                    "accion": "Actualizar",
                    "correo": correo,
                },
            )
    else:
        form = FichaForm(instance=ficha)

    if is_ajax:
        # Para AJAX GET, retornar solo el formulario
        html = render(
            request,
            "panel_instructor_interno/form_ficha_modal.html",
            {
                "form": form,
                "titulo": "Editar Ficha",
                "accion": "Actualizar",
                "correo": correo,
            },
        ).content.decode("utf-8")
        return JsonResponse({"html": html})
    else:
        # Para requests normales
        return render(
            request,
            "panel_instructor_interno/form_ficha.html",
            {
                "form": form,
                "ficha": ficha,
                "titulo": "Editar Ficha",
                "accion": "Actualizar",
                "correo": correo,
            },
        )


@instructor_interno_required
def eliminar_ficha(request, pk):
    correo, _ = get_sesion_instructor(request)
    ficha = get_object_or_404(Ficha, pk=pk)
    is_ajax = (
        request.GET.get("ajax") == "true"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )

    if request.method == "POST":
        numero = ficha.numero
        try:
            ficha.delete()
            if is_ajax:
                return JsonResponse(
                    {"success": True, "message": f"🗑️ Ficha {numero} eliminada."}
                )
            else:
                messages.success(request, f"🗑️ Ficha {numero} eliminada.")
        except Exception as e:
            if is_ajax:
                return JsonResponse(
                    {
                        "success": False,
                        "message": f"❌ No se puede eliminar la ficha. Error: {str(e)}",
                    }
                )
            else:
                messages.error(request, f"❌ No se puede eliminar la ficha.")
        return redirect("panel_instructor_interno:gestionar_fichas")

    if is_ajax:
        return JsonResponse({"numero": ficha.numero, "programa": ficha.programa.nombre})
    else:
        return render(
            request,
            "panel_instructor_interno/confirmar_eliminar_ficha.html",
            {
                "ficha": ficha,
                "correo": correo,
            },
        )


# ==================== MÓDULO: GESTIONAR APRENDICES POR FICHA ====================


@instructor_interno_required
def listar_fichas_aprendices(request):
    """
    Lista todas las fichas con sus aprendices registrados.
    """
    correo, _ = get_sesion_instructor(request)

    # Obtener fichas
    fichas_all = Ficha.objects.select_related("programa").order_by("-numero")

    buscar = request.GET.get("buscar", "")
    if buscar:
        fichas_all = fichas_all.filter(
            Q(numero__icontains=buscar) | Q(programa__nombre__icontains=buscar)
        )

    # Agregar información de conteo de aprendices
    fichas_info = []
    for ficha in fichas_all:
        fichas_info.append(
            {
                "ficha": ficha,
                "total_aprendices": ficha.aprendices.count(),
                "aprendices_activos": ficha.aprendices.filter(estado="activo").count(),
            }
        )

    context = {
        "fichas_info": fichas_info,
        "buscar": buscar,
        "total": len(fichas_info),
        "correo": correo,
    }

    return render(
        request, "panel_instructor_interno/listar_fichas_aprendices.html", context
    )


@instructor_interno_required
def detalle_aprendices_ficha(request, pk):
    """
    Muestra todos los aprendices asociados a una ficha.
    Permite crear, editar y eliminar aprendices.
    """
    correo, _ = get_sesion_instructor(request)
    ficha = get_object_or_404(Ficha, pk=pk)

    aprendices = ficha.aprendices.all().order_by("apellido", "nombre")
    estado_filtro = request.GET.get("estado", "")

    if estado_filtro:
        aprendices = aprendices.filter(estado=estado_filtro)

    # Estadísticas
    stats = {
        "total": ficha.aprendices.count(),
        "activos": ficha.aprendices.filter(estado="activo").count(),
        "inactivos": ficha.aprendices.filter(estado="inactivo").count(),
        "retirados": ficha.aprendices.filter(estado="retirado").count(),
    }

    context = {
        "ficha": ficha,
        "aprendices": aprendices,
        "stats": stats,
        "estado_filtro": estado_filtro,
        "correo": correo,
    }

    return render(
        request, "panel_instructor_interno/detalle_aprendices_ficha.html", context
    )


@instructor_interno_required
def crear_aprendiz(request, ficha_id):
    """
    Crea un nuevo aprendiz para una ficha.
    """
    correo, _ = get_sesion_instructor(request)
    ficha = get_object_or_404(Ficha, pk=ficha_id)

    # Obtener documentos por categoría
    documentos_por_categoria = obtener_documentos_por_categoria()

    if request.method == "POST":
        form = AprendizForm(request.POST, request.FILES, ficha=ficha)
        errores_archivos = validar_archivos_documentos_aprendiz(request.FILES)

        if form.is_valid() and not errores_archivos:
            aprendiz = form.save(commit=False)
            aprendiz.ficha = ficha
            try:
                with transaction.atomic():
                    aprendiz.save()

                    # Guardar documentos de apoyo subidos
                    for categoria, docs in documentos_por_categoria.items():
                        if categoria == '👩🏻‍⚕️ Formato Auto Reporte Condiciones de Salud':
                            for doc in docs:
                                archivo = request.FILES.get(f"documento_{doc.id}")
                                if archivo:
                                    DocumentoSubidoAprendiz.objects.create(
                                        documento_requerido=doc,
                                        aprendiz=aprendiz,
                                        archivo=archivo,
                                        estado='pendiente'
                                    )
                
                messages.success(
                    request,
                    f'✅ Aprendiz "{aprendiz.get_nombre_completo()}" registrado correctamente con documentos.',
                )
                return redirect(
                    "panel_instructor_interno:detalle_aprendices_ficha", pk=ficha.id
                )
            except IntegrityError:
                messages.error(
                    request, 
                    f"❌ Ya existe un aprendiz con el documento {aprendiz.numero_documento} en esta ficha. "
                    f"Cada documento debe ser único por ficha."
                )
        else:
            for error in errores_archivos:
                messages.error(request, error)
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"❌ {field}: {error}")
    else:
        form = AprendizForm(ficha=ficha)

    context = {
        "form": form,
        "ficha": ficha,
        "correo": correo,
        "titulo": "Registrar Aprendiz",
        "documentos_por_categoria": documentos_por_categoria,
    }

    return render(request, "panel_instructor_interno/form_aprendiz.html", context)


@instructor_interno_required
def editar_aprendiz(request, pk):
    """
    Edita un aprendiz existente y sus documentos.
    """
    correo, _ = get_sesion_instructor(request)
    aprendiz = get_object_or_404(Aprendiz, pk=pk)
    ficha = aprendiz.ficha

    # Obtener documentos por categoría
    documentos_por_categoria = obtener_documentos_por_categoria()

    if request.method == "POST":
        form = AprendizForm(request.POST, request.FILES, instance=aprendiz, ficha=ficha)
        errores_archivos = validar_archivos_documentos_aprendiz(request.FILES)

        if form.is_valid() and not errores_archivos:
            try:
                with transaction.atomic():
                    form.save()

                    # Guardar documentos de apoyo subidos (actualizar existentes)
                    for categoria, docs in documentos_por_categoria.items():
                        if categoria == '👩🏻‍⚕️ Formato Auto Reporte Condiciones de Salud':
                            for doc in docs:
                                archivo = request.FILES.get(f"documento_{doc.id}")
                                if archivo:
                                    DocumentoSubidoAprendiz.objects.filter(
                                        documento_requerido=doc,
                                        aprendiz=aprendiz
                                    ).delete()
                                    DocumentoSubidoAprendiz.objects.create(
                                        documento_requerido=doc,
                                        aprendiz=aprendiz,
                                        archivo=archivo,
                                        estado='pendiente'
                                    )
                
                messages.success(
                    request, f'✅ Aprendiz "{aprendiz.get_nombre_completo()}" actualizado.'
                )
                return redirect(
                    "panel_instructor_interno:detalle_aprendices_ficha", pk=ficha.id
                )
            except IntegrityError:
                messages.error(
                    request, 
                    f"❌ Ya existe un aprendiz con el documento {aprendiz.numero_documento} en esta ficha. "
                    f"Cada documento debe ser único por ficha."
                )
        else:
            for error in errores_archivos:
                messages.error(request, error)
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"❌ {field}: {error}")
    else:
        form = AprendizForm(instance=aprendiz, ficha=ficha)

    context = {
        "form": form,
        "aprendiz": aprendiz,
        "ficha": ficha,
        "correo": correo,
        "titulo": "Editar Aprendiz",
        "documentos_por_categoria": documentos_por_categoria,
    }

    return render(request, "panel_instructor_interno/form_aprendiz.html", context)


@instructor_interno_required
def eliminar_aprendiz(request, pk):
    """
    Elimina un aprendiz.
    """
    correo, _ = get_sesion_instructor(request)
    aprendiz = get_object_or_404(Aprendiz, pk=pk)
    ficha = aprendiz.ficha

    if request.method == "POST":
        nombre_completo = aprendiz.get_nombre_completo()
        aprendiz.delete()
        messages.success(request, f'🗑️ Aprendiz "{nombre_completo}" eliminado.')
        return redirect(
            "panel_instructor_interno:detalle_aprendices_ficha", pk=ficha.id
        )

    context = {
        "aprendiz": aprendiz,
        "ficha": ficha,
        "correo": correo,
    }

    return render(
        request, "panel_instructor_interno/confirmar_eliminar_aprendiz.html", context
    )


# ==================== MÓDULO: INTEGRACIÓN CON VISITAS - APRENDICES ====================


@instructor_interno_required
def obtener_aprendices_ficha_json(request, ficha_id):
    """
    Retorna lista JSON de aprendices de una ficha.
    Usado para prellenar datos en formulario de visitas.
    """
    try:
        ficha = get_object_or_404(Ficha, pk=ficha_id)
        aprendices = ficha.aprendices.filter(estado="activo").values(
            "id",
            "nombre",
            "apellido",
            "tipo_documento",
            "numero_documento",
            "correo",
            "telefono",
        )
        return JsonResponse(
            {
                "success": True,
                "aprendices": list(aprendices),
                "total": aprendices.count(),
            }
        )
    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=400,
        )


@instructor_interno_required
def registrar_aprendices_visita(request, visita_id):
    """
    Permite registrar rápidamente aprendices de una ficha en una visita.
    Automáticamente trae sus datos y documentos.
    """
    correo, _ = get_sesion_instructor(request)
    visita = get_object_or_404(
        VisitaInterna, pk=visita_id, correo_responsable__iexact=correo
    )

    # Obtener la ficha de la visita
    try:
        ficha = Ficha.objects.get(numero=visita.numero_ficha)
    except Ficha.DoesNotExist:
        messages.error(request, "❌ No se encontró la ficha asociada a esta visita.")
        return redirect("panel_instructor_interno:detalle_visita", pk=visita_id)

    if request.method == "POST":
        # Obtener lista de IDs de aprendices seleccionados
        aprendices_ids = request.POST.getlist("aprendices[]")
        aprendices_registrados = 0
        aprendices_duplicados = 0

        for aprendiz_id in aprendices_ids:
            try:
                aprendiz = get_object_or_404(Aprendiz, pk=aprendiz_id, ficha=ficha)

                # Verificar si ya está registrado en esta visita
                if AsistenteVisitaInterna.objects.filter(
                    visita=visita, numero_documento=aprendiz.numero_documento
                ).exists():
                    aprendices_duplicados += 1
                    continue

                # Registrar como asistente con datos automáticos
                asistente = AsistenteVisitaInterna.objects.create(
                    visita=visita,
                    nombre_completo=aprendiz.get_nombre_completo(),
                    tipo_documento=aprendiz.tipo_documento,
                    numero_documento=aprendiz.numero_documento,
                    correo=aprendiz.correo,
                    telefono=aprendiz.telefono,
                    estado="pendiente_documentos",
                )

                # Cargar documentos del aprendiz automaticamente por categoria
                docs_aprendiz = DocumentoSubidoAprendiz.objects.filter(
                    aprendiz=aprendiz
                ).select_related("documento_requerido")

                for doc_subido in docs_aprendiz:
                    DocumentoSubidoAsistente.objects.update_or_create(
                        documento_requerido=doc_subido.documento_requerido,
                        asistente_interna=asistente,
                        defaults={"archivo": doc_subido.archivo},
                    )

                # Compatibilidad con registros antiguos que solo guardaban documento_adicional
                if not docs_aprendiz.exists() and aprendiz.documento_adicional:
                    doc_salud = Documento.objects.filter(
                        categoria="Formato Auto Reporte Condiciones de Salud"
                    ).first()
                    if doc_salud:
                        DocumentoSubidoAsistente.objects.update_or_create(
                            documento_requerido=doc_salud,
                            asistente_interna=asistente,
                            defaults={"archivo": aprendiz.documento_adicional},
                        )

                aprendices_registrados += 1
            except Exception as e:
                messages.warning(request, f"⚠️ Error al registrar aprendiz: {str(e)}")

        if aprendices_registrados > 0:
            messages.success(
                request,
                f"✅ {aprendices_registrados} aprendiz(ces) registrado(s) en la visita con documentos.",
            )
        if aprendices_duplicados > 0:
            messages.warning(
                request,
                f"⚠️ {aprendices_duplicados} aprendiz(ces) ya estaban registrados.",
            )

        return redirect("panel_instructor_interno:detalle_visita", pk=visita_id)

    # GET - Mostrar formulario
    aprendices = ficha.aprendices.filter(estado="activo").order_by("apellido", "nombre")

    # Marcas visuales por categoria para el template
    for aprendiz in aprendices:
        docs_qs = aprendiz.documentos_subidos.select_related("documento_requerido")
        aprendiz.tiene_documentos_subidos = docs_qs.exists()
        aprendiz.tiene_doc_salud = docs_qs.filter(
            documento_requerido__categoria="Formato Auto Reporte Condiciones de Salud"
        ).exists()

    # Identificar cuáles ya están registrados
    ya_registrados = list(
        AsistenteVisitaInterna.objects.filter(visita=visita).values_list(
            "numero_documento", flat=True
        )
    )

    context = {
        "visita": visita,
        "ficha": ficha,
        "aprendices": aprendices,
        "ya_registrados": ya_registrados,
        "total_aprendices": aprendices.count(),
        "aprendices_registrados": AsistenteVisitaInterna.objects.filter(
            visita=visita
        ).count(),
        "correo": correo,
    }

    return render(
        request, "panel_instructor_interno/registrar_aprendices_visita.html", context
    )


# ==================== FUNCIÓN DE APOYO (Para evitar repetir código) ====================


def obtener_documentos_por_categoria():
    docs = Documento.objects.all()
    resultado = {}
    for d in docs:
        # Solo agregar si el documento tiene un archivo físico asociado
        if d.archivo:
            cat_display = d.get_categoria_display() if d.categoria else "General"
            if cat_display not in resultado:
                resultado[cat_display] = []
            resultado[cat_display].append(d)
    return resultado


def guardar_documentos_aprendiz(aprendiz, archivos_subidos, documentos_por_categoria):
    """Guarda o reemplaza los documentos requeridos cargados para un aprendiz."""
    for docs in documentos_por_categoria.values():
        for doc in docs:
            archivo = archivos_subidos.get(f"documento_{doc.id}")
            if not archivo:
                continue

            DocumentoSubidoAprendiz.objects.update_or_create(
                aprendiz=aprendiz,
                documento_requerido=doc,
                defaults={
                    "archivo": archivo,
                    "estado": "pendiente",
                    "observaciones_revision": None,
                },
            )


# ==================== MÓDULO: GESTIONAR APRENDICES (ACTUALIZADO) ====================


@instructor_interno_required
def crear_aprendiz(request, ficha_id):
    correo, _ = get_sesion_instructor(request)
    ficha = get_object_or_404(Ficha, pk=ficha_id)

    # --- INTEGRACIÓN DE DOCUMENTOS ---
    docs_cat = obtener_documentos_por_categoria()

    if request.method == "POST":
        form = AprendizForm(request.POST, request.FILES, ficha=ficha)
        if form.is_valid():
            aprendiz = form.save(commit=False)
            aprendiz.ficha = ficha
            try:
                aprendiz.save()
                guardar_documentos_aprendiz(aprendiz, request.FILES, docs_cat)
                messages.success(
                    request,
                    f'✅ Aprendiz "{aprendiz.get_nombre_completo()}" registrado correctamente.',
                )
                return redirect(
                    "panel_instructor_interno:detalle_aprendices_ficha", pk=ficha.id
                )
            except IntegrityError:
                messages.error(
                    request, 
                    f"❌ Ya existe un aprendiz con el documento {aprendiz.numero_documento} en esta ficha."
                )
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"❌ {field}: {error}")
    else:
        form = AprendizForm(ficha=ficha)

    context = {
        "form": form,
        "ficha": ficha,
        "correo": correo,
        "titulo": "Registrar Aprendiz",
        "documentos_por_categoria": docs_cat,  # <-- ESTO ACTIVA LAS SECCIONES EN EL HTML
        "docs_subidos_ids": [],
    }
    return render(request, "panel_instructor_interno/form_aprendiz.html", context)


@instructor_interno_required
def editar_aprendiz(request, pk):
    correo, _ = get_sesion_instructor(request)
    aprendiz = get_object_or_404(Aprendiz, pk=pk)
    ficha = aprendiz.ficha

    # --- INTEGRACIÓN DE DOCUMENTOS ---
    docs_cat = obtener_documentos_por_categoria()

    if request.method == "POST":
        form = AprendizForm(request.POST, request.FILES, instance=aprendiz, ficha=ficha)
        if form.is_valid():
            try:
                form.save()
                guardar_documentos_aprendiz(aprendiz, request.FILES, docs_cat)
                messages.success(
                    request, f'✅ Aprendiz "{aprendiz.get_nombre_completo()}" actualizado.'
                )
                return redirect(
                    "panel_instructor_interno:detalle_aprendices_ficha", pk=ficha.id
                )
            except IntegrityError:
                messages.error(
                    request, 
                    f"❌ Ya existe un aprendiz con el documento {aprendiz.numero_documento} en esta ficha."
                )
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"❌ {field}: {error}")
    else:
        form = AprendizForm(instance=aprendiz, ficha=ficha)

    docs_subidos_ids = list(
        aprendiz.documentos_subidos.values_list("documento_requerido_id", flat=True)
    )

    context = {
        "form": form,
        "aprendiz": aprendiz,
        "ficha": ficha,
        "correo": correo,
        "titulo": "Editar Aprendiz",
        "documentos_por_categoria": docs_cat,  # <-- ESTO ACTIVA LAS SECCIONES EN EL HTML
        "docs_subidos_ids": docs_subidos_ids,
    }
    return render(request, "panel_instructor_interno/form_aprendiz.html", context)


@instructor_interno_required
def eliminar_asistente_visita(request, visita_id, asistente_id, tipo):
    """
    Elimina un asistente desde el detalle de una visita del instructor.
    Redirige de vuelta a la visita, no a visitante.
    """
    correo, _ = get_sesion_instructor(request)
    visita = get_object_or_404(
        VisitaInterna, pk=visita_id, correo_responsable__iexact=correo
    )

    # Verificar que el asistente pertenece a esta visita
    if tipo == "interna":
        asistente = get_object_or_404(
            AsistenteVisitaInterna, pk=asistente_id, visita=visita
        )
        nombre = asistente.nombre_completo
        asistente.delete()
    else:
        return redirect("panel_instructor_interno:detalle_visita", pk=visita_id)

    messages.success(request, f'🗑️ Asistente "{nombre}" eliminado de la visita.')
    return redirect("panel_instructor_interno:detalle_visita", pk=visita_id)
