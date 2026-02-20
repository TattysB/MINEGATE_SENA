#!/usr/bin/env python
"""
Script de Prueba para Sistema de Recuperación de Contraseña
Uso: python test_password_reset.py
"""

import os
import django
import sys
from pathlib import Path

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MINEGATE_SENA.settings')
sys.path.insert(0, str(Path(__file__).parent / 'MINEGATE_SENA'))

django.setup()

from django.test import Client, RequestFactory
from django.urls import reverse
from panel_visitante.models import RegistroVisitante
from panel_visitante.forms import PasswordResetRequestForm, PasswordResetConfirmForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, urlsafe_base64_encode

# Colores para output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
END = '\033[0m'

def print_test(name):
    print(f"\n{BLUE}{'='*60}{END}")
    print(f"{BLUE}PRUEBA: {name}{END}")
    print(f"{BLUE}{'='*60}{END}")

def print_success(msg):
    print(f"{GREEN}✓ {msg}{END}")

def print_error(msg):
    print(f"{RED}✗ {msg}{END}")

def print_info(msg):
    print(f"{YELLOW}ℹ {msg}{END}")

def test_model():
    """Prueba 1: Crear usuario de prueba"""
    print_test("1. Crear y Validar Modelo RegistroVisitante")
    
    try:
        # Limpiar usuario previo si existe
        RegistroVisitante.objects.filter(correo='test@example.com').delete()
        
        # Crear usuario
        visitante = RegistroVisitante.objects.create(
            correo='test@example.com',
            documento='12345678'
        )
        visitante.set_password('SecurePass123!')
        visitante.save()
        
        print_success(f"Visitante creado: {visitante.correo} (Doc: {visitante.documento})")
        
        # Validar contraseña
        if visitante.check_password('SecurePass123!'):
            print_success("Validación de contraseña correcta")
        else:
            print_error("Validación de contraseña fallida")
            return False
        
        # Validar contraseña incorrecta
        if not visitante.check_password('WrongPassword'):
            print_success("Rechazo de contraseña incorrecta funcionando")
        else:
            print_error("No rechaza contraseña incorrecta")
            return False
        
        return visitante
    
    except Exception as e:
        print_error(f"Error creando modelo: {str(e)}")
        return None

def test_forms():
    """Prueba 2: Validar formularios"""
    print_test("2. Validar Formularios")
    
    # Test PasswordResetRequestForm
    form_data = {'email': 'test@example.com'}
    form = PasswordResetRequestForm(data=form_data)
    
    if form.is_valid():
        print_success("PasswordResetRequestForm válido")
    else:
        print_error(f"PasswordResetRequestForm inválido: {form.errors}")
        return False
    
    # Test PasswordResetConfirmForm - Contraseña válida
    form_data = {
        'password1': 'SecurePass123!',
        'password2': 'SecurePass123!'
    }
    form = PasswordResetConfirmForm(data=form_data)
    
    if form.is_valid():
        print_success("PasswordResetConfirmForm válido con contraseña fuerte")
    else:
        print_error(f"PasswordResetConfirmForm inválido: {form.errors}")
        return False
    
    # Test PasswordResetConfirmForm - Contraseña débil
    form_data = {
        'password1': 'weak',
        'password2': 'weak'
    }
    form = PasswordResetConfirmForm(data=form_data)
    
    if not form.is_valid():
        print_success("Rechazo de contraseña débil funcionando")
    else:
        print_error("No rechaza contraseña débil")
        return False
    
    # Test mismatch de contraseñas
    form_data = {
        'password1': 'SecurePass123!',
        'password2': 'DifferentPass456@'
    }
    form = PasswordResetConfirmForm(data=form_data)
    
    if not form.is_valid():
        print_success("Rechazo de contraseñas no coincidentes funcionando")
    else:
        print_error("No rechaza contraseñas no coincidentes")
        return False
    
    return True

def test_tokens(visitante):
    """Prueba 3: Generación y validación de tokens"""
    print_test("3. Generación y Validación de Tokens")
    
    try:
        # Generar token
        token = default_token_generator.make_token(visitante)
        print_success(f"Token generado: {token[:20]}...")
        
        # Generar UID
        uid = urlsafe_base64_encode(force_bytes(visitante.pk))
        print_success(f"UID generado: {uid}")
        
        # Validar token
        if default_token_generator.check_token(visitante, token):
            print_success("Validación de token exitosa")
        else:
            print_error("Validación de token fallida")
            return False
        
        # Token inválido
        fake_token = "invalid_token_12345"
        if not default_token_generator.check_token(visitante, fake_token):
            print_success("Rechazo de token inválido funcionando")
        else:
            print_error("No rechaza token inválido")
            return False
        
        return True
    
    except Exception as e:
        print_error(f"Error en tokens: {str(e)}")
        return False

def test_urls():
    """Prueba 4: Verificar URLs"""
    print_test("4. Verificar URL Patterns")
    
    try:
        urls = [
            ('panel_visitante:restablecer_contraseña', 'GET /visitante/restablecer-contraseña/'),
            ('panel_visitante:correo_enviado', 'GET /visitante/restablecer-contraseña/correo-enviado/'),
            ('panel_visitante:contraseña_actualizada', 'GET /visitante/restablecer-contraseña/completado/'),
        ]
        
        for url_name, description in urls:
            try:
                url = reverse(url_name)
                print_success(f"{description} = {url}")
            except Exception as e:
                print_error(f"URL {url_name} no encontrada: {str(e)}")
                return False
        
        # URL con parámetros
        from django.utils.encoding import urlsafe_base64_encode, force_bytes
        uid = urlsafe_base64_encode(force_bytes(1))
        token = "test-token"
        try:
            url = reverse('panel_visitante:restablecer_contraseña_confirm', 
                         kwargs={'uidb64': uid, 'token': token})
            print_success(f"URL con parámetros = /visitante/restablecer-contraseña/{uid}/{token}/")
        except Exception as e:
            print_error(f"URL con parámetros fallida: {str(e)}")
            return False
        
        return True
    
    except Exception as e:
        print_error(f"Error verificando URLs: {str(e)}")
        return False

def test_client_requests(visitante):
    """Prueba 5: Prueba de requests con cliente Django"""
    print_test("5. Prueba de Requests HTTP")
    
    client = Client()
    
    # GET formulario de solicitud
    try:
        response = client.get(reverse('panel_visitante:restablecer_contraseña'))
        if response.status_code == 200:
            print_success(f"GET /restablecer-contraseña/ = 200 OK")
        else:
            print_error(f"GET /restablecer-contraseña/ = {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error GET: {str(e)}")
        return False
    
    # POST con email válido
    try:
        response = client.post(
            reverse('panel_visitante:restablecer_contraseña'),
            {'email': visitante.correo},
            follow=True
        )
        if response.status_code == 200:
            print_success(f"POST /restablecer-contraseña/ con email válido = 200 OK")
            # Debe redirigir a correo_enviado
            if 'correo-enviado' in str(response.url):
                print_success("Redirección a /correo-enviado/ correcta")
            else:
                print_info(f"URL destino: {response.url}")
        else:
            print_error(f"POST /restablecer-contraseña/ = {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error POST: {str(e)}")
        return False
    
    return True

def test_templates():
    """Prueba 6: Verificar templates existen"""
    print_test("6. Verificar Existencia de Templates")
    
    templates_path = Path(__file__).parent / 'MINEGATE_SENA' / 'panel_visitante' / 'templates'
    required_templates = [
        'solicitar_recuperacion_visitante.html',
        'correo_enviado_visitante.html',
        'restablecer_contraseña_confirm_visitante.html',
        'contraseña_actualizada_visitante.html',
        'email_restablecer_visitante.html',
    ]
    
    for template in required_templates:
        template_path = templates_path / template
        if template_path.exists():
            size = template_path.stat().st_size
            print_success(f"{template} ({size} bytes)")
        else:
            print_error(f"{template} no encontrado")
            return False
    
    return True

def main():
    """Ejecutar todas las pruebas"""
    print(f"\n{BLUE}{'#'*60}{END}")
    print(f"{BLUE}# PRUEBAS DEL SISTEMA DE RECUPERACIÓN DE CONTRASEÑA{END}")
    print(f"{BLUE}{'#'*60}{END}")
    
    results = {}
    
    # Prueba 1
    visitante = test_model()
    results['Modelo'] = visitante is not None
    
    if visitante:
        # Prueba 2
        results['Formularios'] = test_forms()
        
        # Prueba 3
        results['Tokens'] = test_tokens(visitante)
        
        # Prueba 5
        results['Requests'] = test_client_requests(visitante)
    
    # Prueba 4
    results['URLs'] = test_urls()
    
    # Prueba 6
    results['Templates'] = test_templates()
    
    # Resumen
    print(f"\n{BLUE}{'='*60}{END}")
    print(f"{BLUE}RESUMEN DE PRUEBAS{END}")
    print(f"{BLUE}{'='*60}{END}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{GREEN}✓ PASADO{END}" if result else f"{RED}✗ FALLIDO{END}"
        print(f"{test_name:.<40} {status}")
    
    print(f"\n{YELLOW}Total: {passed}/{total} pruebas pasadas{END}")
    
    if passed == total:
        print(f"\n{GREEN}{'#'*60}{END}")
        print(f"{GREEN}¡TODAS LAS PRUEBAS PASARON! ✓{END}")
        print(f"{GREEN}El sistema de recuperación de contraseña está listo.{END}")
        print(f"{GREEN}{'#'*60}{END}")
        return 0
    else:
        print(f"\n{RED}{'#'*60}{END}")
        print(f"{RED}ALGUNAS PRUEBAS FALLARON{END}")
        print(f"{RED}{'#'*60}{END}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
