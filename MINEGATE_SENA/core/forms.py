from io import BytesIO
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import (
    ContenidoPaginaInformativa,
    ElementoEncabezadoInformativo,
    ElementoGaleriaInformativa,
)


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".ogg"}
MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024
MAX_VIDEO_SIZE_BYTES = 120 * 1024 * 1024


def _extension_archivo(nombre):
    return Path(nombre or "").suffix.lower()


def _normalizar_orientacion_imagen(archivo):
    archivo.seek(0)
    with Image.open(archivo) as imagen_original:
        imagen = ImageOps.exif_transpose(imagen_original)
        extension = _extension_archivo(getattr(archivo, "name", ""))

        if extension in {".jpg", ".jpeg"}:
            formato = "JPEG"
            content_type = "image/jpeg"
        elif extension == ".png":
            formato = "PNG"
            content_type = "image/png"
        elif extension == ".webp":
            formato = "WEBP"
            content_type = "image/webp"
        else:
            formato = "JPEG"
            content_type = "image/jpeg"

        if formato == "JPEG" and imagen.mode not in ("RGB", "L"):
            imagen = imagen.convert("RGB")

        buffer = BytesIO()
        kwargs_guardado = {"quality": 90, "optimize": True} if formato == "JPEG" else {}
        imagen.save(buffer, format=formato, **kwargs_guardado)

    buffer.seek(0)
    return SimpleUploadedFile(
        name=getattr(archivo, "name", "imagen.jpg"),
        content=buffer.getvalue(),
        content_type=content_type,
    )


class ContenidoPaginaInformativaForm(forms.ModelForm):
    class Meta:
        model = ContenidoPaginaInformativa
        fields = ["titulo_galeria", "descripcion_galeria"]
        widgets = {
            "titulo_galeria": forms.TextInput(
                attrs={"class": "form-control", "autocomplete": "off"}
            ),
            "descripcion_galeria": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["titulo_galeria"].label = "Título de la sección Galería"
        self.fields["titulo_galeria"].help_text = (
            "Título que verá el visitante encima del carrusel."
        )
        self.fields["titulo_galeria"].widget.attrs.update(
            {"placeholder": "Ej: Explora Nuestras Instalaciones"}
        )

        self.fields["descripcion_galeria"].label = "Descripción de la galería"
        self.fields["descripcion_galeria"].help_text = (
            "Texto de apoyo para invitar a ver imágenes y videos."
        )
        self.fields["descripcion_galeria"].widget.attrs.update(
            {"placeholder": "Explica qué encontrará el usuario en la galería"}
        )


class ElementoEncabezadoInformativoForm(forms.ModelForm):
    class Meta:
        model = ElementoEncabezadoInformativo
        fields = ["titulo", "texto", "imagen", "orden", "activo"]
        widgets = {
            "titulo": forms.TextInput(
                attrs={"class": "form-control", "autocomplete": "off"}
            ),
            "texto": forms.Textarea(
                attrs={
                    "class": "form-control gpi-textarea-auto",
                    "rows": 2,
                    "data-max-words": 50,
                    "data-counter-id": "gpi-texto-counter",
                }
            ),
            "imagen": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
            "orden": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "style": "max-width:120px"}
            ),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["titulo"].label = "Título de la diapositiva"
        self.fields["titulo"].help_text = (
            "Opcional. Si lo dejas vacío, se mostrará solo el texto."
        )
        self.fields["titulo"].widget.attrs.update(
            {"placeholder": "Ej: Centro Minero de Morcá"}
        )

        self.fields["texto"].label = "Texto de la diapositiva"
        self.fields["texto"].help_text = (
            "Mensaje principal del encabezado (máximo 50 palabras)."
        )
        self.fields["texto"].widget.attrs.update(
            {"placeholder": "Ej: Agenda tu experiencia minera..."}
        )

        self.fields["imagen"].label = "Imagen de fondo"
        self.fields["imagen"].help_text = (
            "Sube la imagen para esta diapositiva del encabezado principal."
        )

        self.fields["orden"].label = "Orden de aparición"
        self.fields["orden"].help_text = "Número menor = aparece primero."

        self.fields["activo"].label = "Mostrar en el encabezado"
        self.fields["activo"].help_text = (
            "Si lo desmarcas, la diapositiva no se mostrará en la página pública."
        )

        if self.instance and self.instance.pk:
            self.fields["imagen"].required = False

    def clean_texto(self):
        texto = (self.cleaned_data.get("texto") or "").strip()
        if not texto:
            return texto

        palabras = [fragmento for fragmento in texto.split() if fragmento]
        if len(palabras) > 50:
            raise ValidationError("El texto de la diapositiva no puede superar 50 palabras.")
        return texto

    def clean_imagen(self):
        imagen = self.cleaned_data.get("imagen")
        if not imagen:
            return imagen

        extension = _extension_archivo(getattr(imagen, "name", ""))
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValidationError(
                "Formato de imagen no soportado. Usa JPG, PNG o WEBP."
            )

        if getattr(imagen, "size", 0) > MAX_IMAGE_SIZE_BYTES:
            raise ValidationError("La imagen no puede superar 20 MB.")

        try:
            return _normalizar_orientacion_imagen(imagen)
        except (UnidentifiedImageError, OSError):
            raise ValidationError("El archivo cargado no es una imagen válida.")


class ElementoGaleriaInformativaForm(forms.ModelForm):
    class Meta:
        model = ElementoGaleriaInformativa
        fields = ["tipo", "archivo", "titulo", "descripcion", "orden", "activo"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-control"}),
            "archivo": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*,video/*"}
            ),
            "titulo": forms.TextInput(
                attrs={"class": "form-control", "autocomplete": "off"}
            ),
            "descripcion": forms.TextInput(
                attrs={"class": "form-control", "autocomplete": "off"}
            ),
            "orden": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "style": "max-width:120px"}
            ),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].label = "Tipo de elemento"
        self.fields["tipo"].help_text = "Selecciona si vas a subir una imagen o un video."

        self.fields["archivo"].label = "Archivo (imagen o video)"
        self.fields["archivo"].help_text = "Sube el archivo que quieres mostrar en la galería."

        self.fields["titulo"].label = "Título visible"
        self.fields["titulo"].help_text = "Título corto que aparece sobre el elemento."
        self.fields["titulo"].widget.attrs.update(
            {"placeholder": "Ej: Recorrido por la mina"}
        )

        self.fields["descripcion"].label = "Descripción breve"
        self.fields["descripcion"].help_text = "Texto opcional que complementa el título."
        self.fields["descripcion"].widget.attrs.update(
            {"placeholder": "Ej: Actividades prácticas con aprendices"}
        )

        self.fields["orden"].label = "Orden de aparición"
        self.fields["orden"].help_text = "Número menor = se muestra primero en la galería."

        self.fields["activo"].label = "Mostrar en el sitio"
        self.fields["activo"].help_text = "Si lo desmarcas, no se verá en el index."

        if self.instance and self.instance.pk:
            self.fields["archivo"].required = False

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo")
        archivo_subido = cleaned_data.get("archivo")
        archivo_actual = getattr(self.instance, "archivo", None)
        archivo_referencia = archivo_subido or (
            archivo_actual if getattr(archivo_actual, "name", "") else None
        )

        if not tipo or not archivo_referencia:
            return cleaned_data

        extension = _extension_archivo(getattr(archivo_referencia, "name", ""))

        if tipo == ElementoGaleriaInformativa.TIPO_VIDEO:
            if extension not in ALLOWED_VIDEO_EXTENSIONS:
                self.add_error(
                    "archivo",
                    "Para tipo video solo se permiten archivos MP4, WEBM u OGG.",
                )
                return cleaned_data

            if getattr(archivo_referencia, "size", 0) > MAX_VIDEO_SIZE_BYTES:
                self.add_error("archivo", "El video no puede superar 120 MB.")

            content_type = getattr(archivo_subido, "content_type", "")
            if archivo_subido and content_type and not content_type.startswith("video/"):
                self.add_error("archivo", "El archivo seleccionado no corresponde a un video.")

            return cleaned_data

        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            self.add_error(
                "archivo",
                "Para tipo imagen solo se permiten archivos JPG, PNG o WEBP.",
            )
            return cleaned_data

        if getattr(archivo_referencia, "size", 0) > MAX_IMAGE_SIZE_BYTES:
            self.add_error("archivo", "La imagen no puede superar 20 MB.")

        content_type = getattr(archivo_subido, "content_type", "")
        if archivo_subido and content_type and not content_type.startswith("image/"):
            self.add_error("archivo", "El archivo seleccionado no corresponde a una imagen.")
            return cleaned_data

        if archivo_subido:
            try:
                cleaned_data["archivo"] = _normalizar_orientacion_imagen(archivo_subido)
            except (UnidentifiedImageError, OSError):
                self.add_error("archivo", "El archivo cargado no es una imagen válida.")

        return cleaned_data