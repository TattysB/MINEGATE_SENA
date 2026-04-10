import re
import unicodedata

from django.utils.html import strip_tags


_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_MULTI_SPACE_RE = re.compile(r"[ \t]+")


def sanitize_text(value, max_length=1000, allow_newlines=True):
    """Sanitiza texto de entrada para almacenamiento/uso en respuestas."""
    text = strip_tags(str(value or ""))
    text = unicodedata.normalize("NFKC", text)
    text = _CONTROL_CHARS_RE.sub("", text)

    if allow_newlines:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = "\n".join(_MULTI_SPACE_RE.sub(" ", line).strip() for line in text.split("\n"))
    else:
        text = text.replace("\r", " ").replace("\n", " ")
        text = _MULTI_SPACE_RE.sub(" ", text).strip()

    text = text.strip()
    if max_length and len(text) > max_length:
        text = text[:max_length].strip()
    return text


def sanitize_document_number(value, max_length=50):
    """Permite solo caracteres típicos de documentos."""
    text = sanitize_text(value, max_length=max_length * 2, allow_newlines=False).upper()
    text = re.sub(r"[^0-9A-Z\-.]", "", text)
    return text[:max_length]


def sanitize_token(value, max_length=40):
    """Sanitiza tokens/identificadores cortos usados en filtros o acciones."""
    text = sanitize_text(value, max_length=max_length * 2, allow_newlines=False).lower()
    text = re.sub(r"[^a-z0-9_-]", "", text)
    return text[:max_length]


def sanitize_phone(value, max_length=20):
    text = sanitize_text(value, max_length=max_length * 2, allow_newlines=False)
    text = re.sub(r"[^0-9+()\- ]", "", text)
    return text[:max_length].strip()
