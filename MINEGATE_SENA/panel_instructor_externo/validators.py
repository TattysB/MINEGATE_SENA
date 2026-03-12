"""
Validadores personalizados para el módulo de instructor externo.
Proporciona funciones de validación reutilizables para correos, documentos y datos.
"""

import re
from django.core.exceptions import ValidationError
from visitaExterna.models import AsistenteVisitaExterna


def validar_correo_para_qr(correo):
    """
    Valida que un correo sea válido para el envío de QR.
    - Verifica formato correcto
    - Verifica que el dominio tenga extensión válida
    - Detecta dominios comunes problemáticos
    
    Args:
        correo (str): El correo a validar
        
    Returns:
        dict: {'valido': bool, 'mensaje': str}
    """
    
    if not correo:
        return {
            'valido': False,
            'mensaje': 'El correo es requerido para enviar el QR.'
        }
    
    correo = correo.lower().strip()
    
    # Validar formato básico
    patron_email = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(patron_email, correo):
        return {
            'valido': False,
            'mensaje': 'El correo no tiene un formato válido.'
        }
    
    # Dividir en usuario y dominio
    partes = correo.split('@')
    if len(partes) != 2:
        return {
            'valido': False,
            'mensaje': 'El correo debe tener exactamente un símbolo @.'
        }
    
    usuario, dominio = partes
    
    # Validar longitud del usuario
    if len(usuario) < 1:
        return {
            'valido': False,
            'mensaje': 'La parte del usuario del correo no puede estar vacía.'
        }
    
    # Validar que el dominio tenga al menos una extensión
    if '.' not in dominio:
        return {
            'valido': False,
            'mensaje': 'El dominio debe incluir una extensión (ej: .com, .co, etc).'
        }
    
    # Validar extensión mínima
    extension = dominio.split('.')[-1]
    if len(extension) < 2:
        return {
            'valido': False,
            'mensaje': 'La extensión del dominio debe tener al menos 2 caracteres.'
        }
    
    # Validar que no sea un dominio dummy
    dominios_invalidos = ['local', 'test', 'ejemplo', 'example', 'localhost']
    if dominio.split('.')[0] in dominios_invalidos:
        return {
            'valido': False,
            'mensaje': f'El dominio "{dominio}" no es válido para envío de emails.'
        }
    
    return {
        'valido': True,
        'mensaje': 'Correo válido.'
    }


def validar_correos_visitantes(visita_id):
    """
    Valida que todos los visitantes de una visita externa tengan correos válidos.
    Previo a enviar los QR.
    
    Args:
        visita_id (int): ID de la visita externa
        
    Returns:
        dict: {
            'todos_validos': bool,
            'correos_invalidos': list,
            'mensajes': list
        }
    """
    
    asistentes = AsistenteVisitaExterna.objects.filter(visita_id=visita_id)
    
    resultados = {
        'todos_validos': True,
        'correos_invalidos': [],
        'mensajes': []
    }
    
    for asistente in asistentes:
        correo = asistente.correo if hasattr(asistente, 'correo') else getattr(asistente, 'email', None)
        
        if not correo:
            resultados['todos_validos'] = False
            resultados['correos_invalidos'].append({
                'asistente': str(asistente),
                'razon': 'Sin correo'
            })
            resultados['mensajes'].append(
                f'⚠️ {asistente}: No tiene correo registrado para enviar QR.'
            )
            continue
        
        validacion = validar_correo_para_qr(correo)
        if not validacion['valido']:
            resultados['todos_validos'] = False
            resultados['correos_invalidos'].append({
                'asistente': str(asistente),
                'correo': correo,
                'razon': validacion['mensaje']
            })
            resultados['mensajes'].append(
                f'⚠️ {asistente} ({correo}): {validacion["mensaje"]}'
            )
    
    return resultados


def validar_documento_para_visitante(numero_documento, tipo_documento='CC'):
    """
    Valida que el número de documento sea válido para un visitante externo.
    
    Args:
        numero_documento (str): Número de documento
        tipo_documento (str): Tipo de documento (CC, CE, PA, etc)
        
    Returns:
        dict: {'valido': bool, 'mensaje': str}
    """
    
    if not numero_documento:
        return {
            'valido': False,
            'mensaje': 'El número de documento es obligatorio.'
        }
    
    numero_documento = str(numero_documento).strip()
    
    # Solo permite números, guiones y puntos
    if not re.match(r'^[0-9\-\.]*$', numero_documento):
        return {
            'valido': False,
            'mensaje': 'El documento solo debe contener números, guiones o puntos.'
        }
    
    # Extrae solo los números para validar longitud
    numeros = re.sub(r'[^\d]', '', numero_documento)
    
    # Validación mínima según tipo de documento
    tipos_validacion = {
        'CC': (5, 'Cédula de Ciudadanía'),  # Mínimo 5 dígitos
        'CE': (7, 'Cédula de Extranjería'),  # Mínimo 7 dígitos
        'PA': (6, 'Pasaporte'),  # Mínimo 6 dígitos
        'TI': (7, 'Tarjeta de Identidad'),  # Mínimo 7 dígitos
        'RC': (6, 'Registro Civil'),  # Mínimo 6 dígitos
    }
    
    if tipo_documento in tipos_validacion:
        minimo, nombre = tipos_validacion[tipo_documento]
        if len(numeros) < minimo:
            return {
                'valido': False,
                'mensaje': f'{nombre} debe tener al menos {minimo} dígitos.'
            }
    elif len(numeros) < 5:
        return {
            'valido': False,
            'mensaje': 'El documento debe tener al menos 5 dígitos.'
        }
    
    return {
        'valido': True,
        'mensaje': 'Documento válido.'
    }


def validar_datos_visitante(visitante_dict):
    """
    Valida todos los datos necesarios de un visitante antes de crear el registro.
    
    Args:
        visitante_dict (dict): Diccionario con datos del visitante
        
    Returns:
        dict: {
            'valido': bool,
            'errores': list,
            'advertencias': list
        }
    """
    
    resultados = {
        'valido': True,
        'errores': [],
        'advertencias': []
    }
    
    # Validaciones obligatorias
    campos_obligatorios = ['correo', 'numero_documento']
    for campo in campos_obligatorios:
        if campo not in visitante_dict or not visitante_dict[campo]:
            resultados['valido'] = False
            resultados['errores'].append(f'Falta el campo obligatorio: {campo}')
    
    # Validar correo si está presente
    if 'correo' in visitante_dict and visitante_dict['correo']:
        validacion_correo = validar_correo_para_qr(visitante_dict['correo'])
        if not validacion_correo['valido']:
            resultados['valido'] = False
            resultados['errores'].append(f"Correo inválido: {validacion_correo['mensaje']}")
    
    # Validar documento si está presente
    if 'numero_documento' in visitante_dict and visitante_dict['numero_documento']:
        tipo = visitante_dict.get('tipo_documento', 'CC')
        validacion_doc = validar_documento_para_visitante(
            visitante_dict['numero_documento'],
            tipo
        )
        if not validacion_doc['valido']:
            resultados['valido'] = False
            resultados['errores'].append(f"Documento inválido: {validacion_doc['mensaje']}")
    
    # Advertencias
    if 'nombre' in visitante_dict and visitante_dict['nombre']:
        if len(str(visitante_dict['nombre']).strip()) < 2:
            resultados['advertencias'].append('El nombre parece muy corto.')
    
    return resultados
