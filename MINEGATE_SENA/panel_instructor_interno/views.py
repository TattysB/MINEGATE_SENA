from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from visitaInterna.models import VisitaInterna
from .models import Ficha, Programa
from .forms import VisitaInternaInstructorForm, ProgramaForm, FichaForm
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from calendario.models import ReservaHorario

from django.http import JsonResponse
from visitaInterna.models import VisitaInterna, AsistenteVisitaInterna
from .models import Ficha, Programa, Aprendiz
from .forms import VisitaInternaInstructorForm, ProgramaForm, FichaForm, AprendizForm
from documentos.models import Documento

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
            visita = form.save(commit=False)
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
    programas = Programa.objects.filter(activo=True)
    context = {
        "form": form,
        "fichas": fichas,
        "programas": programas,
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
        "panel_instructor_interno/detalle_visita.html",
        {
            "visita": visita,
            "correo": correo,
            "documentos_por_categoria": documentos_por_categoria,
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
    docs = Documento.objects.all()
    documentos_por_categoria = {}
    for doc in docs:
        if doc.categoria not in documentos_por_categoria:
            documentos_por_categoria[doc.categoria] = []
        documentos_por_categoria[doc.categoria].append(doc)

    if request.method == "POST":
        form = AprendizForm(request.POST, request.FILES)
        if form.is_valid():
            aprendiz = form.save(commit=False)
            aprendiz.ficha = ficha
            aprendiz.save()
            messages.success(
                request,
                f'✅ Aprendiz "{aprendiz.get_nombre_completo()}" registrado correctamente con documentos.',
            )
            return redirect(
                "panel_instructor_interno:detalle_aprendices_ficha", pk=ficha.id
            )
        else:
            messages.error(
                request, "❌ Error al validar el formulario. Revisa los campos."
            )
    else:
        form = AprendizForm()

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
    docs = Documento.objects.all()
    documentos_por_categoria = {}
    for doc in docs:
        if doc.categoria not in documentos_por_categoria:
            documentos_por_categoria[doc.categoria] = []
        documentos_por_categoria[doc.categoria].append(doc)

    if request.method == "POST":
        form = AprendizForm(request.POST, request.FILES, instance=aprendiz)
        if form.is_valid():
            form.save()
            messages.success(
                request, f'✅ Aprendiz "{aprendiz.get_nombre_completo()}" actualizado.'
            )
            return redirect(
                "panel_instructor_interno:detalle_aprendices_ficha", pk=ficha.id
            )
        else:
            messages.error(request, "❌ Error al validar el formulario.")
    else:
        form = AprendizForm(instance=aprendiz)

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

        from documentos.models import DocumentoSubidoAsistente, Documento

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

                # Cargar documentos del aprendiz automáticamente
                # Buscar el documento "Formato Auto Reporte Condiciones de Salud"
                if aprendiz.documento_adicional:
                    try:
                        doc_salud = Documento.objects.filter(
                            categoria="Formato Auto Reporte Condiciones de Salud"
                        ).first()
                        if doc_salud:
                            DocumentoSubidoAsistente.objects.create(
                                documento_requerido=doc_salud,
                                asistente_interna=asistente,
                                archivo=aprendiz.documento_adicional,
                            )
                    except Exception as e:
                        # Silenciar si falla, pero continuar con el registro
                        pass

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
            cat_nombre = str(d.categoria) if d.categoria else "General"
            if cat_nombre not in resultado:
                resultado[cat_nombre] = []
            resultado[cat_nombre].append(d)
    return resultado


# ==================== MÓDULO: GESTIONAR APRENDICES (ACTUALIZADO) ====================


@instructor_interno_required
def crear_aprendiz(request, ficha_id):
    correo, _ = get_sesion_instructor(request)
    ficha = get_object_or_404(Ficha, pk=ficha_id)

    # --- INTEGRACIÓN DE DOCUMENTOS ---
    docs_cat = obtener_documentos_por_categoria()

    if request.method == "POST":
        form = AprendizForm(request.POST, request.FILES)
        if form.is_valid():
            aprendiz = form.save(commit=False)
            aprendiz.ficha = ficha
            aprendiz.save()
            messages.success(
                request,
                f'✅ Aprendiz "{aprendiz.get_nombre_completo()}" registrado correctamente.',
            )
            return redirect(
                "panel_instructor_interno:detalle_aprendices_ficha", pk=ficha.id
            )
        else:
            messages.error(
                request, "❌ Error al validar el formulario. Revisa los campos."
            )
    else:
        form = AprendizForm()

    context = {
        "form": form,
        "ficha": ficha,
        "correo": correo,
        "titulo": "Registrar Aprendiz",
        "documentos_por_categoria": docs_cat,  # <-- ESTO ACTIVA LAS SECCIONES EN EL HTML
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
        form = AprendizForm(request.POST, request.FILES, instance=aprendiz)
        if form.is_valid():
            form.save()
            messages.success(
                request, f'✅ Aprendiz "{aprendiz.get_nombre_completo()}" actualizado.'
            )
            return redirect(
                "panel_instructor_interno:detalle_aprendices_ficha", pk=ficha.id
            )
        else:
            messages.error(request, "❌ Error al validar el formulario.")
    else:
        form = AprendizForm(instance=aprendiz)

    context = {
        "form": form,
        "aprendiz": aprendiz,
        "ficha": ficha,
        "correo": correo,
        "titulo": "Editar Aprendiz",
        "documentos_por_categoria": docs_cat,  # <-- ESTO ACTIVA LAS SECCIONES EN EL HTML
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
