# Sistema de Recuperación de Contraseña - MINEGATE

## ✅ Implementación Completada

### 1. **Estructura de Backend**

#### Modelos (`panel_visitante/models.py`)
- ✅ `RegistroVisitante` - Modelo limpio sin campos de token personalizado
- ✅ Métodos `set_password()` y `check_password()` usando Django

#### Formularios (`panel_visitante/forms.py`)
- ✅ `PasswordResetRequestForm` - Solicita correo del usuario
- ✅ `PasswordResetConfirmForm` - Valida nueva contraseña con requisitos fuertes:
  - Mínimo 8 caracteres
  - Al menos una mayúscula, minúscula, número y carácter especial
  - Confirmación de contraseña

#### Vistas (`panel_visitante/views.py`)
1. **`restablecer_contraseña()`** - Solicita email y envía enlace de recuperación
2. **`correo_enviado_view()`** - Página de confirmación post-envío
3. **`restablecer_contraseña_confirm(uidb64, token)`** - Valida token y permite cambio de contraseña
4. **`contraseña_actualizada_view()`** - Página de éxito

#### URLs (`panel_visitante/urls.py`)
```
GET  /visitante/restablecer-contraseña/                    → Formulario de solicitud
POST /visitante/restablecer-contraseña/                    → Procesa solicitud y envía email
GET  /visitante/restablecer-contraseña/correo-enviado/     → Página de confirmación
GET  /visitante/restablecer-contraseña/<uidb64>/<token>/   → Formulario de nueva contraseña
POST /visitante/restablecer-contraseña/<uidb64>/<token>/   → Procesa nueva contraseña
GET  /visitante/restablecer-contraseña/completado/         → Página de éxito
```

### 2. **Plantillas HTML Creadas**

| Template | Propósito | Ubicación |
|----------|-----------|-----------|
| `solicitar_recuperacion_visitante.html` | Formulario para solicitar recuperación | `panel_visitante/templates/` |
| `correo_enviado_visitante.html` | Confirmación de envío de correo | `panel_visitante/templates/` |
| `restablecer_contraseña_confirm_visitante.html` | Formulario de nueva contraseña | `panel_visitante/templates/` |
| `contraseña_actualizada_visitante.html` | Página de éxito após cambio | `panel_visitante/templates/` |
| `email_restablecer_visitante.html` | Email HTML con instrucciones | `panel_visitante/templates/` |

**Estilos**: Todos los templates incluyen:
- Diseño responsivo
- Gradientes y animaciones profesionales
- Iconos Font Awesome
- Validación visual en formularios
- Mensajes de error claros

### 3. **Flujo de Seguridad**

#### Token Generation (Creación de Token)
```python
token = default_token_generator.make_token(visitante)  # HMAC-based, single-use
uid = urlsafe_base64_encode(force_bytes(visitante.pk))  # Safe URL encoding
reset_url = /visitante/restablecer-contraseña/{uid}/{token}/
```

#### Token Validation (Validación)
```python
visitante = RegistroVisitante.objects.get(pk=uid)
if default_token_generator.check_token(visitante, token):
    # Token válido - permitir cambio de contraseña
```

#### Características de Seguridad
- ✅ Tokens generados con HMAC (más seguro que UUID)
- ✅ Base64 encoding para UID en URLs
- ✅ Tokens de un solo uso
- ✅ Expiración automática (24 horas por defecto)
- ✅ CSRF protection en formularios
- ✅ Validación de contraseña fuerte
- ✅ Mensajes genéricos por seguridad (no revela si email existe)

### 4. **Email Configuration**

**Desarrollo** (settings.py - línea 158):
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# Los correos se muestran en la consola del servidor
```

**Producción** (settings.py - líneas 179-185):
```python
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "minegate123@gmail.com"
EMAIL_HOST_PASSWORD = "zcvq ifep jxtz kyxy"
DEFAULT_FROM_EMAIL = "MineGate <minegate123@gmail.com>"
```

### 5. **Flujo Completo de Usuario**

```
1. Usuario accede a login
   ↓
2. Hace clic en "¿Olvidaste tu contraseña?"
   ↓
3. Llena formulario con su correo
   ↓
4. Recibe email con botón "RESTABLECER CONTRASEÑA"
   ↓
5. Hace clic en enlace (válido por 24 horas)
   ↓
6. Ingresa nueva contraseña fuerte
   ↓
7. Confirma contraseña
   ↓
8. Ve página de éxito "Contraseña Actualizada"
   ↓
9. Inicia sesión con nuevas credenciales
```

## 🔍 Cómo Probar el Sistema

### Test Manual en Desarrollo

1. **Inicia el servidor Django**:
   ```bash
   python manage.py runserver
   ```

2. **Accede a la página de login**:
   ```
   http://localhost:8000/visitante/login/
   ```

3. **Haz clic en "¿Olvidaste tu contraseña?"**:
   - Te llevará a: `/visitante/restablecer-contraseña/`

4. **Ingresa un correo registrado**:
   - Si el correo existe, recibirás email en consola
   - El token aparecerá en la terminal del servidor
   - Copia el enlace completo

5. **Accede al enlace de reset**:
   - Verás el formulario de nueva contraseña
   - Ingresa contraseña que cumpla requisitos

6. **Verifica el éxito**:
   - Serás redirigido a página de éxito
   - Podrás iniciar sesión con nuevas credenciales

### Test Automatizado (Opcional)

Para crear un test automatizado, use:
```python
# panel_visitante/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from .models import RegistroVisitante

class PasswordResetTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.visitante = RegistroVisitante.objects.create_user(
            correo='test@example.com',
            documento='12345',
            password='TestPass123!'
        )
    
    def test_password_reset_request(self):
        response = self.client.post(reverse('panel_visitante:restablecer_contraseña'), {
            'email': 'test@example.com'
        })
        self.assertEqual(response.status_code, 302)  # Redirect
```

## ⚙️ Configuración para Producción

### Paso 1: Configurar Email SMTP

En `settings.py`, reemplaza:
```python
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"  # Tu servidor SMTP
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "tu-correo@gmail.com"
EMAIL_HOST_PASSWORD = "tu-contraseña-app"  # No la contraseña real de Gmail
DEFAULT_FROM_EMAIL = "MineGate <tu-correo@gmail.com>"
```

### Paso 2: Usar Variables de Entorno

Para mayor seguridad:
```python
import os

EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
```

### Paso 3: Crear archivo `.env`

```
EMAIL_HOST_USER=minegate123@gmail.com
EMAIL_HOST_PASSWORD=zcvq ifep jxtz kyxy
```

### Paso 4: Instalar python-decouple (opcional)

```bash
pip install python-decouple
```

```python
from decouple import config

EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
```

## 📋 Checklist de Verificación

- ✅ Modelos actualizados (sin campos de token personalizado)
- ✅ Formularios con validación de contraseña fuerte
- ✅ Vistas implementadas correctamente
- ✅ URLs mapeadas correctamente
- ✅ Todos los templates HTML creados
- ✅ Email template con HTML profesional
- ✅ Tokens usando Django standard (default_token_generator)
- ✅ Base64 encoding para UID
- ✅ Sin cambios en el link de login (ya apunta a reset)
- ✅ Configuración de email ya presente en settings.py
- ✅ Sintaxis Python validada (sin errores)
- ✅ Migraciones existentes (0001_initial.py, 0002_registrovisitante_reset_fields.py)

## 🐛 Troubleshooting

### Email no llega en desarrollo
- **Solución**: En desarrollo, los emails se muestran en la consola del servidor. Busca en la terminal.

### Token inválido o expirado
- **Razón**: Tokens expiran después de 24 horas
- **Solución**: Usar "Enviar otro correo" para generar nuevo token

### Contraseña no cumple requisitos
- **Revisar**: Debe tener mayúscula, minúscula, número y carácter especial

### Enlace en email no funciona
- **Revisar**: URL base del sitio en `ALLOWED_HOSTS` de settings.py

## 📞 Soporte

Si encuentras problemas:
1. Revisa los logs del servidor Django
2. Verifica que el modelo `RegistroVisitante` tenga datos
3. Confirma que `DEFAULT_FROM_EMAIL` está configurado
4. En producción, verifica credenciales SMTP

---

**Sistema implementado**: {{date}}
**Patrón utilizado**: Django Standard Password Reset (como en app `usuarios`)
**Seguridad**: Tokens HMAC de un solo uso, base64 encoding, CSRF protection
