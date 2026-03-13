import json
import re
import unicodedata
from difflib import SequenceMatcher

from django.db.utils import OperationalError, ProgrammingError
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .knowledge_base import BASE_FAQ
from .models import PreguntaFrecuente


FALLBACK_RESPUESTA = (
	"Aun no tengo una respuesta exacta para eso. "
	"Puedes intentar con una pregunta sobre registro de visitas, seguridad, "
	"calendario, documentos o reportes."
)


def _normalizar_texto(texto):
	texto = (texto or "").strip().lower()
	texto = unicodedata.normalize("NFKD", texto)
	texto = "".join(c for c in texto if not unicodedata.combining(c))
	texto = re.sub(r"[^a-z0-9\s]", " ", texto)
	return re.sub(r"\s+", " ", texto).strip()


def _tokenizar(texto):
	return [t for t in _normalizar_texto(texto).split(" ") if len(t) > 1]


def _conocimiento_desde_bd():
	try:
		registros = PreguntaFrecuente.objects.filter(activa=True)
		return [
			{
				"pregunta": row.pregunta,
				"respuesta": row.respuesta,
				"palabras_clave": row.palabras_clave,
				"prioridad": row.prioridad,
			}
			for row in registros
		]
	except (OperationalError, ProgrammingError):
		return []


def _obtener_base_conocimiento():
	return BASE_FAQ + _conocimiento_desde_bd()


def _puntaje_entrada(texto_usuario, entrada):
	pregunta = entrada.get("pregunta", "")
	palabras_clave = entrada.get("palabras_clave", "")
	prioridad = int(entrada.get("prioridad", 5) or 5)

	normal_usuario = _normalizar_texto(texto_usuario)
	normal_pregunta = _normalizar_texto(pregunta)

	if normal_usuario == normal_pregunta:
		return 1.0

	similitud = SequenceMatcher(None, normal_usuario, normal_pregunta).ratio()

	tokens_usuario = set(_tokenizar(texto_usuario))
	tokens_referencia = set(_tokenizar(pregunta)) | set(_tokenizar(palabras_clave))

	if tokens_usuario and tokens_referencia:
		coincidencias = len(tokens_usuario & tokens_referencia)
		cobertura = coincidencias / max(len(tokens_usuario), 1)
	else:
		cobertura = 0

	puntaje = (similitud * 0.65) + (cobertura * 0.35)
	return min(puntaje * (1 + (prioridad / 100.0)), 1.0)


def _buscar_respuesta(mensaje):
	base = _obtener_base_conocimiento()
	if not base:
		return {
			"respuesta": FALLBACK_RESPUESTA,
			"confianza": 0,
			"sugerencias": [],
		}

	candidatos = []
	for entrada in base:
		score = _puntaje_entrada(mensaje, entrada)
		candidatos.append((score, entrada))

	candidatos.sort(key=lambda item: item[0], reverse=True)

	mejor_score, mejor_entrada = candidatos[0]
	sugerencias = [
		item[1]["pregunta"]
		for item in candidatos[1:4]
		if item[0] >= 0.30 and item[1].get("pregunta")
	]

	if mejor_score < 0.40:
		return {
			"respuesta": FALLBACK_RESPUESTA,
			"confianza": round(mejor_score, 3),
			"sugerencias": sugerencias,
		}

	return {
		"respuesta": mejor_entrada.get("respuesta", FALLBACK_RESPUESTA),
		"confianza": round(mejor_score, 3),
		"sugerencias": sugerencias,
	}


@require_POST
def responder_chatbot(request):
	try:
		payload = json.loads(request.body.decode("utf-8"))
	except (json.JSONDecodeError, UnicodeDecodeError):
		return JsonResponse({"ok": False, "error": "JSON invalido"}, status=400)

	mensaje = (payload.get("mensaje") or "").strip()
	if not mensaje:
		return JsonResponse(
			{"ok": False, "error": "El mensaje no puede estar vacio"},
			status=400,
		)

	resultado = _buscar_respuesta(mensaje)
	return JsonResponse({"ok": True, **resultado})
