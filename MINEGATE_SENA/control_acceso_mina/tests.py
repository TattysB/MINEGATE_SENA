from django.test import TestCase, Client
from django.contrib.auth.models import User
from control_acceso_mina.models import RegistroAccesoMina
from control_acceso_mina.views import _parse_qr_data, _contar_personas_en_visita_mina


def _registro(documento, tipo, visita_id=1, visita_tipo='interna', nombre='Test Usuario'):
    return RegistroAccesoMina.objects.create(
        documento=documento,
        nombre_completo=nombre,
        categoria='Visitante',
        visita_tipo=visita_tipo,
        visita_id=visita_id,
        tipo=tipo,
    )


class RegistroAccesoMinaTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='portero', password='1234')
        self.client = Client()


    def test_crear_registro_entrada(self):
        r = _registro('11111111', 'ENTRADA')
        self.assertEqual(r.tipo, 'ENTRADA')
        self.assertEqual(r.documento, '11111111')

    def test_crear_registro_salida(self):
        r = _registro('22222222', 'SALIDA')
        self.assertEqual(r.tipo, 'SALIDA')

    def test_str_contiene_nombre_y_tipo(self):
        r = _registro('33333333', 'ENTRADA', nombre='Carlos López')
        self.assertIn('Carlos López', str(r))
        self.assertIn('ENTRADA', str(r))

    def test_registrado_por_puede_ser_nulo(self):
        r = _registro('44444444', 'ENTRADA')
        self.assertIsNone(r.registrado_por)

    def test_fecha_hora_se_asigna_sola(self):
        r = _registro('55555555', 'ENTRADA')
        self.assertIsNotNone(r.fecha_hora)


    def test_conteo_sin_registros_es_cero(self):
        self.assertEqual(_contar_personas_en_visita_mina('interna', 1), 0)

    def test_conteo_una_entrada(self):
        _registro('66666666', 'ENTRADA')
        self.assertEqual(_contar_personas_en_visita_mina('interna', 1), 1)

    def test_conteo_entrada_salida_es_cero(self):
        _registro('77777777', 'ENTRADA')
        _registro('77777777', 'SALIDA')
        self.assertEqual(_contar_personas_en_visita_mina('interna', 1), 0)

    def test_conteo_no_mezcla_visitas(self):
        _registro('88888888', 'ENTRADA', visita_id=1)
        _registro('88888888', 'ENTRADA', visita_id=2)
        self.assertEqual(_contar_personas_en_visita_mina('interna', 1), 1)
        self.assertEqual(_contar_personas_en_visita_mina('interna', 2), 1)

    def test_conteo_no_mezcla_tipos(self):
        _registro('99999999', 'ENTRADA', visita_tipo='interna')
        self.assertEqual(_contar_personas_en_visita_mina('externa', 1), 0)


    def test_qr_valido(self):
        r = _parse_qr_data('SENA|1|12345678|Juan Pérez|interna')
        self.assertEqual(r['documento'], '12345678')
        self.assertEqual(r['tipo'], 'interna')
        self.assertEqual(r['visita_id'], 1)

    def test_qr_sin_pipes(self):
        self.assertEqual(_parse_qr_data('12345678'), {})

    def test_qr_prefijo_incorrecto(self):
        self.assertEqual(_parse_qr_data('OTRO|1|111|Nombre|interna'), {})

    def test_qr_vacio(self):
        self.assertEqual(_parse_qr_data(''), {})

    def test_qr_tipo_invalido(self):
        r = _parse_qr_data('SENA|1|111|Nombre|desconocido')
        self.assertIsNone(r.get('tipo'))


    def test_registrar_sin_login_redirige(self):
        resp = self.client.post('/porteria/registrar/', '{}', content_type='application/json')
        self.assertEqual(resp.status_code, 302)

    def test_datos_visita_sin_login_redirige(self):
        resp = self.client.get('/porteria/visita/interna/1/datos/')
        self.assertEqual(resp.status_code, 302)

    def test_registrar_tipo_invalido_retorna_400(self):
        self.client.force_login(self.user)
        import json
        resp = self.client.post(
            '/porteria/registrar/',
            data=json.dumps({'documento': '123', 'qr_data': '',
                             'selected_visit_type': 'invalido', 'selected_visit_id': 1}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()['success'])

    def test_datos_visita_inexistente_retorna_404(self):
        self.client.force_login(self.user)
        resp = self.client.get('/porteria/visita/interna/99999/datos/')
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(resp.json()['success'])