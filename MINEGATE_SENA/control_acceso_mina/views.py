import json

from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Subquery
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from core.sanitization import sanitize_document_number, sanitize_text, sanitize_token

from .models import RegistroAccesoMina


ESTADOS_VISITA_CONFIRMADA = ['confirmada', 'aprobada_final']


@login_required
@require_POST
def registrar_acceso(request):
    """
    Endpoint AJAX para registrar entrada/salida por visita específica.
    """
    try:
        body = json.loads(request.body)
        documento = sanitize_document_number(body.get('documento', ''), max_length=50)
        qr_data = sanitize_text(body.get('qr_data', ''), max_length=500, allow_newlines=False)
        selected_visit_id = sanitize_text(str(body.get('selected_visit_id', '')), max_length=12, allow_newlines=False)
        selected_visit_type = sanitize_token(str(body.get('selected_visit_type', '')), max_length=20)
    except (json.JSONDecodeError, AttributeError):
        documento = sanitize_document_number(request.POST.get('documento', ''), max_length=50)
        qr_data = sanitize_text(request.POST.get('qr_data', ''), max_length=500, allow_newlines=False)
        selected_visit_id = sanitize_text(str(request.POST.get('selected_visit_id', '')), max_length=12, allow_newlines=False)
        selected_visit_type = sanitize_token(str(request.POST.get('selected_visit_type', '')), max_length=20)

    if selected_visit_type not in ('interna', 'externa') or not selected_visit_id.isdigit():
        return JsonResponse({
            'success': False,
            'error': 'Debe seleccionar una visita válida antes de registrar.'
        }, status=400)

    visita_id = int(selected_visit_id)
    visita_data = _obtener_visita_confirmada_hoy(selected_visit_type, visita_id)
    if not visita_data:
        return JsonResponse({
            'success': False,
            'error': 'La visita seleccionada no está confirmada para hoy.'
        }, status=400)

    qr_info = _parse_qr_data(qr_data or documento)
    if qr_info.get('documento'):
        if documento and '|' not in documento and qr_info['documento'] != documento:
            return JsonResponse({
                'success': False,
                'error': 'El documento no coincide con el contenido del QR.'
            }, status=400)
        documento = sanitize_document_number(qr_info['documento'], max_length=50)

    if not documento:
        return JsonResponse({
            'success': False,
            'error': 'Ingrese o escanee un número de documento.'
        }, status=400)

    asistente_data, error = _buscar_asistente_en_visita(
        documento=documento,
        tipo_visita=selected_visit_type,
        visita_id=visita_id,
        qr_info=qr_info,
    )

    if error:
        return JsonResponse({'success': False, 'error': error}, status=400)

    if not asistente_data:
        return JsonResponse({
            'success': False,
            'error': f'Documento {documento} no autorizado para la visita seleccionada.'
        }, status=404)

    ultimo_registro = RegistroAccesoMina.objects.filter(
        documento=documento,
        visita_tipo=selected_visit_type,
        visita_id=visita_id,
    ).order_by('-fecha_hora').first()

    tipo_movimiento = 'SALIDA' if (ultimo_registro and ultimo_registro.tipo == 'ENTRADA') else 'ENTRADA'

    registro = RegistroAccesoMina.objects.create(
        documento=documento,
        nombre_completo=asistente_data['nombre_completo'],
        categoria=asistente_data['categoria'],
        visita_tipo=selected_visit_type,
        visita_id=visita_id,
        tipo=tipo_movimiento,
        registrado_por=request.user,
    )

    personas_dentro_visita = _contar_personas_en_visita_mina(selected_visit_type, visita_id)

    return JsonResponse({
        'success': True,
        'data': {
            'documento': documento,
            'nombre_completo': asistente_data['nombre_completo'],
            'categoria': asistente_data['categoria'],
            'tipo': tipo_movimiento,
            'fecha_hora': timezone.localtime(registro.fecha_hora).strftime('%d/%m/%Y %H:%M:%S'),
            'personas_en_mina': personas_dentro_visita,
            'visita': visita_data,
        }
    })


@login_required
@require_GET
def visitas_hoy(request):
    """
    Lista visitas internas y externas confirmadas para hoy.
    """
    data = _obtener_visitas_hoy_data()
    return JsonResponse({
        'success': True,
        'visitas': data['visitas'],
        'totales': data['totales'],
    })


@login_required
@require_GET
def porteria_visita(request, tipo_visita, visita_id):
    """
    Pantalla dedicada para escaneo y control de acceso de una visita puntual.
    """
    if not (request.user.is_superuser or request.user.is_staff):
        return render(
            request,
            'control_acceso_mina/porteria_visita.html',
            {
                'visita': None,
                'error_visita': 'No tienes permisos para acceder al control de acceso.',
                'panel_role_label': 'Usuario',
                'seccion_activa': 'control_acceso',
            },
            status=403,
        )

    visita_data = _obtener_visita_confirmada_hoy(tipo_visita, visita_id)
    es_coordinador = request.user.groups.filter(name='coordinador').exists()
    es_sst = request.user.groups.filter(name='sst').exists()

    usuario_es_admin_panel = request.user.is_superuser or (
        request.user.is_staff and not es_sst and not es_coordinador
    )
    usuario_solo_sst = es_sst and not request.user.is_superuser

    if usuario_es_admin_panel:
        panel_role_label = 'Administrador'
    elif usuario_solo_sst:
        panel_role_label = 'SST'
    elif es_coordinador:
        panel_role_label = 'Coordinador'
    else:
        panel_role_label = 'Usuario'

    contexto_base_panel = {
        'es_superusuario': usuario_es_admin_panel,
        'solo_sst': usuario_solo_sst,
        'solo_coordinador': es_coordinador,
        'perfil': getattr(request.user, 'perfil', None),
        'perfil_panel': getattr(request.user, 'perfil', None),
        'panel_role_label': panel_role_label,
        'seccion_activa': 'control_acceso',
    }

    if not visita_data:
        return render(
            request,
            'control_acceso_mina/porteria_visita.html',
            {
                **contexto_base_panel,
                'visita': None,
                'error_visita': 'La visita no existe o no está confirmada para hoy.',
            },
            status=404,
        )

    return render(
        request,
        'control_acceso_mina/porteria_visita.html',
        {
            **contexto_base_panel,
            'visita': visita_data,
            'error_visita': '',
        },
    )


@login_required
@require_GET
def datos_visita(request, tipo_visita, visita_id):
    """
    Datos de una visita puntual: asistentes habilitados, conteo actual y registros del día.
    """
    visita_data = _obtener_visita_confirmada_hoy(tipo_visita, visita_id)
    if not visita_data:
        return JsonResponse({
            'success': False,
            'error': 'La visita no existe o no está confirmada para hoy.',
        }, status=404)

    registros_data = _obtener_registros_visita_hoy(tipo_visita, visita_id)
    personas_dentro_visita = _contar_personas_en_visita_mina(tipo_visita, visita_id)
    asistentes_data = _obtener_asistentes_visita_aprobados(tipo_visita, visita_id)
    estado_actual = _obtener_estado_actual_visita(tipo_visita, visita_id)

    entradas = sum(1 for r in registros_data if r['tipo'] == 'ENTRADA')
    salidas = sum(1 for r in registros_data if r['tipo'] == 'SALIDA')

    return JsonResponse({
        'success': True,
        'visita': visita_data,
        'personas_en_mina': personas_dentro_visita,
        'entradas_hoy': entradas,
        'salidas_hoy': salidas,
        'registros_hoy': registros_data,
        'asistentes_aprobados': asistentes_data,
        'personas_dentro': estado_actual['dentro'],
        'personas_fuera': estado_actual['fuera'],
    })


def _parse_qr_data(raw_text):
    """
    Parsea QR con formato: SENA|visita_id|documento|nombre|tipo
    """
    if not raw_text or '|' not in raw_text:
        return {}

    parts = [sanitize_text(p, max_length=120, allow_newlines=False) for p in str(raw_text).split('|')]
    if len(parts) < 5 or parts[0] != 'SENA':
        return {}

    visita_id = int(parts[1]) if parts[1].isdigit() else None
    tipo_token = sanitize_token(parts[4], max_length=20)
    tipo = tipo_token if tipo_token in ('interna', 'externa') else None

    return {
        'visita_id': visita_id,
        'documento': sanitize_document_number(parts[2], max_length=50),
        'nombre': sanitize_text(parts[3], max_length=200, allow_newlines=False),
        'tipo': tipo,
    }


def _formatear_horario(hora_inicio, hora_fin):
    inicio = hora_inicio.strftime('%H:%M') if hora_inicio else 'Por definir'
    fin = hora_fin.strftime('%H:%M') if hora_fin else 'Por definir'
    return f'{inicio} - {fin}'


def _obtener_visita_confirmada_hoy(tipo_visita, visita_id):
    hoy = timezone.localdate()

    if tipo_visita == 'interna':
        try:
            from visitaInterna.models import VisitaInterna

            visita = VisitaInterna.objects.filter(
                id=visita_id,
                estado__in=ESTADOS_VISITA_CONFIRMADA,
                fecha_visita=hoy,
            ).first()

            if not visita:
                return None

            return {
                'tipo': 'interna',
                'tipo_label': 'Interna',
                'visita_id': visita.id,
                'nombre': visita.nombre_programa,
                'responsable': visita.responsable,
                'horario': _formatear_horario(visita.hora_inicio, visita.hora_fin),
                'asistentes_aprobados': visita.asistentes.filter(estado='documentos_aprobados').count(),
                'url_porteria': reverse('control_acceso_mina:porteria_visita', args=['interna', visita.id]),
            }
        except Exception:
            return None

    if tipo_visita == 'externa':
        try:
            from visitaExterna.models import VisitaExterna

            visita = VisitaExterna.objects.filter(
                id=visita_id,
                estado__in=ESTADOS_VISITA_CONFIRMADA,
                fecha_visita=hoy,
            ).first()

            if not visita:
                return None

            return {
                'tipo': 'externa',
                'tipo_label': 'Externa',
                'visita_id': visita.id,
                'nombre': visita.nombre,
                'responsable': visita.nombre_responsable,
                'horario': _formatear_horario(visita.hora_inicio, visita.hora_fin),
                'asistentes_aprobados': visita.asistentes.filter(estado='documentos_aprobados').count(),
                'url_porteria': reverse('control_acceso_mina:porteria_visita', args=['externa', visita.id]),
            }
        except Exception:
            return None

    return None


def _buscar_asistente_en_visita(documento, tipo_visita, visita_id, qr_info=None):
    qr_info = qr_info or {}

    if qr_info.get('tipo') and qr_info.get('visita_id'):
        if qr_info['tipo'] != tipo_visita or qr_info['visita_id'] != visita_id:
            return None, 'El QR escaneado no corresponde a la visita seleccionada.'

    if tipo_visita == 'interna':
        try:
            from visitaInterna.models import AsistenteVisitaInterna, VisitaInterna

            visita = VisitaInterna.objects.filter(
                id=visita_id,
                estado__in=ESTADOS_VISITA_CONFIRMADA,
                fecha_visita=timezone.localdate(),
            ).first()
            if visita and str(visita.documento_responsable).strip() == str(documento).strip():
                return {
                    'nombre_completo': visita.responsable,
                    'categoria': 'Instructor Interno',
                }, None

            asistente = AsistenteVisitaInterna.objects.filter(
                numero_documento=documento,
                estado='documentos_aprobados',
                visita_id=visita_id,
                visita__estado__in=ESTADOS_VISITA_CONFIRMADA,
                visita__fecha_visita=timezone.localdate(),
            ).first()

            if not asistente:
                return None, None

            return {
                'nombre_completo': asistente.nombre_completo,
                'categoria': 'Visitante Interno',
            }, None
        except Exception:
            return None, 'No se pudo validar el asistente interno para esta visita.'

    if tipo_visita == 'externa':
        try:
            from visitaExterna.models import AsistenteVisitaExterna, VisitaExterna

            visita = VisitaExterna.objects.filter(
                id=visita_id,
                estado__in=ESTADOS_VISITA_CONFIRMADA,
                fecha_visita=timezone.localdate(),
            ).first()
            if visita and str(visita.documento_responsable).strip() == str(documento).strip():
                return {
                    'nombre_completo': visita.nombre_responsable,
                    'categoria': 'Instructor Externo',
                }, None

            asistente = AsistenteVisitaExterna.objects.filter(
                numero_documento=documento,
                estado='documentos_aprobados',
                visita_id=visita_id,
                visita__estado__in=ESTADOS_VISITA_CONFIRMADA,
                visita__fecha_visita=timezone.localdate(),
            ).first()

            if not asistente:
                return None, None

            return {
                'nombre_completo': asistente.nombre_completo,
                'categoria': 'Visitante Externo',
            }, None
        except Exception:
            return None, 'No se pudo validar el asistente externo para esta visita.'

    return None, 'Tipo de visita no soportado.'


def _obtener_asistentes_visita_aprobados(tipo_visita, visita_id):
    asistentes = []

    if tipo_visita == 'interna':
        try:
            from visitaInterna.models import AsistenteVisitaInterna, VisitaInterna

            visita = VisitaInterna.objects.filter(id=visita_id).first()
            if visita and visita.documento_responsable:
                asistentes.append({
                    'documento': visita.documento_responsable,
                    'nombre_completo': visita.responsable,
                })

            qs = AsistenteVisitaInterna.objects.filter(
                visita_id=visita_id,
                estado='documentos_aprobados',
            ).order_by('nombre_completo')

            for a in qs:
                asistentes.append({
                    'documento': a.numero_documento,
                    'nombre_completo': a.nombre_completo,
                })
        except Exception:
            return []

    if tipo_visita == 'externa':
        try:
            from visitaExterna.models import AsistenteVisitaExterna, VisitaExterna

            visita = VisitaExterna.objects.filter(id=visita_id).first()
            if visita and visita.documento_responsable:
                asistentes.append({
                    'documento': visita.documento_responsable,
                    'nombre_completo': visita.nombre_responsable,
                })

            qs = AsistenteVisitaExterna.objects.filter(
                visita_id=visita_id,
                estado='documentos_aprobados',
            ).order_by('nombre_completo')

            for a in qs:
                asistentes.append({
                    'documento': a.numero_documento,
                    'nombre_completo': a.nombre_completo,
                })
        except Exception:
            return []

    return asistentes


def _obtener_registros_visita_hoy(tipo_visita, visita_id, limit=50):
    hoy = timezone.localdate()
    registros = RegistroAccesoMina.objects.filter(
        fecha_hora__date=hoy,
        visita_tipo=tipo_visita,
        visita_id=visita_id,
    ).order_by('-fecha_hora')[:limit]

    return [
        {
            'documento': r.documento,
            'nombre_completo': r.nombre_completo,
            'categoria': r.categoria,
            'tipo': r.tipo,
            'fecha_hora': timezone.localtime(r.fecha_hora).strftime('%H:%M:%S'),
        }
        for r in registros
    ]


def _obtener_estado_actual_visita(tipo_visita, visita_id):
    """
    Retorna dos listas para la visita:
    - dentro: personas cuyo último movimiento es ENTRADA
    - fuera: personas cuyo último movimiento es SALIDA
    """
    ultimos_ids = RegistroAccesoMina.objects.filter(
        documento=OuterRef('documento'),
        visita_tipo=tipo_visita,
        visita_id=visita_id,
    ).order_by('-fecha_hora', '-id').values('id')[:1]

    ultimos_registros = RegistroAccesoMina.objects.filter(
        visita_tipo=tipo_visita,
        visita_id=visita_id,
        id=Subquery(ultimos_ids),
    ).order_by('-fecha_hora')

    dentro = []
    fuera = []

    for r in ultimos_registros:
        item = {
            'documento': r.documento,
            'nombre_completo': r.nombre_completo,
            'categoria': r.categoria,
            'hora': timezone.localtime(r.fecha_hora).strftime('%H:%M:%S'),
        }

        if r.tipo == 'ENTRADA':
            dentro.append(item)
        else:
            fuera.append(item)

    return {
        'dentro': dentro,
        'fuera': fuera,
    }


def _obtener_visitas_hoy_data():
    hoy = timezone.localdate()
    visitas = []
    total_internas = 0
    total_externas = 0

    try:
        from visitaInterna.models import VisitaInterna

        internas = VisitaInterna.objects.filter(
            estado__in=ESTADOS_VISITA_CONFIRMADA,
            fecha_visita=hoy,
        ).order_by('hora_inicio', 'id')

        for visita in internas:
            total_internas += 1
            visitas.append({
                'tipo': 'interna',
                'tipo_label': 'Interna',
                'visita_id': visita.id,
                'nombre': visita.nombre_programa,
                'responsable': visita.responsable,
                'horario': _formatear_horario(visita.hora_inicio, visita.hora_fin),
                'asistentes_aprobados': visita.asistentes.filter(estado='documentos_aprobados').count(),
                'url_porteria': reverse('control_acceso_mina:porteria_visita', args=['interna', visita.id]),
            })
    except Exception:
        pass

    try:
        from visitaExterna.models import VisitaExterna

        externas = VisitaExterna.objects.filter(
            estado__in=ESTADOS_VISITA_CONFIRMADA,
            fecha_visita=hoy,
        ).order_by('hora_inicio', 'id')

        for visita in externas:
            total_externas += 1
            visitas.append({
                'tipo': 'externa',
                'tipo_label': 'Externa',
                'visita_id': visita.id,
                'nombre': visita.nombre,
                'responsable': visita.nombre_responsable,
                'horario': _formatear_horario(visita.hora_inicio, visita.hora_fin),
                'asistentes_aprobados': visita.asistentes.filter(estado='documentos_aprobados').count(),
                'url_porteria': reverse('control_acceso_mina:porteria_visita', args=['externa', visita.id]),
            })
    except Exception:
        pass

    return {
        'visitas': visitas,
        'totales': {
            'internas': total_internas,
            'externas': total_externas,
            'total': total_internas + total_externas,
        }
    }


def _contar_personas_en_mina():
    """
    Conteo global de personas dentro, independiente de visita.
    """
    ultimos = RegistroAccesoMina.objects.filter(
        documento=OuterRef('documento')
    ).order_by('-fecha_hora').values('tipo')[:1]

    return RegistroAccesoMina.objects.values('documento').annotate(
        ultimo_tipo=Subquery(ultimos)
    ).filter(
        ultimo_tipo='ENTRADA'
    ).count()


def _contar_personas_en_visita_mina(tipo_visita, visita_id):
    """
    Conteo de personas dentro para una visita puntual.
    """
    ultimos = RegistroAccesoMina.objects.filter(
        documento=OuterRef('documento'),
        visita_tipo=tipo_visita,
        visita_id=visita_id,
    ).order_by('-fecha_hora').values('tipo')[:1]

    return RegistroAccesoMina.objects.filter(
        visita_tipo=tipo_visita,
        visita_id=visita_id,
    ).values('documento').annotate(
        ultimo_tipo=Subquery(ultimos)
    ).filter(
        ultimo_tipo='ENTRADA'
    ).count()
