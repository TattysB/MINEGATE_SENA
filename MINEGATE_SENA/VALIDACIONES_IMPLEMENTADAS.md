# 📋 VALIDACIONES EXHAUSTIVAS IMPLEMENTADAS

## ✅ Validaciones Agregadas - Panel Instructor Interno y Externo

### 1. **Validadores Base (Ambos módulos)**

```python
validar_correo_formato(correo)
├─ Regex: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$
└─ Valida formato de correo estándar

validar_documento_numero(numero_documento)
├─ Solo dígitos (0-9)
├─ Mínimo: 5 dígitos
├─ Máximo: 15 dígitos
└─ Sin puntos, guiones ni caracteres especiales

validar_cantidad_minima(cantidad)
├─ Solo números enteros
├─ Rango: 1 a 1000
└─ Rechaza 0, negativos y valores > 1000

validar_nombre_alfabetico(nombre, campo)
├─ Solo letras + acentos (á, é, í, ó, ú, ñ, ü)
├─ Permite espacios y apóstrofos
├─ Mínimo: 2 caracteres
├─ Máximo: 100 caracteres
├─ Rechaza números y caracteres especiales
└─ No puede ser solo espacios

validar_telefono(telefono)
├─ Formato: +[0-9] con espacios/guiones
├─ Dígitos: 7 a 15
├─ Opcional (puede estar vacío)
└─ Válido: +57 300 123 4567 ó 3001234567

validar_observaciones(observaciones)
├─ Máximo: 500 caracteres
├─ Rechaza caracteres de control
└─ Opcional (puede estar vacía)
```

---

## 📋 VisitaInternaInstructorForm

### Campos y Validaciones:

| Campo | Validación | Ejemplo Válido | Ejemplo Inválido |
|-------|-----------|-----------------|-----------------|
| **nombre_programa** | 3-200 caracteres, texto | "Técnico en Sistemas" | "" ó 123 |
| **numero_ficha** | Solo números, 1-10 dígitos | 12345 | abc ó 12345678901 |
| **responsable** | Solo letras, 2-100 chars | "Juan García" | "Juan123" |
| **documento_responsable** | Solo números, 5-15 dígitos | 1023456789 | "102-345-6789" |
| **correo_responsable** | Correo válido, dominio real | "juan@sena.gov.co" | "juan@.com" |
| **telefono_responsable** | 7-15 dígitos, con + opcional | "+57 3001234567" | "123" ó "abc" |
| **cantidad_aprendices** | Número 1-1000 | 25 | 0 ó 2000 |
| **observaciones** | Max 500 chars, sin control | "Observación válida" | (512 caracteres) |

---

## 📋 VisitaExternaInstructorForm

### Campos y Validaciones:

| Campo | Validación | Ejemplo Válido | Ejemplo Inválido |
|-------|-----------|-----------------|-----------------|
| **nombre** | 3-200 caracteres | "Institución Educativa" | "" ó "12" |
| **nombre_responsable** | Solo letras, 2-100 chars | "María López" | "María123" |
| **documento_responsable** | Solo números, 5-15 dígitos | 987654321 | "987-654-321" |
| **correo_responsable** | Correo válido | "contacto@empresa.com" | "correo@" |
| **telefono_responsable** | 7-15 dígitos | "+57 3009876543" | "123" |
| **cantidad_visitantes** | Número 1-1000 | 50 | -5 ó 5000 |
| **observacion** | Max 500 chars | "Nota: llegada temprana" | (501+ caracteres) |

---

## 📋 AprendizForm (Interno) / VisitanteForm (Externo)

### Campos Críticos:

```
✓ nombre
  └─ Solo letras, 2-100 caracteres
  └─ Ejemplo: "Juan" NO "Juan123"

✓ apellido
  └─ Solo letras, 2-100 caracteres
  └─ Ejemplo: "Pérez" NO "Perez2024"

✓ numero_documento (CRÍTICO)
  └─ Solo números, 5-15 dígitos
  └─ Ejemplo: 1234567890 NO 1234-567-890
  └─ Validación de largo según tipo:
     ├─ CC (Cédula): mín 5 dígitos
     ├─ CE (Extranjería): mín 7 dígitos
     ├─ PA (Pasaporte): mín 6 dígitos
     └─ TI (Tarjeta): mín 7 dígitos

✓ correo (CRÍTICO PARA QR)
  └─ Correo válido con dominio real
  └─ Máximo 150 caracteres
  └─ Ejemplo: usuario@empresa.com
  └─ NO: usuario@localhost ó usuario@.com
  └─ Obligatorio: Sin correo = SIN QR

✓ telefono
  └─ 7-15 dígitos con +, espacios
  └─ Ejemplo: +57 3001234567
  └─ Opcional (puede ser vacío)
```

---

## 🔒 Atributos HTML de Seguridad

Se agregaron atributos `maxlength`, `inputmode` e `inputtype` en widgets:

```html
<!-- Documentos: solo números -->
<input inputmode="numeric" maxlength="15" placeholder="Solo números">

<!-- Teléfonos: solo números -->
<input inputmode="tel" maxlength="20" placeholder="+57 3001234567">

<!-- Correos: validación email -->
<input type="email" maxlength="150" placeholder="usuario@ejemplo.com">

<!-- Cantidades: rango -->
<input type="number" min="1" max="1000">
```

---

## 📊 Resumen de Tipos de Validación

### Por Tipo de Campo:

**ALFABÉTICO (Solo Letras)**:
- Nombres, Apellidos
- Responsables
- Regex: `^[a-záéíóúñüA-ZÁÉÍÓÚÑÜ\s'-]+$`

**NUMÉRICO (Solo Números)**:
- Documentos (5-15 dígitos)
- Fichas (1-10 dígitos)
- Cantidades (1-1000)
- Teléfonos (7-15 dígitos, con + opcional)

**EMAIL**:
- Correos (formato + dominio válido)
- Regex: `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`

**TEXTO**:
- Programas, Instituciones (3-200 caracteres)
- Observaciones (máximo 500 caracteres)
- Rechaza caracteres de control

---

## 🚨 Validaciones Críticas

### ⭐ Para Envío de QR:

1. **Correo del Asistente**
   - ✓ Formato válido
   - ✓ Dominio con extensión
   - ✓ No puede ser vacío
   - ✓ Máximo 150 caracteres

2. **Documento del Asistente**
   - ✓ Solo números
   - ✓ 5-15 dígitos
   - ✓ Sin puntos ni guiones

3. **Nombre Completo**
   - ✓ Solo letras
   - ✓ 2-100 caracteres
   - ✓ Sin números

---

## 📝 Ejemplos de Validación

### ✅ VÁLIDOS:
```
Correo: usuario@empresa.com.co
Documento: 1234567890 (10 dígitos)
Teléfono: +57 3001234567
Nombre: Juan Carlos García
Cantidad: 25
```

### ❌ INVÁLIDOS:
```
Correo: usuario@.com (dominio incompleto)
Documento: 1234-567-890 (guiones)
Teléfono: 123 (muy corto)
Nombre: Juan123 (contiene números)
Cantidad: 0 (debe ser >= 1)
```

---

## 🔄 Flujo de Validación

```
Usuario llena formulario
        ↓
Cliente valida (HTML5)
        ↓
Django clean_* methods validan
        ↓
¿Todos válidos?
├─ SÍ → Guardar en BD
└─ NO → Mostrar errores específicos
        ↓
Admin aprueba documentos
        ↓
Signal dispara GeneradorQRPDF
        ↓
ValidarCorreoParaQR()
        ↓
✉️ ENVIAR QR por email
```

---

## 🎯 Uso en Vistas

```python
# Uso básico en views.py
if form.is_valid():
    # form.cleaned_data tiene datos validados
    asistente = form.save(commit=False)
    asistente.visita = visita
    asistente.save()
else:
    # Mostrar errores automáticamente en template
    return render(request, 'form.html', {'form': form})
```

---

## ✅ Checklist de Validaciones Implementadas

### Instructor Interno:
- [x] Nombre programa (3-200 chars)
- [x] Número ficha (solo números)
- [x] Responsable (solo letras)
- [x] Documento (5-15 dígitos)
- [x] Correo responsable (formato + dominio)
- [x] Teléfono (7-15 dígitos)
- [x] Cantidad aprendices (1-1000)
- [x] Observaciones (max 500 chars)
- [x] Nombre aprendiz (solo letras)
- [x] Correo aprendiz (CRÍTICO para QR)
- [x] Documento aprendiz (solo números)
- [x] Teléfono aprendiz

### Instructor Externo:
- [x] Nombre institución (3-200 chars)
- [x] Nombre responsable (solo letras)
- [x] Documento responsable (5-15 dígitos)
- [x] Correo responsable (formato + dominio)
- [x] Teléfono responsable (7-15 dígitos)
- [x] Cantidad visitantes (1-1000)
- [x] Observaciones (max 500 chars)

---

## 📦 Archivos Modificados

```
✏️  panel_instructor_interno/forms.py
✏️  panel_instructor_externo/forms.py
✨  VALIDACIONES_IMPLEMENTADAS.md (este archivo)
```

---

## 🔗 Referencia Rápida de Validadores

```python
# Importar en views si necesitas usar directamente
from panel_instructor_interno.forms import (
    validar_correo_formato,
    validar_documento_numero,
    validar_cantidad_minima,
    validar_nombre_alfabetico,
    validar_telefono,
    validar_observaciones,
)
```
