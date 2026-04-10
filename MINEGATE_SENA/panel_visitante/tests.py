from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from .models import RegistroVisitante
from .views import REGISTRO_VERIFICACION_SESSION_KEY


class RegistroVisitaTests(TestCase):
	def setUp(self):
		self.url_registro = reverse("panel_visitante:registro_visita")
		self.url_verificar = reverse("panel_visitante:verificar_codigo_registro")
		self.valid_payload = {
			"nombre": "Ana",
			"apellido": "Lopez",
			"tipo_documento": "CC",
			"documento": "1234567890",
			"telefono": "3001234567",
			"correo": "ana@sena.edu.co",
			"rol": "interno",
			"password1": "Valida123!",
			"password2": "Valida123!",
		}

	def test_registro_get_retorna_200_y_formulario(self):
		response = self.client.get(self.url_registro)

		self.assertEqual(response.status_code, 200)
		self.assertIn("form", response.context)

	def test_registro_post_rechaza_telefono_invalido(self):
		payload = dict(self.valid_payload)
		payload["telefono"] = "30012"

		response = self.client.post(self.url_registro, data=payload)

		self.assertEqual(response.status_code, 200)
		self.assertIn("form", response.context)
		self.assertTrue(response.context["form"].errors)
		self.assertIn("telefono", response.context["form"].errors)

	def test_registro_post_interno_requiere_correo_sena(self):
		payload = dict(self.valid_payload)
		payload["correo"] = "ana@gmail.com"

		response = self.client.post(self.url_registro, data=payload)

		self.assertEqual(response.status_code, 200)
		self.assertIn("form", response.context)
		self.assertIn("correo", response.context["form"].errors)

	@patch("panel_visitante.views._enviar_codigo_verificacion_registro")
	def test_registro_post_valido_guarda_sesion_y_redirige(self, mock_enviar):
		response = self.client.post(self.url_registro, data=self.valid_payload)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, self.url_verificar)
		self.assertTrue(mock_enviar.called)

		datos = self.client.session.get(REGISTRO_VERIFICACION_SESSION_KEY)
		self.assertIsNotNone(datos)
		self.assertEqual(datos["correo"], "ana@sena.edu.co")
		self.assertEqual(datos["documento"], "1234567890")
		self.assertEqual(datos["rol"], "interno")

	def test_registro_post_rechaza_documento_duplicado(self):
		visitante = RegistroVisitante(
			nombre="Carlos",
			apellido="Perez",
			tipo_documento="CC",
			documento="1234567890",
			telefono="3001234567",
			correo="carlos@sena.edu.co",
			rol="interno",
		)
		visitante.set_password("Valida123!")
		visitante.save()

		payload = dict(self.valid_payload)
		payload["correo"] = "nuevo@sena.edu.co"

		response = self.client.post(self.url_registro, data=payload)

		self.assertEqual(response.status_code, 200)
		self.assertIn("form", response.context)
		self.assertIn("documento", response.context["form"].errors)
