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
			data=json.dumps({"mensaje": "Que es SICAM y para que sirve?"}),
			content_type="application/json",
		)
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		self.assertIn("SICAM", payload["respuesta"])

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
