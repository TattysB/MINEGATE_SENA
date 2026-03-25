from django.test import TestCase

from core.sanitization import (
	sanitize_document_number,
	sanitize_phone,
	sanitize_text,
	sanitize_token,
)


class SanitizationHelpersTests(TestCase):
	def test_sanitize_text_remueve_html_y_espacios(self):
		raw = "  <script>alert(1)</script>  Hola    mundo  "
		self.assertEqual(sanitize_text(raw, allow_newlines=False), "alert(1) Hola mundo")

	def test_sanitize_text_remueve_caracteres_control(self):
		raw = "Linea1\x00\x1f\nLinea2\x7f"
		self.assertEqual(sanitize_text(raw), "Linea1\nLinea2")

	def test_sanitize_text_trunca_longitud(self):
		self.assertEqual(sanitize_text("abcdef", max_length=4), "abcd")

	def test_sanitize_document_number_filtra_caracteres_invalidos(self):
		raw = " cc-12.34/5*abc "
		self.assertEqual(sanitize_document_number(raw), "CC-12.345ABC")

	def test_sanitize_token_permite_solo_formato_seguro(self):
		raw = " Confirmada<script>-ok_01 "
		self.assertEqual(sanitize_token(raw), "confirmada-ok_01")

	def test_sanitize_phone_permite_caracteres_telefonicos(self):
		raw = " +57 (310)-123-45#67 ext "
		self.assertEqual(sanitize_phone(raw), "+57 (310)-123-4567")
