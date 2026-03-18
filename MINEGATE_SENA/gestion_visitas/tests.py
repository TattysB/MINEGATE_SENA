from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from calendario.models import ReservaHorario
from visitaExterna.models import HistorialReprogramacion as HistorialReprogramacionExterna
from visitaExterna.models import VisitaExterna
from visitaInterna.models import HistorialReprogramacion as HistorialReprogramacionInterna
from visitaInterna.models import VisitaInterna


class CompletarReprogramacionTests(TestCase):
	def test_responsable_interno_por_sesion_puede_reenviar_a_coordinacion(self):
		visita = VisitaInterna.objects.create(
			estado="reprogramacion_solicitada",
			nombre_programa="Tecnologia en Minas",
			numero_ficha=12345,
			responsable="Instructor Interno",
			tipo_documento_responsable="CC",
			documento_responsable="10001",
			correo_responsable="interno@example.com",
			telefono_responsable="3000000000",
			cantidad_aprendices=20,
		)
		historial = HistorialReprogramacionInterna.objects.create(
			visita_interna=visita,
			fecha_anterior=timezone.now(),
			motivo="Cambiar fecha",
			tipo="coordinador",
			completada=False,
		)

		session = self.client.session
		session["responsable_autenticado"] = True
		session["responsable_rol"] = "interno"
		session["responsable_correo"] = "interno@example.com"
		session["responsable_documento"] = "10001"
		session.save()

		fecha_nueva = (timezone.localdate() + timedelta(days=2)).isoformat()
		response = self.client.post(
			reverse(
				"gestion_visitas:completar_reprogramacion",
				kwargs={"tipo": "interna", "visita_id": visita.id},
			),
			{
				"fecha": fecha_nueva,
				"hora": "08:00",
				"hora_fin": "10:00",
				"historial_id": historial.id,
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertJSONEqual(response.content, {
			"success": True,
			"message": f"✅ Visita reprogramada exitosamente. Nueva fecha: {(timezone.datetime.strptime(fecha_nueva + ' 08:00', '%Y-%m-%d %H:%M')).strftime('%d/%m/%Y %H:%M')}"
		})

		visita.refresh_from_db()
		historial.refresh_from_db()

		self.assertEqual(visita.estado, "enviada_coordinacion")
		self.assertEqual(str(visita.fecha_visita), fecha_nueva)
		self.assertEqual(visita.hora_inicio.strftime("%H:%M"), "08:00")
		self.assertEqual(visita.hora_fin.strftime("%H:%M"), "10:00")
		self.assertTrue(historial.completada)
		self.assertIsNotNone(historial.fecha_reprogramacion)
		self.assertTrue(ReservaHorario.objects.filter(visita_interna=visita).exists())

	def test_responsable_externo_por_sesion_puede_reenviar_a_coordinacion(self):
		visita = VisitaExterna.objects.create(
			estado="reprogramacion_solicitada",
			nombre="Colegio Demo",
			nombre_responsable="Instructor Externo",
			tipo_documento_responsable="CC",
			documento_responsable="20002",
			correo_responsable="externo@example.com",
			telefono_responsable="3111111111",
			cantidad_visitantes=15,
		)
		historial = HistorialReprogramacionExterna.objects.create(
			visita_externa=visita,
			fecha_anterior=timezone.now(),
			motivo="Cambiar fecha",
			tipo="coordinador",
			completada=False,
		)

		session = self.client.session
		session["responsable_autenticado"] = True
		session["responsable_rol"] = "externo"
		session["responsable_correo"] = "externo@example.com"
		session["responsable_documento"] = "20002"
		session.save()

		fecha_nueva = (timezone.localdate() + timedelta(days=3)).isoformat()
		response = self.client.post(
			reverse(
				"gestion_visitas:completar_reprogramacion",
				kwargs={"tipo": "externa", "visita_id": visita.id},
			),
			{
				"fecha": fecha_nueva,
				"hora": "09:00",
				"hora_fin": "11:00",
				"historial_id": historial.id,
			},
		)

		self.assertEqual(response.status_code, 200)

		visita.refresh_from_db()
		historial.refresh_from_db()

		self.assertEqual(visita.estado, "enviada_coordinacion")
		self.assertEqual(str(visita.fecha_visita), fecha_nueva)
		self.assertEqual(visita.hora_inicio.strftime("%H:%M"), "09:00")
		self.assertEqual(visita.hora_fin.strftime("%H:%M"), "11:00")
		self.assertTrue(historial.completada)
		self.assertIsNotNone(historial.fecha_reprogramacion)
		self.assertTrue(ReservaHorario.objects.filter(visita_externa=visita).exists())
