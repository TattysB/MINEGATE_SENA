from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.csrf import csrf_protect
from django.urls import reverse
from datetime import datetime
from visitaInterna.models import VisitaInterna, AsistenteVisitaInterna
from visitaExterna.models import VisitaExterna, AsistenteVisitaExterna
from documentos.models import (
    Documento,
    DocumentoSubidoAsistente,
    DocumentoSubidoAprendiz,
)
from .forms import (
    RegistroVisitanteForm,
    PasswordResetRequestForm,
    PasswordResetConfirmForm,
)
from .forms import (
    RegistroVisitanteForm,
    PasswordResetRequestForm,
    PasswordResetConfirmForm,
    ActualizarPerfilForm,
    CambiarContrasenaForm,
)
from .models import RegistroVisitante
from django.conf import settings
from django.db import IntegrityError
from django.http import JsonResponse


def _redirect_segun_rol(request, tipo=None, visita_id=None):
    """
    Redirige al panel correcto según el rol de la sesión.
    Si se pasa tipo y visita_id, intenta ir al detalle de la visita.
    """
    rol = request.session.get("responsable_rol")
    if rol == "interno":
        if tipo and visita_id:
            from django.urls import reverse

            return redirect(
                reverse("panel_instructor_interno:detalle_visita", args=[visita_id])
            )
        return redirect("panel_instructor_interno:panel")
    elif rol == "externo":
        if tipo and visita_id:
            from django.urls import reverse

            return redirect(
                reverse("panel_instructor_externo:detalle_visita", args=[visita_id])
            )
        return redirect("panel_instructor_externo:panel")
    else:
        return redirect("panel_visitante:panel_responsable")


def _tiene_acceso_por_correo(visita, correo):
    """
    Valida ownership de la visita usando el correo del responsable.
    El correo es el identificador canonico de la cuenta en sesion.
    """
    if not correo:
        return False
    return (visita.correo_responsable or "").strip().lower() == correo.strip().lower()


def login_responsable(request):
    """
    Login para responsables de visitas usando solo documento y contraseña.
    """
    if request.method == "POST":
        documento = request.POST.get("documento", "").strip()
        contrasena = request.POST.get("contrasena", "")

        visitante = RegistroVisitante.objects.filter(documento=documento).first()

        if visitante and visitante.check_password(contrasena):
            # Guardar sesión
            request.session["responsable_correo"] = visitante.correo
            request.session["responsable_documento"] = visitante.documento
            request.session["responsable_rol"] = visitante.rol
            request.session["responsable_nombre"] = visitante.nombre
            request.session["responsable_apellido"] = visitante.apellido
            request.session["responsable_tipo_documento"] = visitante.tipo_documento
            request.session["responsable_telefono"] = visitante.telefono
            request.session["responsable_autenticado"] = True
            request.session.modified = True

            messages.success(
                request,
                f"Bienvenido {visitante.nombre} {visitante.apellido}. Accediendo a tu panel...",
            )
            # Redirigir al panel de instructor según el rol
            if visitante.rol == "interno":
                return redirect("panel_instructor_interno:panel")
            else:
                return redirect("panel_instructor_externo:panel")

        messages.error(
            request,
            "Credenciales invalidas. Verifica tu documento y contrasena.",
        )

    return render(request, "login_responsable.html")


def registro_visita(request):
    """
    Registro inicial de visita para responsables.
    """
    if request.method == "POST":
        form = RegistroVisitanteForm(request.POST)

        if form.is_valid():
            visitante = RegistroVisitante(
                nombre=form.cleaned_data["nombre"],
                apellido=form.cleaned_data["apellido"],
                tipo_documento=form.cleaned_data["tipo_documento"],
                documento=form.cleaned_data["documento"],
                telefono=form.cleaned_data["telefono"],
                correo=form.cleaned_data["correo"],
                rol=form.cleaned_data["rol"],
            )
            visitante.set_password(form.cleaned_data["password1"])
            visitante.save()
            messages.success(
                request,
                f"Cuenta creada exitosamente para {visitante.nombre} {visitante.apellido}. Ya puedes iniciar sesion con tus credenciales.",
            )
            return redirect("panel_visitante:login_responsable")
    else:
        form = RegistroVisitanteForm()

    return render(
        request,
        "registro_visita.html",
        {"form": form, "titulo": "Registro de Usuario"},
    )


def logout_responsable(request):
    """
    Cerrar sesión del responsable.
    """
    request.session.pop("responsable_correo", None)
    request.session.pop("responsable_documento", None)
    request.session.pop("responsable_autenticado", None)
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect("panel_visitante:login_responsable")


def panel_responsable(request):
    """
    Panel para que el responsable vea sus visitas y registre asistentes.
    """
    # Obtener datos de sesión
    correo = request.session.get("responsable_correo")
    documento = request.session.get("responsable_documento")
    rol = request.session.get("responsable_rol")
    autenticado = request.session.get("responsable_autenticado", False)

    # Verificar si está autenticado
    if not autenticado or not correo or not documento:
        messages.warning(request, "Debe iniciar sesión para acceder al panel.")
        return redirect("panel_visitante:login_responsable")

    try:
        # Obtener visitas del responsable
        visitas_internas = VisitaInterna.objects.filter(
            correo_responsable__iexact=correo
        ).prefetch_related("asistentes")

        visitas_externas = VisitaExterna.objects.filter(
            correo_responsable__iexact=correo
        ).prefetch_related("asistentes")

        context = {
            "visitas_internas": visitas_internas,
            "visitas_externas": visitas_externas,
            "correo": correo,
            "rol": rol,
        }

        return render(request, "panel_responsable.html", context)

    except Exception as e:
        messages.error(request, f"Error al cargar el panel: {str(e)}")
        return redirect("panel_visitante:login_responsable")


def registrar_asistentes(request, tipo, visita_id):
    """
    Formulario para registrar asistentes a una visita aprobada.
    """
    # Verificar autenticación
    if not request.session.get("responsable_autenticado"):
        messages.warning(request, "Debe iniciar sesión para acceder.")
        return redirect("panel_visitante:login_responsable")

    correo = request.session.get("responsable_correo")
    # Obtener la visita según el tipo
    if tipo == "interna":
        visita = get_object_or_404(
            VisitaInterna,
            id=visita_id,
            correo_responsable__iexact=correo,
        )
        asistentes = visita.asistentes.all()
        max_asistentes = visita.cantidad_aprendices
    elif tipo == "externa":
        visita = get_object_or_404(
            VisitaExterna,
            id=visita_id,
            correo_responsable__iexact=correo,
        )
        asistentes = visita.asistentes.all()
        max_asistentes = visita.cantidad_visitantes
    else:
        messages.error(request, "Tipo de visita no válido.")
        return _redirect_segun_rol(request)

    # Verificar que la visita esté aprobada inicialmente para registro de asistentes
    if visita.estado not in [
        "aprobada_inicial",
        "documentos_enviados",
        "en_revision_documentos",
    ]:
        messages.error(request, "Solo puede registrar asistentes en visitas aprobadas.")
        return _redirect_segun_rol(request)

    # Obtener asistentes previos disponibles (de visitas pasadas del mismo programa)
    asistentes_previos = []
    if tipo == "interna":
        # Obtener todas las fichas anteriores del mismo programa
        visitas_anteriores = VisitaInterna.objects.filter(
            numero_ficha=visita.numero_ficha,
            id__lt=visita.id,
            estado__in=["documentos_enviados", "en_revision_documentos", "confirmada"],
        ).order_by("-id")
        for visita_anterior in visitas_anteriores:
            asistentes_del_programa = visita_anterior.asistentes.filter(
                puede_reutilizar=True
            ).values_list(
                "id",
                "nombre_completo",
                "tipo_documento",
                "numero_documento",
                "correo",
                "telefono",
            )
            asistentes_previos.extend(asistentes_del_programa)
        # Eliminar duplicados basados en número de documento
        nums_doc_vistos = set()
        asistentes_previos_unicos = []
        for doc_info in asistentes_previos:
            num_doc = doc_info[3]  # numero_documento
            if num_doc not in nums_doc_vistos:
                nums_doc_vistos.add(num_doc)
                asistentes_previos_unicos.append(doc_info)
        asistentes_previos = asistentes_previos_unicos
    elif tipo == "externa":
        # Obtener todas las visitas anteriores de la misma institución
        visitas_anteriores = VisitaExterna.objects.filter(
            nombre=visita.nombre,
            id__lt=visita.id,
            estado__in=["documentos_enviados", "en_revision_documentos", "confirmada"],
        ).order_by("-id")
        for visita_anterior in visitas_anteriores:
            asistentes_del_programa = visita_anterior.asistentes.filter(
                puede_reutilizar=True
            ).values_list(
                "id",
                "nombre_completo",
                "tipo_documento",
                "numero_documento",
                "correo",
                "telefono",
            )
            asistentes_previos.extend(asistentes_del_programa)
        # Eliminar duplicados basados en número de documento
        nums_doc_vistos = set()
        asistentes_previos_unicos = []
        for doc_info in asistentes_previos:
            num_doc = doc_info[3]  # numero_documento
            if num_doc not in nums_doc_vistos:
                nums_doc_vistos.add(num_doc)
                asistentes_previos_unicos.append(doc_info)
        asistentes_previos = asistentes_previos_unicos

    # Sincronizar documento de salud desde Aprendiz -> Asistente (solo visitas internas)
    if tipo == "interna":
        from panel_instructor_interno.models import Aprendiz

        doc_salud_default = Documento.objects.filter(
            categoria="Formato Auto Reporte Condiciones de Salud"
        ).first()

        for asistente in asistentes:
            tiene_doc_salud = asistente.documentos_subidos.filter(
                documento_requerido__categoria="Formato Auto Reporte Condiciones de Salud"
            ).exists()

            if not tiene_doc_salud:
                aprendiz = Aprendiz.objects.filter(
                    ficha__numero=visita.numero_ficha,
                    numero_documento=asistente.numero_documento,
                ).first()

                if aprendiz:
                    docs_salud_aprendiz = DocumentoSubidoAprendiz.objects.filter(
                        aprendiz=aprendiz,
                        documento_requerido__categoria="Formato Auto Reporte Condiciones de Salud",
                    ).select_related("documento_requerido")

                    for doc_subido in docs_salud_aprendiz:
                        DocumentoSubidoAsistente.objects.update_or_create(
                            documento_requerido=doc_subido.documento_requerido,
                            asistente_interna=asistente,
                            asistente_externa=None,
                            defaults={"archivo": doc_subido.archivo},
                        )

                    # Compatibilidad con registros antiguos que guardaban en documento_adicional
                    if (
                        not docs_salud_aprendiz.exists()
                        and aprendiz.documento_adicional
                        and doc_salud_default
                    ):
                        DocumentoSubidoAsistente.objects.update_or_create(
                            documento_requerido=doc_salud_default,
                            asistente_interna=asistente,
                            asistente_externa=None,
                            defaults={"archivo": aprendiz.documento_adicional},
                        )

            asistente.tiene_doc_salud = asistente.documentos_subidos.filter(
                documento_requerido__categoria="Formato Auto Reporte Condiciones de Salud"
            ).exists()
    else:
        for asistente in asistentes:
            asistente.tiene_doc_salud = asistente.documentos_subidos.filter(
                documento_requerido__categoria="Formato Auto Reporte Condiciones de Salud"
            ).exists()

    # Obtener documentos disponibles para descargar, agrupados por categoria
    documentos_disponibles = Documento.objects.all().order_by(
        "categoria", "-fecha_subida"
    )
    documentos_por_categoria = {}
    for doc in documentos_disponibles:
        categoria = doc.categoria
        if categoria not in documentos_por_categoria:
            documentos_por_categoria[categoria] = []
        documentos_por_categoria[categoria].append(doc)

    asistentes_actuales = asistentes.count()
    puede_agregar = asistentes_actuales < max_asistentes
    # Permitir archivos finales si hay al menos 1 asistente registrado
    mostrar_archivos_finales = asistentes_actuales > 0

    context = {
        "visita": visita,
        "tipo": tipo,
        "asistentes": asistentes,
        "asistentes_actuales": asistentes_actuales,
        "max_asistentes": max_asistentes,
        "puede_agregar": puede_agregar,
        "documentos_por_categoria": documentos_por_categoria,
        "asistentes_previos": asistentes_previos,
        "tiene_asistentes_previos": len(asistentes_previos) > 0,
        "mostrar_archivos_finales": mostrar_archivos_finales,
    }

    # Procesar archivos finales si se envía el formulario del modal
    if (
        request.method == "POST"
        and mostrar_archivos_finales  # Permitir si hay al menos 1 asistente
        and any(f.startswith("archivo_final_") for f in request.FILES)
    ):
        es_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
        archivos_subidos = []
        # Obtener el primer asistente para asociar los archivos finales
        primer_asistente = asistentes.first() if asistentes.exists() else None

        if primer_asistente:
            for categoria, docs in context["documentos_por_categoria"].items():
                if categoria in [
                    "ATS",
                    "Formato Inducción y Reinducción",
                    "Charla de Seguridad y Calestenia",
                ]:
                    for doc in docs:
                        archivo = request.FILES.get(f"archivo_final_{doc.id}")
                        if archivo:
                            # Reemplazar la versión anterior para permitir nueva revisión
                            DocumentoSubidoAsistente.objects.update_or_create(
                                documento_requerido=doc,
                                asistente_interna=(
                                    primer_asistente if tipo == "interna" else None
                                ),
                                asistente_externa=(
                                    primer_asistente if tipo == "externa" else None
                                ),
                                defaults={
                                    "archivo": archivo,
                                    "estado": "pendiente",
                                    "observaciones_revision": "",
                                },
                            )
                            archivos_subidos.append(doc.titulo)

            if archivos_subidos:
                primer_asistente.estado = "pendiente_documentos"
                primer_asistente.observaciones_revision = ""
                primer_asistente.save(update_fields=["estado", "observaciones_revision"])

                if visita.estado in ["documentos_enviados", "en_revision_documentos"]:
                    visita.estado = "aprobada_inicial"
                    visita.save(update_fields=["estado"])

                if es_ajax:
                    return JsonResponse(
                        {
                            "success": True,
                            "message": "Archivos finales corregidos y cargados correctamente.",
                            "archivos_subidos": archivos_subidos,
                        }
                    )

                messages.success(request, "Archivos finales subidos con éxito.")
                return redirect(
                    "panel_visitante:registrar_asistentes",
                    tipo=tipo,
                    visita_id=visita_id,
                )
            else:
                if es_ajax:
                    return JsonResponse(
                        {
                            "success": False,
                            "error": "No se subieron archivos finales.",
                        },
                        status=400,
                    )
                messages.warning(request, "No se subieron archivos finales.")
        else:
            if es_ajax:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "No hay asistentes registrados para asociar los archivos.",
                    },
                    status=400,
                )
            messages.error(
                request, "No hay asistentes registrados para asociar los archivos."
            )

    if request.method == "POST":
        if not puede_agregar:
            messages.error(
                request, f"Ya se alcanzó el límite de {max_asistentes} asistentes."
            )
        else:
            nombre = request.POST.get("nombre_completo", "").strip()
            tipo_doc = request.POST.get("tipo_documento", "")
            num_doc = request.POST.get("numero_documento", "").strip()
            correo_asistente = request.POST.get("correo", "").strip()
            telefono = request.POST.get("telefono", "").strip()

            # Validar campos obligatorios
            campos_ok = nombre and tipo_doc and num_doc
            documentos_disponibles = Documento.objects.all().order_by(
                "categoria", "-fecha_subida"
            )
            documentos_por_categoria = {}
            for doc in documentos_disponibles:
                categoria = doc.categoria
                if categoria not in documentos_por_categoria:
                    documentos_por_categoria[categoria] = []
                documentos_por_categoria[categoria].append(doc)

            # Validar que solo el documento de 'Formato Auto Reporte Condiciones de Salud' fue subido
            archivos_ok = False
            archivos_dict = {}
            for categoria, docs in documentos_por_categoria.items():
                if categoria == "Formato Auto Reporte Condiciones de Salud":
                    for doc in docs:
                        file_field = f"documento_{doc.id}"
                        archivo = request.FILES.get(file_field)
                        if archivo:
                            archivos_ok = True
                        archivos_dict[doc.id] = archivo
                elif categoria == "Formato Autorización Padres de Familia":
                    for doc in docs:
                        file_field = f"documento_{doc.id}"
                        archivo = request.FILES.get(file_field)
                        # Este archivo es opcional, por lo que no afecta archivos_ok
                        archivos_dict[doc.id] = archivo

            if campos_ok and archivos_ok:
                try:
                    if tipo == "interna":
                        asistente = AsistenteVisitaInterna.objects.create(
                            visita=visita,
                            nombre_completo=nombre,
                            tipo_documento=tipo_doc,
                            numero_documento=num_doc,
                            correo=correo_asistente,
                            telefono=telefono,
                        )
                    else:
                        asistente = AsistenteVisitaExterna.objects.create(
                            visita=visita,
                            nombre_completo=nombre,
                            tipo_documento=tipo_doc,
                            numero_documento=num_doc,
                            correo=correo_asistente,
                            telefono=telefono,
                        )
                    # Guardar archivos subidos
                    # Separar el formato de autorización de padres de los demás documentos
                    formato_padres_archivo = None
                    documentos_regulares = {}

                    for doc_id, archivo in archivos_dict.items():
                        if archivo:
                            # Verificar si es el documento de autorización de padres
                            documento = Documento.objects.get(id=doc_id)
                            if (
                                documento.categoria
                                == "Formato Autorización Padres de Familia"
                            ):
                                formato_padres_archivo = archivo
                            else:
                                documentos_regulares[doc_id] = archivo

                    # Guardar el formato de autorización de padres directamente en el asistente
                    if formato_padres_archivo:
                        asistente.formato_autorizacion_padres = formato_padres_archivo
                        asistente.save()

                    # Guardar los demás documentos en DocumentoSubidoAsistente
                    for doc_id, archivo in documentos_regulares.items():
                        DocumentoSubidoAsistente.objects.create(
                            documento_requerido_id=doc_id,
                            asistente_interna=(
                                asistente if tipo == "interna" else None
                            ),
                            asistente_externa=(
                                asistente if tipo == "externa" else None
                            ),
                            archivo=archivo,
                        )

                    # Si es visita interna, también registrar aprendiz en la ficha
                    if tipo == "interna":
                        try:
                            from panel_instructor_interno.models import Ficha, Aprendiz

                            # Obtener la ficha de la visita
                            ficha = Ficha.objects.get(numero=visita.numero_ficha)

                            # Verificar si el aprendiz ya existe en la ficha
                            aprendiz_existe = Aprendiz.objects.filter(
                                ficha=ficha, numero_documento=num_doc
                            ).exists()

                            if not aprendiz_existe:
                                # Crear aprendiz en la ficha con el documento de salud
                                aprendiz_data = {
                                    "ficha": ficha,
                                    "nombre": (
                                        nombre.split()[0] if nombre else ""
                                    ),  # Primer nombre
                                    "apellido": (
                                        " ".join(nombre.split()[1:])
                                        if len(nombre.split()) > 1
                                        else ""
                                    ),  # Resto como apellido
                                    "tipo_documento": tipo_doc,
                                    "numero_documento": num_doc,
                                    "correo": correo_asistente,
                                    "telefono": telefono,
                                    "estado": "activo",
                                }

                                # Si hay documento de salud, asignarlo
                                for doc_id, archivo in archivos_dict.items():
                                    if archivo and doc_id in archivos_dict:
                                        # El archivo del Auto Reporte va a documento_adicional
                                        aprendiz_data["documento_adicional"] = archivo

                                Aprendiz.objects.create(**aprendiz_data)
                        except Exception as e:
                            # Si falla la creación del aprendiz en ficha, no interrumpir el flujo
                            pass

                    # El QR se envia unicamente cuando la visita queda confirmada en su totalidad.
                    messages.success(
                        request,
                        f'Asistente "{nombre}" registrado correctamente. El QR se enviara cuando la visita sea confirmada definitivamente.',
                    )

                    # Ya no es necesario guardar en session, el context lo calcula dinámicamente
                    return redirect(
                        "panel_visitante:registrar_asistentes",
                        tipo=tipo,
                        visita_id=visita_id,
                    )
                except Exception as e:
                    if "unique" in str(e).lower():
                        messages.error(
                            request,
                            "Este documento ya está registrado para esta visita.",
                        )
                    else:
                        messages.error(request, f"Error al registrar: {str(e)}")
            else:
                if not campos_ok:
                    messages.error(request, "Complete todos los campos obligatorios.")
                elif not archivos_ok:
                    messages.error(request, "Debe subir todos los archivos requeridos.")

    # Obtener documentos disponibles para descargar, agrupados por categoría
    documentos_disponibles = Documento.objects.all().order_by(
        "categoria", "-fecha_subida"
    )
    documentos_por_categoria = {}
    for doc in documentos_disponibles:
        categoria = doc.categoria
        if categoria not in documentos_por_categoria:
            documentos_por_categoria[categoria] = []
        documentos_por_categoria[categoria].append(doc)

    context = {
        "visita": visita,
        "tipo": tipo,
        "asistentes": asistentes,
        "asistentes_actuales": asistentes_actuales,
        "max_asistentes": max_asistentes,
        "puede_agregar": puede_agregar,
        "documentos_por_categoria": documentos_por_categoria,
    }

    return render(request, "registrar_asistentes.html", context)


def eliminar_asistente(request, tipo, asistente_id):
    """
    Eliminar un asistente de una visita.
    """
    # Verificar autenticación
    if not request.session.get("responsable_autenticado"):
        return redirect("panel_visitante:login_responsable")

    correo = request.session.get("responsable_correo")
    if tipo == "interna":
        asistente = get_object_or_404(AsistenteVisitaInterna, id=asistente_id)
        visita = asistente.visita
        # Verificar que el responsable tenga acceso a esta visita
        if not _tiene_acceso_por_correo(visita, correo):
            messages.error(request, "No tiene permiso para esta acción.")
            return _redirect_segun_rol(request)
        visita_id = visita.id
        asistente.delete()
    elif tipo == "externa":
        asistente = get_object_or_404(AsistenteVisitaExterna, id=asistente_id)
        visita = asistente.visita
        if not _tiene_acceso_por_correo(visita, correo):
            messages.error(request, "No tiene permiso para esta acción.")
            return _redirect_segun_rol(request)
        visita_id = visita.id
        asistente.delete()
    else:
        messages.error(request, "Tipo de visita no válido.")
        return _redirect_segun_rol(request)

    messages.success(request, "Asistente eliminado correctamente.")
    return redirect(
        "panel_visitante:registrar_asistentes", tipo=tipo, visita_id=visita_id
    )


def enviar_solicitud_final(request, tipo, visita_id):
    """
    Vista para que el responsable envíe la solicitud final de aprobación.
    Cambia el estado de la visita a 'documentos_enviados' para revisión de documentos.
    """
    # Verificar autenticación
    es_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    def respuesta_error(mensaje, status_code=400):
        if es_ajax:
            return JsonResponse(
                {
                    "success": False,
                    "error": mensaje,
                },
                status=status_code,
            )
        messages.error(request, mensaje)
        return _redirect_segun_rol(request, tipo, visita_id)

    def respuesta_ok(mensaje):
        if es_ajax:
            return JsonResponse(
                {
                    "success": True,
                    "message": mensaje,
                }
            )
        messages.success(request, mensaje)
        return _redirect_segun_rol(request, tipo, visita_id)

    if not request.session.get("responsable_autenticado"):
        if es_ajax:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Sesión no válida. Inicie sesión nuevamente.",
                },
                status=401,
            )
        return redirect("panel_visitante:login_responsable")

    correo = request.session.get("responsable_correo")
    # Obtener la visita
    if tipo == "interna":
        visita = get_object_or_404(VisitaInterna, id=visita_id)
        if not _tiene_acceso_por_correo(visita, correo):
            if es_ajax:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "No tiene permiso para esta acción.",
                    },
                    status=403,
                )
            messages.error(request, "No tiene permiso para esta acción.")
            return _redirect_segun_rol(request)
    elif tipo == "externa":
        visita = get_object_or_404(VisitaExterna, id=visita_id)
        if not _tiene_acceso_por_correo(visita, correo):
            if es_ajax:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "No tiene permiso para esta acción.",
                    },
                    status=403,
                )
            messages.error(request, "No tiene permiso para esta acción.")
            return _redirect_segun_rol(request)
    else:
        if es_ajax:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Tipo de visita no válido.",
                },
                status=400,
            )
        messages.error(request, "Tipo de visita no válido.")
        return _redirect_segun_rol(request)

    # Verificar que la visita esté en estado aprobada_inicial
    if visita.estado != "aprobada_inicial":
        return respuesta_error(
            "Solo puede enviar la solicitud final cuando la visita esté aprobada inicialmente.",
        )

    cantidad_maxima = (
        visita.cantidad_aprendices if tipo == "interna" else visita.cantidad_visitantes
    )
    if cantidad_maxima < 1:
        return respuesta_error(
            "La visita debe tener una cantidad de asistentes mayor a cero antes de enviar la solicitud final.",
        )

    # Verificar que haya al menos un asistente registrado
    if visita.asistentes.count() == 0:
        return respuesta_error(
            "Debe registrar al menos un asistente antes de enviar la solicitud final.",
        )

    # Evitar reenvío mientras existan rechazos pendientes de corrección
    if visita.asistentes.filter(estado="documentos_rechazados").exists():
        return respuesta_error(
            "Hay asistentes con documentos rechazados. Corrija los archivos antes de reenviar la solicitud.",
        )

    # Cambiar el estado a documentos_enviados
    visita.estado = "documentos_enviados"
    visita.save()

    # Enviar correo al responsable informando que la solicitud final fue enviada
    try:
        if tipo == "interna":
            panel_path = reverse("panel_instructor_interno:mis_visitas")
            template_name = "emails/solicitud_final_enviada_interna.html"
        else:
            panel_path = reverse("panel_instructor_externo:panel")
            template_name = "emails/solicitud_final_enviada_externa.html"
        panel_url = request.build_absolute_uri(panel_path)
        subject = "Solicitud final enviada con éxito — documentos en revisión"
        context = {
            "responsable_nombre": request.session.get("responsable_nombre", ""),
            "panel_url": panel_url,
        }
        html_content = render_to_string(template_name, context)
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

    return respuesta_ok(
        "¡Solicitud final enviada correctamente! El administrador revisará los documentos de los asistentes.",
    )


def restablecer_contraseña(request):
    """
    Vista para mostrar la página de restablecimiento de contraseña.
    Maneja la solicitud de recuperación y el cambio de contraseña.
    """
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]

            # Buscar visitante con ese email
            visitante = RegistroVisitante.objects.filter(correo__iexact=email).first()

            if visitante:
                # Generar token y uid usando Django's default_token_generator
                token = default_token_generator.make_token(visitante)
                uid = urlsafe_base64_encode(force_bytes(visitante.pk))

                # Construir URL de reset usando reverse
                reset_path = reverse(
                    "panel_visitante:restablecer_contraseña_confirm",
                    kwargs={"uidb64": uid, "token": token},
                )
                reset_url = request.build_absolute_uri(reset_path)

                # Preparar contexto para el template HTML
                email_context = {
                    "nombre": visitante.documento,
                    "reset_url": reset_url,
                    "year": datetime.now().year,
                }

                # Renderizar template HTML
                html_content = render_to_string(
                    "email_restablecer_visitante.html", email_context
                )
                text_content = strip_tags(html_content)

                # Enviar correo HTML
                subject = "🔐 Recuperación de Contraseña - MINEGATE"
                email_msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL or "noreply@minegate.com",
                    to=[visitante.correo],
                )
                email_msg.attach_alternative(html_content, "text/html")
                try:
                    email_msg.send()
                    messages.success(
                        request,
                        "Se ha enviado un correo con instrucciones para restablecer tu contraseña.",
                    )
                except Exception as e:
                    messages.warning(
                        request,
                        "El correo no se pudo enviar. Por favor intenta más tarde.",
                    )
                    print(f"Error enviando email: {str(e)}")
            else:
                # Por seguridad, mostrar el mismo mensaje aunque no exista el email
                messages.success(
                    request,
                    "Si el correo existe en nuestro sistema, recibirás instrucciones para restablecer tu contraseña.",
                )

            return redirect("panel_visitante:correo_enviado")
    else:
        form = PasswordResetRequestForm()

    context = {"form": form, "titulo": "Recuperar Contraseña"}
    return render(request, "solicitar_recuperacion_visitante.html", context)


def correo_enviado_view(request):
    """
    Vista que se muestra después de enviar el correo de recuperación
    """
    return render(request, "correo_enviado_visitante.html")


@csrf_protect
def restablecer_contraseña_confirm(request, uidb64, token):
    """
    Vista para confirmar y restablecer la contraseña con token
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        visitante = RegistroVisitante.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, RegistroVisitante.DoesNotExist):
        visitante = None

    if visitante is not None and default_token_generator.check_token(visitante, token):
        if request.method == "POST":
            form = PasswordResetConfirmForm(request.POST)
            if form.is_valid():
                password = form.cleaned_data["password1"]
                visitante.set_password(password)
                visitante.save()

                messages.success(
                    request,
                    "¡Tu contraseña ha sido actualizada exitosamente! Ahora puedes iniciar sesión.",
                )
                return redirect("panel_visitante:contraseña_actualizada")
        else:
            form = PasswordResetConfirmForm()

        context = {
            "form": form,
            "validlink": True,
            "titulo": "Establecer Nueva Contraseña",
        }
        return render(request, "restablecer_contraseña_confirm_visitante.html", context)
    else:
        messages.error(request, "El enlace de recuperación es inválido o ha expirado.")
        context = {"validlink": False, "titulo": "Enlace Inválido"}
        return render(request, "restablecer_contraseña_confirm_visitante.html", context)


def contraseña_actualizada_view(request):
    """
    Vista que se muestra después de actualizar la contraseña
    """
    return render(request, "contraseña_actualizada_visitante.html")


def actualizar_perfil(request):
    """
    Vista para que el usuario actualice sus datos personales y contraseña
    """
    # Verificar que el usuario esté autenticado
    if not request.session.get("responsable_autenticado"):
        messages.warning(request, "Debe iniciar sesión para acceder a esta página.")
        return redirect("panel_visitante:login_responsable")

    documento = request.session.get("responsable_documento")
    rol = request.session.get("responsable_rol")
    visitante = RegistroVisitante.objects.filter(documento=documento).first()

    if not visitante:
        messages.error(request, "No se encontró el usuario.")
        return redirect("panel_visitante:login_responsable")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "actualizar_datos":
            form_perfil = ActualizarPerfilForm(request.POST, current_user=visitante)
            form_contrasena = CambiarContrasenaForm()

            if form_perfil.is_valid():
                visitante.nombre = form_perfil.cleaned_data["nombre"]
                visitante.apellido = form_perfil.cleaned_data["apellido"]
                visitante.tipo_documento = form_perfil.cleaned_data["tipo_documento"]
                visitante.telefono = form_perfil.cleaned_data["telefono"]
                visitante.correo = form_perfil.cleaned_data["correo"]
                visitante.save()

                # Actualizar sesión
                request.session["responsable_nombre"] = visitante.nombre
                request.session["responsable_apellido"] = visitante.apellido
                request.session["responsable_tipo_documento"] = visitante.tipo_documento
                request.session["responsable_telefono"] = visitante.telefono
                request.session["responsable_correo"] = visitante.correo
                request.session.modified = True

                messages.success(
                    request, "✅ Tus datos han sido actualizados exitosamente."
                )
                return redirect("panel_visitante:actualizar_perfil")

        elif action == "cambiar_contrasena":
            form_perfil = ActualizarPerfilForm(
                initial={
                    "nombre": visitante.nombre,
                    "apellido": visitante.apellido,
                    "tipo_documento": visitante.tipo_documento,
                    "telefono": visitante.telefono,
                    "correo": visitante.correo,
                },
                current_user=visitante,
            )
            form_contrasena = CambiarContrasenaForm(request.POST)

            if form_contrasena.is_valid():
                contrasena_actual = form_contrasena.cleaned_data["contrasena_actual"]

                if visitante.check_password(contrasena_actual):
                    nueva_contrasena = form_contrasena.cleaned_data["nueva_contrasena"]

                    if visitante.check_password(nueva_contrasena):
                        messages.error(
                            request,
                            "La nueva contraseña no puede ser igual a la actual.",
                        )
                        return redirect("panel_visitante:actualizar_perfil")

                    visitante.set_password(nueva_contrasena)
                    visitante.save()

                    messages.success(
                        request, "🔒 Tu contraseña ha sido actualizada exitosamente."
                    )
                    return redirect("panel_visitante:actualizar_perfil")
                else:
                    messages.error(request, "La contraseña actual es incorrecta.")
    else:
        form_perfil = ActualizarPerfilForm(
            initial={
                "nombre": visitante.nombre,
                "apellido": visitante.apellido,
                "tipo_documento": visitante.tipo_documento,
                "telefono": visitante.telefono,
                "correo": visitante.correo,
            },
            current_user=visitante,
        )
        form_contrasena = CambiarContrasenaForm()

    context = {
        "form_perfil": form_perfil,
        "form_contrasena": form_contrasena,
        "visitante": visitante,
        "titulo": "Actualizar Perfil",
        "volver_url": (
            reverse("panel_instructor_interno:panel")
            if rol == "interno"
            else (
                reverse("panel_instructor_externo:panel")
                if rol == "externo"
                else reverse("panel_visitante:panel_responsable")
            )
        ),
    }
    return render(request, "actualizar_perfil.html", context)


def actualizar_documento_asistente(request, tipo, asistente_id):
    """
    Permite actualizar documentos de un asistente.
    Soporta respuesta JSON cuando la solicitud es AJAX.
    """
    es_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if not request.session.get("responsable_autenticado"):
        if es_ajax:
            return JsonResponse({"success": False, "error": "No autenticado."}, status=401)
        return redirect("panel_visitante:login_responsable")

    correo = request.session.get("responsable_correo")

    if tipo == "interna":
        asistente = get_object_or_404(AsistenteVisitaInterna, id=asistente_id)
        visita = asistente.visita
    elif tipo == "externa":
        asistente = get_object_or_404(AsistenteVisitaExterna, id=asistente_id)
        visita = asistente.visita
    else:
        error_msg = "Tipo de visita no válido."
        if es_ajax:
            return JsonResponse({"success": False, "error": error_msg}, status=400)
        messages.error(request, error_msg)
        return _redirect_segun_rol(request)

    if not _tiene_acceso_por_correo(visita, correo):
        error_msg = "No tiene permiso para esta acción."
        if es_ajax:
            return JsonResponse({"success": False, "error": error_msg}, status=403)
        messages.error(request, error_msg)
        return _redirect_segun_rol(request)

    if request.method != "POST":
        if es_ajax:
            return JsonResponse({"success": False, "error": "Método no permitido."}, status=405)
        return redirect("panel_visitante:registrar_asistentes", tipo=tipo, visita_id=visita.id)

    from documentos.models import Documento as DocumentoModel

    doc_salud = DocumentoModel.objects.filter(
        categoria="Formato Auto Reporte Condiciones de Salud"
    ).first()

    # Para AJAX llega "archivo_correccion". Para formulario tradicional,
    # se mantiene la compatibilidad con los nombres por asistente.
    archivo_salud = request.FILES.get("archivo_correccion") or request.FILES.get(
        f"documento_salud_{asistente_id}"
    )
    archivo_autorizacion = request.FILES.get(f"formato_padres_{asistente_id}")

    if not archivo_salud and not archivo_autorizacion:
        error_msg = "Debe seleccionar al menos un archivo para corregir."
        if es_ajax:
            return JsonResponse({"success": False, "error": error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect("panel_visitante:registrar_asistentes", tipo=tipo, visita_id=visita.id)

    actualizaciones_asistente = {
        "estado": "pendiente_documentos",
        "observaciones_revision": "",
    }

    if archivo_salud:
        if not doc_salud:
            error_msg = "Documento de salud no encontrado en el sistema."
            if es_ajax:
                return JsonResponse({"success": False, "error": error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect("panel_visitante:registrar_asistentes", tipo=tipo, visita_id=visita.id)

        if tipo == "interna":
            DocumentoSubidoAsistente.objects.update_or_create(
                documento_requerido=doc_salud,
                asistente_interna=asistente,
                asistente_externa=None,
                defaults={
                    "archivo": archivo_salud,
                    "estado": "pendiente",
                    "observaciones_revision": "",
                },
            )
        else:
            DocumentoSubidoAsistente.objects.update_or_create(
                documento_requerido=doc_salud,
                asistente_interna=None,
                asistente_externa=asistente,
                defaults={
                    "archivo": archivo_salud,
                    "estado": "pendiente",
                    "observaciones_revision": "",
                },
            )

    if archivo_autorizacion:
        actualizaciones_asistente.update(
            {
                "formato_autorizacion_padres": archivo_autorizacion,
                "estado_autorizacion_padres": "pendiente",
                "observaciones_autorizacion_padres": "",
            }
        )

    for campo, valor in actualizaciones_asistente.items():
        setattr(asistente, campo, valor)
    asistente.save(update_fields=list(actualizaciones_asistente.keys()))

    if visita.estado in ["documentos_enviados", "en_revision_documentos"]:
        visita.estado = "aprobada_inicial"
        visita.save(update_fields=["estado"])

    success_msg = (
        f"Se actualizaron los archivos de {asistente.nombre_completo}. "
        "Ya puede reenviar la solicitud final."
    )
    if es_ajax:
        return JsonResponse({"success": True, "message": success_msg})

    messages.success(request, success_msg)
    return redirect("panel_visitante:registrar_asistentes", tipo=tipo, visita_id=visita.id)


def actualizar_info_asistente(request, tipo, asistente_id):
    """Actualiza solo la informacion basica del asistente (sin documentos)."""
    if not request.session.get("responsable_autenticado"):
        return redirect("panel_visitante:login_responsable")

    correo = request.session.get("responsable_correo")
    if tipo == "interna":
        asistente = get_object_or_404(AsistenteVisitaInterna, id=asistente_id)
        visita = asistente.visita
        if not _tiene_acceso_por_correo(visita, correo):
            messages.error(request, "No tiene permiso para esta accion.")
            return _redirect_segun_rol(request)
    elif tipo == "externa":
        asistente = get_object_or_404(AsistenteVisitaExterna, id=asistente_id)
        visita = asistente.visita
        if not _tiene_acceso_por_correo(visita, correo):
            messages.error(request, "No tiene permiso para esta accion.")
            return _redirect_segun_rol(request)
    else:
        messages.error(request, "Tipo de visita no valido.")
        return _redirect_segun_rol(request)

    if request.method == "POST":
        nombre = request.POST.get("nombre_completo", "").strip()
        tipo_doc = request.POST.get("tipo_documento", "").strip()
        numero_doc = request.POST.get("numero_documento", "").strip()
        correo_asistente = request.POST.get("correo", "").strip()
        telefono = request.POST.get("telefono", "").strip()

        if not nombre or not tipo_doc or not numero_doc:
            messages.error(
                request, "Nombre, tipo y numero de documento son obligatorios."
            )
            return render(
                request,
                "actualizar_info_asistente.html",
                {
                    "asistente": asistente,
                    "tipo": tipo,
                    "visita": visita,
                    "tipo_documento_choices": asistente.TIPO_DOCUMENTO_CHOICES,
                },
            )

        duplicado_qs = asistente.__class__.objects.filter(
            visita=visita,
            numero_documento=numero_doc,
        ).exclude(id=asistente.id)

        if duplicado_qs.exists():
            messages.error(
                request,
                "Ya existe otro asistente en esta visita con ese numero de documento.",
            )
            return render(
                request,
                "actualizar_info_asistente.html",
                {
                    "asistente": asistente,
                    "tipo": tipo,
                    "visita": visita,
                    "tipo_documento_choices": asistente.TIPO_DOCUMENTO_CHOICES,
                },
            )

        asistente.nombre_completo = nombre
        asistente.tipo_documento = tipo_doc
        asistente.numero_documento = numero_doc
        asistente.correo = correo_asistente
        asistente.telefono = telefono

        try:
            asistente.save()
            messages.success(
                request, "Informacion del asistente actualizada correctamente."
            )
            return _redirect_segun_rol(request, tipo=tipo, visita_id=visita.id)
        except IntegrityError:
            messages.error(request, "No se pudo actualizar por conflicto de datos.")

    return render(
        request,
        "actualizar_info_asistente.html",
        {
            "asistente": asistente,
            "tipo": tipo,
            "visita": visita,
            "tipo_documento_choices": asistente.TIPO_DOCUMENTO_CHOICES,
        },
    )


def copiar_asistente_previo(request, tipo, visita_id, asistente_previo_id):
    """
    Copia un asistente previo de una visita anterior a la visita actual.
    """
    # Verificar autenticación
    if not request.session.get("responsable_autenticado"):
        return redirect("panel_visitante:login_responsable")

    correo = request.session.get("responsable_correo")
    # Obtener visita actual
    if tipo == "interna":
        visita = get_object_or_404(
            VisitaInterna,
            id=visita_id,
            correo_responsable__iexact=correo,
        )
        # Obtener asistente previo (de cualquier visita anterior con el mismo número de ficha)
        asistente_original = get_object_or_404(
            AsistenteVisitaInterna, id=asistente_previo_id, puede_reutilizar=True
        )
    elif tipo == "externa":
        visita = get_object_or_404(
            VisitaExterna,
            id=visita_id,
            correo_responsable__iexact=correo,
        )
        # Obtener asistente previo (de cualquier visita anterior con el mismo nombre)
        asistente_original = get_object_or_404(
            AsistenteVisitaExterna, id=asistente_previo_id, puede_reutilizar=True
        )
    else:
        messages.error(request, "Tipo de visita no válido.")
        return _redirect_segun_rol(request)

    # Verificar que no esté duplicado
    asistentes_actuales = visita.asistentes.all()
    max_asistentes = (
        visita.cantidad_aprendices if tipo == "interna" else visita.cantidad_visitantes
    )

    if asistentes_actuales.count() >= max_asistentes:
        messages.error(
            request, f"Ya se alcanzó el límite de {max_asistentes} asistentes."
        )
        return redirect(
            "panel_visitante:registrar_asistentes", tipo=tipo, visita_id=visita_id
        )

    # Verificar si el asistente ya está en la visita actual
    if asistentes_actuales.filter(
        numero_documento=asistente_original.numero_documento
    ).exists():
        messages.warning(
            request,
            f"El asistente {asistente_original.nombre_completo} ya está registrado en esta visita.",
        )
        return redirect(
            "panel_visitante:registrar_asistentes", tipo=tipo, visita_id=visita_id
        )

    try:
        # Copiar asistente
        if tipo == "interna":
            nuevo_asistente = AsistenteVisitaInterna.objects.create(
                visita=visita,
                nombre_completo=asistente_original.nombre_completo,
                tipo_documento=asistente_original.tipo_documento,
                numero_documento=asistente_original.numero_documento,
                correo=asistente_original.correo,
                telefono=asistente_original.telefono,
                es_reutilizado=True,
                visita_original=asistente_original,
            )
            # Copiar el archivo de autorización de padres si existe
            if asistente_original.formato_autorizacion_padres:
                from django.core.files.base import ContentFile

                archivo_original = asistente_original.formato_autorizacion_padres
                nuevo_asistente.formato_autorizacion_padres.save(
                    archivo_original.name,
                    ContentFile(archivo_original.read()),
                    save=True,
                )
        else:
            nuevo_asistente = AsistenteVisitaExterna.objects.create(
                visita=visita,
                nombre_completo=asistente_original.nombre_completo,
                tipo_documento=asistente_original.tipo_documento,
                numero_documento=asistente_original.numero_documento,
                correo=asistente_original.correo,
                telefono=asistente_original.telefono,
                es_reutilizado=True,
                visita_original=asistente_original,
            )
            # Copiar el archivo de autorización de padres si existe
            if asistente_original.formato_autorizacion_padres:
                from django.core.files.base import ContentFile

                archivo_original = asistente_original.formato_autorizacion_padres
                nuevo_asistente.formato_autorizacion_padres.save(
                    archivo_original.name,
                    ContentFile(archivo_original.read()),
                    save=True,
                )

        messages.success(
            request,
            f'Asistente "{nuevo_asistente.nombre_completo}" reutilizado correctamente de una visita anterior.',
        )
    except Exception as e:
        if "unique" in str(e).lower():
            messages.error(
                request,
                "Este asistente ya está registrado para esta visita.",
            )
        else:
            messages.error(request, f"Error al reutilizar: {str(e)}")

    return redirect(
        "panel_visitante:registrar_asistentes", tipo=tipo, visita_id=visita_id
    )
