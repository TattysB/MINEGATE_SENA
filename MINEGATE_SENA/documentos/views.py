from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_exempt
from visitaInterna.models import VisitaInterna, AsistenteVisitaInterna
from visitaExterna.models import VisitaExterna, AsistenteVisitaExterna
from .models import Documento, DocumentoSubidoAsistente


def devolver_visita_a_agendador(visita):
    """Retorna la visita a estado editable para permitir correcciones y reenvío."""
    if visita and visita.estado in ["documentos_enviados", "en_revision_documentos"]:
        visita.estado = "aprobada_inicial"
        visita.save(update_fields=["estado"])


def registro_publico_asistentes(request, token, tipo):
    """
    Vista pública para registro de asistentes usando enlace único con token.
    No requiere autenticación, solo el token válido.
    """
    # Obtener la visita según el tipo y token
    if tipo == "interna":
        visita = get_object_or_404(VisitaInterna, token_acceso=token)
        asistentes = visita.asistentes.all()
        max_asistentes = visita.cantidad_aprendices
    elif tipo == "externa":
        visita = get_object_or_404(VisitaExterna, token_acceso=token)
        asistentes = visita.asistentes.all()
        max_asistentes = visita.cantidad_visitantes
    else:
        messages.error(request, "Tipo de visita no válido.")
        return redirect("core:index")

    # Verificar que la visita esté aprobada inicialmente para registro de asistentes
    if visita.estado not in [
        "aprobada_inicial",
        "documentos_enviados",
        "en_revision_documentos",
    ]:
        context = {
            "visita": visita,
            "tipo": tipo,
            "estado_no_aprobado": True,
        }
        return render(request, "documentos/registro_publico_asistentes.html", context)

    # Verificar límite de asistentes
    asistentes_actuales = asistentes.count()
    puede_agregar = asistentes_actuales < max_asistentes

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
            documento_identidad = request.FILES.get("documento_identidad")
            documento_adicional = request.FILES.get("documento_adicional")
            formato_autorizacion_padres = request.FILES.get(
                "formato_autorizacion_padres"
            )

            if nombre and tipo_doc and num_doc:
                try:
                    if tipo == "interna":
                        nuevo_asistente = AsistenteVisitaInterna(
                            visita=visita,
                            nombre_completo=nombre,
                            tipo_documento=tipo_doc,
                            numero_documento=num_doc,
                            correo=correo_asistente,
                            telefono=telefono,
                            estado="pendiente_documentos",
                        )
                        if documento_identidad:
                            nuevo_asistente.documento_identidad = documento_identidad
                        if documento_adicional:
                            nuevo_asistente.documento_adicional = documento_adicional
                        if formato_autorizacion_padres:
                            nuevo_asistente.formato_autorizacion_padres = (
                                formato_autorizacion_padres
                            )
                        nuevo_asistente.save()
                    else:
                        nuevo_asistente = AsistenteVisitaExterna(
                            visita=visita,
                            nombre_completo=nombre,
                            tipo_documento=tipo_doc,
                            numero_documento=num_doc,
                            correo=correo_asistente,
                            telefono=telefono,
                            estado="pendiente_documentos",
                        )
                        if documento_identidad:
                            nuevo_asistente.documento_identidad = documento_identidad
                        if documento_adicional:
                            nuevo_asistente.documento_adicional = documento_adicional
                        if formato_autorizacion_padres:
                            nuevo_asistente.formato_autorizacion_padres = (
                                formato_autorizacion_padres
                            )
                        nuevo_asistente.save()

                    messages.success(
                        request,
                        f'¡Asistente "{nombre}" registrado correctamente! Estado: Pendiente de revisión de documentos.',
                    )

                    # Redirigir según el tipo
                    if tipo == "interna":
                        return redirect(
                            "documentos:registro_publico_interna", token=token
                        )
                    else:
                        return redirect(
                            "documentos:registro_publico_externa", token=token
                        )

                except Exception as e:
                    if "unique" in str(e).lower():
                        messages.error(
                            request,
                            "Este número de documento ya está registrado para esta visita.",
                        )
                    else:
                        messages.error(request, f"Error al registrar: {str(e)}")
            else:
                messages.error(
                    request,
                    "Complete todos los campos obligatorios (nombre, tipo y número de documento).",
                )

    # Generar enlace completo para compartir
    enlace_registro = request.build_absolute_uri()

    # Obtener documentos disponibles para descargar, agrupados por categoría
    documentos_disponibles = Documento.objects.all().order_by(
        "categoria", "-fecha_subida"
    )
    documentos_por_categoria = {}
    for doc in documentos_disponibles:
        cat_display = doc.get_categoria_display()
        if cat_display not in documentos_por_categoria:
            documentos_por_categoria[cat_display] = []
        documentos_por_categoria[cat_display].append(doc)

    context = {
        "visita": visita,
        "tipo": tipo,
        "token": token,
        "asistentes": asistentes,
        "asistentes_actuales": asistentes_actuales,
        "max_asistentes": max_asistentes,
        "puede_agregar": puede_agregar,
        "enlace_registro": enlace_registro,
        "estado_no_aprobado": False,
        "documentos_por_categoria": documentos_por_categoria,
    }

    return render(request, "documentos/registro_publico_asistentes.html", context)


def eliminar_asistente_publico(request, tipo, token, asistente_id):
    """
    Eliminar un asistente desde el enlace público.
    """
    if tipo == "interna":
        visita = get_object_or_404(VisitaInterna, token_acceso=token)
        asistente = get_object_or_404(
            AsistenteVisitaInterna, id=asistente_id, visita=visita
        )
        asistente.delete()
        messages.success(request, "Asistente eliminado correctamente.")
        return redirect("documentos:registro_publico_interna", token=token)
    elif tipo == "externa":
        visita = get_object_or_404(VisitaExterna, token_acceso=token)
        asistente = get_object_or_404(
            AsistenteVisitaExterna, id=asistente_id, visita=visita
        )
        asistente.delete()
        messages.success(request, "Asistente eliminado correctamente.")
        return redirect("documentos:registro_publico_externa", token=token)
    else:
        messages.error(request, "Tipo de visita no válido.")
        return redirect("core:index")


@require_POST
def actualizar_asistente_publico(request, tipo, token, asistente_id):
    """Permite corregir archivos de un asistente registrado desde el enlace público."""
    if tipo == "interna":
        visita = get_object_or_404(VisitaInterna, token_acceso=token)
        asistente = get_object_or_404(
            AsistenteVisitaInterna, id=asistente_id, visita=visita
        )
        redirect_name = "documentos:registro_publico_interna"
        docs_qs = DocumentoSubidoAsistente.objects.filter(asistente_interna=asistente)
    elif tipo == "externa":
        visita = get_object_or_404(VisitaExterna, token_acceso=token)
        asistente = get_object_or_404(
            AsistenteVisitaExterna, id=asistente_id, visita=visita
        )
        redirect_name = "documentos:registro_publico_externa"
        docs_qs = DocumentoSubidoAsistente.objects.filter(asistente_externa=asistente)
    else:
        messages.error(request, "Tipo de visita no válido.")
        return redirect("core:index")

    if visita.estado not in ["aprobada_inicial", "documentos_enviados", "en_revision_documentos"]:
        messages.error(
            request,
            "La visita no está disponible para correcciones en este momento.",
        )
        return redirect(redirect_name, token=token)

    documento_identidad = request.FILES.get("documento_identidad")
    documento_adicional = request.FILES.get("documento_adicional")
    formato_autorizacion_padres = request.FILES.get("formato_autorizacion_padres")

    if not any([documento_identidad, documento_adicional, formato_autorizacion_padres]):
        messages.error(request, "Debe adjuntar al menos un archivo para corregir.")
        return redirect(redirect_name, token=token)

    if documento_identidad:
        asistente.documento_identidad = documento_identidad
    if documento_adicional:
        asistente.documento_adicional = documento_adicional
    if formato_autorizacion_padres:
        asistente.formato_autorizacion_padres = formato_autorizacion_padres
        asistente.estado_autorizacion_padres = "pendiente"
        asistente.observaciones_autorizacion_padres = ""

    asistente.estado = "pendiente_documentos"
    asistente.observaciones_revision = ""
    asistente.save()

    docs_qs.filter(estado="rechazado").update(estado="pendiente", observaciones_revision="")
    devolver_visita_a_agendador(visita)

    messages.success(
        request,
        f"Se actualizaron los archivos de {asistente.nombre_completo}. Ya puede reenviar la solicitud final.",
    )
    return redirect(redirect_name, token=token)


# =============================================
# API para gestión de documentos en panel admin
# =============================================


@login_required(login_url="usuarios:login")
def listar_documentos_api(request):
    """API: Retorna la lista de documentos en JSON."""
    from django.urls import reverse

    documentos = Documento.objects.all()

    # Filtrar por categoría si se envía
    categoria = request.GET.get("categoria", "")
    if categoria:
        documentos = documentos.filter(categoria=categoria)

    # Buscar por título, nombre de archivo o categoría
    buscar = request.GET.get("buscar", "")
    if buscar:
        from django.db.models import Q

        documentos = documentos.filter(
            Q(titulo__icontains=buscar)
            | Q(archivo__icontains=buscar)
            | Q(categoria__icontains=buscar)
        )

    data = []
    for doc in documentos:
        # Generar URL a través de la vista descargar_documento
        archivo_url = reverse(
            "documentos:descargar_documento", kwargs={"documento_id": doc.id}
        )

        data.append(
            {
                "id": doc.id,
                "titulo": doc.categoria,
                "archivo_url": archivo_url,
                "nombre_archivo": doc.nombre_archivo,
                "categoria": doc.categoria,
                "categoria_display": doc.get_categoria_display(),
                "descripcion": doc.descripcion or "",
                "subido_por": doc.subido_por.get_full_name() or doc.subido_por.username,
                "fecha_subida": doc.fecha_subida.strftime("%d/%m/%Y %H:%M"),
                "tamaño": doc.tamaño_legible,
                "extension": doc.extension,
            }
        )

    return JsonResponse({"documentos": data, "total": len(data)})


@login_required(login_url="usuarios:login")
def categorias_faltantes_api(request):
    """API: Retorna categorías pendientes por cargar."""
    cats_validas = [c[0] for c in Documento.CATEGORIA_CHOICES]
    categorias_ocupadas = set(Documento.objects.values_list("categoria", flat=True))
    categorias_faltantes = [c for c in cats_validas if c not in categorias_ocupadas]

    return JsonResponse(
        {
            "categorias_faltantes": categorias_faltantes,
            "categorias_ocupadas": list(categorias_ocupadas),
            "total_faltantes": len(categorias_faltantes),
        }
    )


@login_required(login_url="usuarios:login")
@require_POST
def subir_documentos_api(request):
    """API: Sube uno o varios documentos."""
    archivos = request.FILES.getlist("archivos")
    categorias = request.POST.getlist("categorias")
    descripcion = request.POST.get("descripcion", "")

    if not archivos:
        return JsonResponse(
            {"success": False, "error": "No se seleccionaron archivos."}, status=400
        )

    import os

    # Extensiones permitidas
    extensiones_permitidas = [
        ".pdf",
        ".doc",
        ".docx",
    ]
    max_size = 10 * 1024 * 1024  # 10 MB

    documentos_creados = []
    errores = []

    # Categorías válidas del modelo
    cats_validas = [c[0] for c in Documento.CATEGORIA_CHOICES]
    categorias_existentes = set(Documento.objects.values_list("categoria", flat=True))

    # Normalizar nombres de archivo ya existentes en BD
    nombres_existentes = {
        os.path.basename(nombre).lower()
        for nombre in Documento.objects.values_list("archivo", flat=True)
        if nombre
    }

    categorias_en_lote = set()
    nombres_en_lote = set()

    for idx, archivo in enumerate(archivos):
        _, ext = os.path.splitext(archivo.name)
        ext = ext.lower()

        if ext not in extensiones_permitidas:
            errores.append(f'"{archivo.name}": extensión {ext} no permitida.')
            continue

        if archivo.size > max_size:
            errores.append(f'"{archivo.name}": excede el tamaño máximo de 10 MB.')
            continue

        nombre_normalizado = archivo.name.lower()
        if (
            nombre_normalizado in nombres_existentes
            or nombre_normalizado in nombres_en_lote
        ):
            errores.append(f'"{archivo.name}": ya existe un archivo con ese nombre.')
            continue

        # Obtener categoría individual del archivo
        cat_archivo = (
            categorias[idx]
            if idx < len(categorias)
            else (cats_validas[0] if cats_validas else "EPP Necesarios")
        )
        if cat_archivo not in cats_validas:
            cat_archivo = cats_validas[0] if cats_validas else "EPP Necesarios"

        if cat_archivo in categorias_existentes or cat_archivo in categorias_en_lote:
            errores.append(
                f'"{archivo.name}": la categoría "{cat_archivo}" ya fue cargada.'
            )
            continue

        # El título visible debe ser el label del formato/categoría
        titulo = cat_archivo

        doc = Documento(
            titulo=titulo,
            archivo=archivo,
            categoria=cat_archivo,
            descripcion=descripcion,
            subido_por=request.user,
            tamaño=archivo.size,
        )
        doc.save()
        nombres_en_lote.add(nombre_normalizado)
        categorias_en_lote.add(cat_archivo)
        documentos_creados.append(
            {
                "id": doc.id,
                "titulo": doc.categoria,
                "nombre_archivo": doc.nombre_archivo,
            }
        )

    return JsonResponse(
        {
            "success": True,
            "creados": len(documentos_creados),
            "documentos": documentos_creados,
            "errores": errores,
        }
    )


@login_required(login_url="usuarios:login")
@require_POST
def eliminar_documento_api(request, documento_id):
    """API: Elimina un documento."""
    doc = get_object_or_404(Documento, id=documento_id)

    # Eliminar el archivo físico
    if doc.archivo:
        try:
            doc.archivo.delete(save=False)
        except Exception:
            pass

    doc.delete()
    return JsonResponse(
        {"success": True, "message": "Documento eliminado correctamente."}
    )


@login_required(login_url="usuarios:login")
@xframe_options_exempt
def descargar_documento(request, documento_id):
    """Descarga o sirve un documento para visualización."""
    import logging

    logger = logging.getLogger(__name__)

    logger.info(
        f"Intentando servir documento {documento_id} para usuario {request.user}"
    )

    try:
        doc = get_object_or_404(Documento, id=documento_id)
        logger.info(f"Documento encontrado: {doc.titulo}")
    except:
        logger.error(f"Documento {documento_id} no encontrado")
        from django.http import HttpResponseNotFound

        return HttpResponseNotFound("El documento no existe")

    if not doc.archivo:
        logger.error(f"El documento {documento_id} no tiene archivo")
        from django.http import HttpResponseNotFound

        return HttpResponseNotFound("El archivo no existe")

    from django.http import FileResponse
    import mimetypes

    try:
        # Verificar que el archivo existe
        if not doc.archivo.storage.exists(doc.archivo.name):
            logger.error(f"El archivo físico no existe: {doc.archivo.name}")
            from django.http import HttpResponseNotFound

            return HttpResponseNotFound("El archivo no existe en el servidor")

        logger.info(f"Abriendo archivo: {doc.archivo.name}")
        # Abrir el archivo
        archivo = doc.archivo.open("rb")

        # Determinar el tipo MIME
        tipo_mime, _ = mimetypes.guess_type(doc.archivo.name)
        if not tipo_mime:
            tipo_mime = "application/octet-stream"

        logger.info(f"MIME type detectado: {tipo_mime}")

        # Crear respuesta
        response = FileResponse(archivo, content_type=tipo_mime)

        # Para PDFs e imágenes, mostrarlas en línea (inline)
        # Para otros archivos, forzar descarga (attachment)
        ext = doc.extension.lower().lstrip(".")  # Remover el punto (.pdf -> pdf)
        logger.info(f"Extensión detectada: {ext}")

        if ext == "pdf" or ext in ["jpg", "jpeg", "png", "gif", "webp"]:
            response["Content-Disposition"] = f'inline; filename="{doc.nombre_archivo}"'
            logger.info(f"Sirviendo como inline (mostrar en navegador)")
        else:
            response["Content-Disposition"] = (
                f'attachment; filename="{doc.nombre_archivo}"'
            )
            logger.info(f"Sirviendo como attachment (descargar)")

        return response
    except Exception as e:
        logger.exception(f"Error al servir el archivo: {str(e)}")
        from django.http import HttpResponseServerError

        return HttpResponseServerError(f"Error al servir el archivo: {str(e)}")


@xframe_options_exempt
def ver_documento_inline(request, documento_id):
    """Sirve un documento para visualización inline en iframe (sin restricción X-Frame-Options)."""
    import mimetypes
    from django.http import FileResponse, HttpResponseNotFound

    doc = get_object_or_404(Documento, id=documento_id)

    if not doc.archivo or not doc.archivo.storage.exists(doc.archivo.name):
        return HttpResponseNotFound("El archivo no existe")

    archivo = doc.archivo.open("rb")
    tipo_mime, _ = mimetypes.guess_type(doc.archivo.name)
    if not tipo_mime:
        tipo_mime = "application/octet-stream"

    response = FileResponse(archivo, content_type=tipo_mime)
    response["Content-Disposition"] = f'inline; filename="{doc.nombre_archivo}"'
    response["X-Frame-Options"] = "SAMEORIGIN"
    return response


def descargar_documento_publico(request, documento_id):
    """Descarga pública de un documento con el nombre y extensión correctos."""
    import mimetypes
    from django.http import FileResponse, HttpResponseNotFound

    doc = get_object_or_404(Documento, id=documento_id)

    if not doc.archivo or not doc.archivo.storage.exists(doc.archivo.name):
        return HttpResponseNotFound("El archivo no existe")

    archivo = doc.archivo.open("rb")
    tipo_mime, _ = mimetypes.guess_type(doc.archivo.name)
    if not tipo_mime:
        tipo_mime = "application/octet-stream"

    response = FileResponse(archivo, content_type=tipo_mime)
    response["Content-Disposition"] = f'attachment; filename="{doc.nombre_archivo}"'
    response["X-Frame-Options"] = "SAMEORIGIN"
    return response


@xframe_options_exempt
def ver_documento_asistente_inline(request, documento_subido_id):
    """Sirve un documento subido por asistente para visualización inline en iframe."""
    import mimetypes
    from django.http import FileResponse, HttpResponseNotFound

    doc = get_object_or_404(DocumentoSubidoAsistente, id=documento_subido_id)

    if not doc.archivo or not doc.archivo.storage.exists(doc.archivo.name):
        return HttpResponseNotFound("El archivo no existe")

    archivo = doc.archivo.open("rb")
    tipo_mime, _ = mimetypes.guess_type(doc.archivo.name)
    if not tipo_mime:
        tipo_mime = "application/octet-stream"

    response = FileResponse(archivo, content_type=tipo_mime)
    response["Content-Disposition"] = f'inline; filename="{doc.nombre_archivo}"'
    response["X-Frame-Options"] = "SAMEORIGIN"
    return response


@xframe_options_exempt
def descargar_documento_asistente(request, documento_subido_id):
    """Descarga un documento subido por asistente."""
    import mimetypes
    from django.http import FileResponse, HttpResponseNotFound

    doc = get_object_or_404(DocumentoSubidoAsistente, id=documento_subido_id)

    if not doc.archivo or not doc.archivo.storage.exists(doc.archivo.name):
        return HttpResponseNotFound("El archivo no existe")

    archivo = doc.archivo.open("rb")
    tipo_mime, _ = mimetypes.guess_type(doc.archivo.name)
    if not tipo_mime:
        tipo_mime = "application/octet-stream"

    response = FileResponse(archivo, content_type=tipo_mime)
    response["Content-Disposition"] = f'attachment; filename="{doc.nombre_archivo}"'
    return response


@login_required(login_url="usuarios:login")
@require_POST
def revisar_documento_asistente_api(request, documento_subido_id):
    """API: Aprueba o rechaza un documento específico de un asistente."""
    doc = get_object_or_404(DocumentoSubidoAsistente, id=documento_subido_id)
    estado = request.POST.get("estado")
    observaciones = request.POST.get("observaciones", "")

    if estado not in ["aprobado", "rechazado"]:
        return JsonResponse(
            {"success": False, "error": "Estado no válido."}, status=400
        )

    doc.estado = estado
    doc.observaciones_revision = observaciones
    doc.save()

    asistente = doc.asistente_interna or doc.asistente_externa

    # Sincronizar estado del asistente si hay un rechazo
    if estado == "rechazado":
        if asistente:
            asistente.estado = "documentos_rechazados"
            asistente.observaciones_revision = (
                f"Documento '{doc.documento_requerido.titulo}' rechazado: {observaciones}"
                if observaciones
                else f"Documento '{doc.documento_requerido.titulo}' rechazado."
            )
            asistente.save()

    return JsonResponse(
        {
            "success": True,
            "message": (
                f"Documento marcado como {estado} correctamente."
                if estado == "aprobado"
                else "Documento rechazado. Queda pendiente de corrección."
            ),
            "nuevo_estado": estado,
        }
    )


@require_POST
def enviar_solicitud_final(request, token, tipo):
    """
    Cambia el estado de la visita a 'documentos_enviados' para indicar que
    el organizador ha finalizado el registro de asistentes.
    """
    if tipo == "interna":
        visita = get_object_or_404(VisitaInterna, token_acceso=token)
    elif tipo == "externa":
        visita = get_object_or_404(VisitaExterna, token_acceso=token)
    else:
        return JsonResponse({"success": False, "error": "Tipo no válido."}, status=400)

    if visita.estado != "aprobada_inicial":
        return JsonResponse(
            {
                "success": False,
                "error": "La solicitud ya fue enviada o no se puede enviar en este estado.",
            },
            status=400,
        )

    cantidad_maxima = (
        visita.cantidad_aprendices if tipo == "interna" else visita.cantidad_visitantes
    )
    if cantidad_maxima < 1:
        return JsonResponse(
            {
                "success": False,
                "error": "La visita debe tener una cantidad de asistentes mayor a cero antes de enviar la solicitud final.",
            },
            status=400,
        )

    # Verificar que haya al menos un asistente registrado
    if visita.asistentes.count() == 0:
        return JsonResponse(
            {
                "success": False,
                "error": "Debe registrar al menos un asistente antes de enviar la solicitud final.",
            },
            status=400,
        )

    # No permitir reenvío si aún hay asistentes con rechazo pendiente de corrección
    if visita.asistentes.filter(estado="documentos_rechazados").exists():
        return JsonResponse(
            {
                "success": False,
                "error": "Hay asistentes con documentos rechazados. Corrija los archivos antes de reenviar.",
            },
            status=400,
        )

    visita.estado = "documentos_enviados"
    visita.save()

    return JsonResponse(
        {
            "success": True,
            "message": "Solicitud final enviada correctamente. El administrador revisará la información.",
        }
    )
