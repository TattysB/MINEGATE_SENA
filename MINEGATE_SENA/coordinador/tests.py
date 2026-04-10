from datetime import date, time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from calendario.models import ReservaHorario
from coordinador.models import AprobacionRegistro
from visitaExterna.models import (
	HistorialAccionVisitaExterna,
	HistorialReprogramacion as HistorialReprogramacionExterna,
	VisitaExterna,
)
from visitaInterna.models import HistorialAccionVisitaInterna, VisitaInterna


class CoordinadorTestBase(TestCase):
	def setUp(self):
		self.user_model = get_user_model()
		self.coordinador_group, _ = Group.objects.get_or_create(name="coordinador")
		self.coordinador = self.user_model.objects.create_user(
			username="coord_test",
			email="coord@test.com",
			password="testpass123",
		)
		self.coordinador.groups.add(self.coordinador_group)

	def login_como_coordinador(self):
		self.client.force_login(self.coordinador)

	def _crear_visita_interna(
		self,
		responsable="Responsable Interno",
		estado="enviada_coordinacion",
		fecha_visita=None,
		hora_inicio=None,
		hora_fin=None,
	):
		return VisitaInterna.objects.create(
			estado=estado,
			responsable=responsable,
			tipo_documento_responsable="CC",
			documento_responsable="10000001",
			correo_responsable="interno@test.com",
			telefono_responsable="3000000001",
			nombre_programa="Programa de Prueba",
			numero_ficha=123456,
			cantidad_aprendices=25,
			fecha_visita=fecha_visita,
			hora_inicio=hora_inicio,
			hora_fin=hora_fin,
		)

	def _crear_visita_externa(
		self,
		responsable="Responsable Externo",
		estado="enviada_coordinacion",
		fecha_visita=None,
		hora_inicio=None,
		hora_fin=None,
	):
		return VisitaExterna.objects.create(
			estado=estado,
			nombre="Institucion de Prueba",
			nombre_responsable=responsable,
			tipo_documento_responsable="CC",
			documento_responsable="20000001",
			correo_responsable="externo@test.com",
			telefono_responsable="3100000001",
			cantidad_visitantes=12,
			fecha_visita=fecha_visita,
			hora_inicio=hora_inicio,
			hora_fin=hora_fin,
		)

class CoordinadorViewsTests(CoordinadorTestBase):

	def test_api_solicitudes_internas_filtra_por_estado_y_busqueda(self):
		self.login_como_coordinador()
		esperada = self._crear_visita_interna(responsable="Ana Lopez")
		self._crear_visita_interna(responsable="Bruno Sierra", estado="pendiente")
		self._crear_visita_interna(responsable="Carlos Diaz")

		url = reverse("coordinador:api_solicitudes")
		response = self.client.get(url, {"tipo": "internas", "buscar": "ana"})

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertEqual(len(payload["visitas"]), 1)
		self.assertEqual(payload["visitas"][0]["id"], esperada.id)
		self.assertEqual(payload["visitas"][0]["tipo"], "interna")


	def test_api_accion_aprobar_interna_actualiza_estado_y_registra(self):
		self.login_como_coordinador()
		visita = self._crear_visita_interna(responsable="Marta Rios")

		url = reverse("coordinador:api_accion", args=["interna", visita.id, "aprobar"])
		response = self.client.post(url)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.json()["success"])

		visita.refresh_from_db()
		self.assertEqual(visita.estado, "pendiente")
		self.assertTrue(
			AprobacionRegistro.objects.filter(
				visita_id=visita.id,
				visita_tipo="interna",
				aprobado_por=self.coordinador,
			).exists()
		)
		self.assertTrue(
			HistorialAccionVisitaInterna.objects.filter(
				visita=visita,
				tipo_accion="aprobacion",
			).exists()
		)


	def test_api_accion_rechazar_externa_crea_reprogramacion_y_libera_reserva(self):
		self.login_como_coordinador()
		fecha_visita = date(2026, 3, 25)
		inicio = time(8, 0)
		fin = time(11, 0)
		visita = self._crear_visita_externa(
			responsable="Laura Mesa",
			fecha_visita=fecha_visita,
			hora_inicio=inicio,
			hora_fin=fin,
		)

		ReservaHorario.objects.create(
			fecha=fecha_visita,
			hora_inicio=inicio,
			hora_fin=fin,
			estado="pendiente",
			visita_externa=visita,
		)

		url = reverse("coordinador:api_accion", args=["externa", visita.id, "rechazar"])
		response = self.client.post(url, {"observaciones": "Se requiere nueva fecha"})

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.json()["success"])

		visita.refresh_from_db()
		self.assertEqual(visita.estado, "reprogramacion_solicitada")
		self.assertFalse(ReservaHorario.objects.filter(visita_externa=visita).exists())
		self.assertTrue(
			HistorialReprogramacionExterna.objects.filter(
				visita_externa=visita,
				tipo="coordinador",
			).exists()
		)
		self.assertTrue(
			HistorialAccionVisitaExterna.objects.filter(
				visita=visita,
				tipo_accion="rechazo",
			).exists()
		)


	def test_resumen_dia_coordinador_fecha_invalida_retorna_400(self):
		self.login_como_coordinador()
		url = reverse("coordinador:resumen_dia", args=["2026-99-99"])
		response = self.client.get(url)

		self.assertEqual(response.status_code, 400)
		self.assertFalse(response.json()["ok"])


	def test_resumen_dia_coordinador_retorna_visitas_de_ambos_tipos(self):
		self.login_como_coordinador()
		dia = date(2026, 3, 28)

		visita_interna = self._crear_visita_interna(
			responsable="Pedro Interno",
			fecha_visita=dia,
			hora_inicio=time(8, 0),
			hora_fin=time(11, 0),
		)
		visita_externa = self._crear_visita_externa(
			responsable="Sara Externa",
			fecha_visita=dia,
			hora_inicio=time(11, 0),
			hora_fin=time(13, 0),
		)

		ReservaHorario.objects.create(
			fecha=dia,
			hora_inicio=time(8, 0),
			hora_fin=time(11, 0),
			estado="pendiente",
			visita_interna=visita_interna,
		)
		ReservaHorario.objects.create(
			fecha=dia,
			hora_inicio=time(11, 0),
			hora_fin=time(13, 0),
			estado="confirmada",
			visita_externa=visita_externa,
		)

		url = reverse("coordinador:resumen_dia", args=[dia.isoformat()])
		response = self.client.get(url)

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		self.assertEqual(payload["day"], dia.isoformat())
		self.assertEqual(len(payload["visitas"]), 2)

		tipos = {item["tipo_slug"] for item in payload["visitas"]}
		self.assertSetEqual(tipos, {"interna", "externa"})