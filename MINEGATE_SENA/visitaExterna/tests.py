from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from .models import (
	VisitaExterna,
	AsistenteVisitaExterna,
	documento_asistente_path_externa,
	HistorialAccionVisitaExterna,
	HistorialReprogramacion,
)


class VisitaExternaModelTests(TestCase):
	def setUp(self):
		self.user_model = get_user_model()
		self.user = self.user_model.objects.create_user(username='tester', password='pass')

	def test_visita_token_and_enlace_generated(self):
		v = VisitaExterna.objects.create(
			nombre='Institucion X',
			nombre_responsable='Responsable Y',
			tipo_documento_responsable='CC',
			documento_responsable='12345678',
			correo_responsable='resp@example.com',
			telefono_responsable='3001112222',
			cantidad_visitantes=5,
		)
		# token_acceso debe generarse al guardar
		self.assertIsNotNone(v.token_acceso)
		self.assertEqual(len(v.token_acceso), 32)
		enlace = v.get_enlace_registro()
		self.assertIn(v.token_acceso, enlace)
		self.assertTrue(enlace.endswith(f"/{v.token_acceso}/"))

	def test_asistente_unique_together_raises(self):
		v = VisitaExterna.objects.create(
			nombre='Inst A',
			nombre_responsable='Resp A',
			tipo_documento_responsable='CC',
			documento_responsable='1111',
			correo_responsable='a@e.com',
			telefono_responsable='300000',
			cantidad_visitantes=2,
		)
		AsistenteVisitaExterna.objects.create(
			visita=v,
			nombre_completo='Asistente Uno',
			tipo_documento='CC',
			numero_documento='ABC123',
		)
		# intentar crear otro con mismo visita y numero_documento debe fallar
		with self.assertRaises(IntegrityError):
			AsistenteVisitaExterna.objects.create(
				visita=v,
				nombre_completo='Asistente Dos',
				tipo_documento='CC',
				numero_documento='ABC123',
			)

	def test_documento_asistente_path_externa_format(self):
		v = VisitaExterna.objects.create(
			nombre='Inst B',
			nombre_responsable='Resp B',
			tipo_documento_responsable='CC',
			documento_responsable='2222',
			correo_responsable='b@e.com',
			telefono_responsable='300111',
			cantidad_visitantes=1,
		)
		a = AsistenteVisitaExterna(visita=v, numero_documento='DOC99', nombre_completo='X')
		path = documento_asistente_path_externa(a, 'identidad.pdf')
		expected = f"documentos_asistentes/externa/{v.id}/DOC99/identidad.pdf"
		self.assertEqual(path, expected)

	def test_historial_accion_str_contains_display_and_visita(self):
		v = VisitaExterna.objects.create(
			nombre='Inst C',
			nombre_responsable='Resp C',
			tipo_documento_responsable='CC',
			documento_responsable='3333',
			correo_responsable='c@e.com',
			telefono_responsable='300222',
			cantidad_visitantes=3,
		)
		h = HistorialAccionVisitaExterna.objects.create(
			visita=v,
			usuario=self.user,
			tipo_accion='creacion',
			descripcion='Se creó la solicitud',
		)
		s = str(h)
		self.assertIn(h.get_tipo_accion_display(), s)
		self.assertIn(str(v), s)

	def test_reprogramacion_str_contains_type_and_date(self):
		v = VisitaExterna.objects.create(
			nombre='Inst D',
			nombre_responsable='Resp D',
			tipo_documento_responsable='CC',
			documento_responsable='4444',
			correo_responsable='d@e.com',
			telefono_responsable='300333',
			cantidad_visitantes=4,
		)
		fecha_anterior = timezone.now()
		r = HistorialReprogramacion.objects.create(
			visita_externa=v,
			fecha_anterior=fecha_anterior,
			motivo='Necesario cambio de fecha',
			solicitado_por=self.user,
			tipo='coordinador',
		)
		s = str(r)
		self.assertIn('Reprogramación', s)
		self.assertIn(r.get_tipo_display(), s)