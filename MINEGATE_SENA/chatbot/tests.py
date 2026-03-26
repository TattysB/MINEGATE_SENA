import json

from django.test import Client, TestCase
from django.urls import reverse


class ChatbotEndpointTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.url = reverse("chatbot:responder")

	def test_responde_pregunta_conocida(self):
		response = self.client.post(
			self.url,
			data=json.dumps({"mensaje": "Como agendo una visita en la plataforma?"}),
			content_type="application/json",
		)
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		self.assertIn("pagina principal", payload["respuesta"])

	def test_respuesta_fallback_cuando_no_hay_match(self):
		response = self.client.post(
			self.url,
			data=json.dumps({"mensaje": "pregunta totalmente distinta"}),
			content_type="application/json",
		)
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		self.assertIn("Aun no tengo", payload["respuesta"])

	def test_bloquea_preguntas_sobre_modulos_admin(self):
		response = self.client.post(
			self.url,
			data=json.dumps({"mensaje": "Como entro al modulo de reportes del admin?"}),
			content_type="application/json",
		)
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		self.assertIn("modulos administrativos", payload["respuesta"])
