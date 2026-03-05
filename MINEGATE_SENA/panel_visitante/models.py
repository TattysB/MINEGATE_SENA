from django.db import models
from django.contrib.auth.hashers import check_password, make_password


class RegistroVisitante(models.Model):
	ROLES = [
		('interno', 'Usuario Interno (SENA)'),
		('externo', 'Usuario Externo'),
	]
	
	TIPOS_DOCUMENTO = [
		('CC', 'Cédula de Ciudadanía'),
		('TI', 'Tarjeta de Identidad'),
		('CE', 'Cédula de Extranjería'),
		('PA', 'Pasaporte'),
		('RC', 'Registro Civil'),
	]
	
	nombre = models.CharField(max_length=100, default='Sin nombre')
	apellido = models.CharField(max_length=100, default='Sin apellido')
	tipo_documento = models.CharField(max_length=2, choices=TIPOS_DOCUMENTO, default='CC')
	documento = models.CharField(max_length=20, unique=True)
	telefono = models.CharField(max_length=15, blank=True, null=True)
	correo = models.EmailField(unique=True)
	password_hash = models.CharField(max_length=128)
	rol = models.CharField(max_length=10, choices=ROLES, default='interno')
	created_at = models.DateTimeField(auto_now_add=True)
	last_login = models.DateTimeField(null=True, blank=True)

	def set_password(self, raw_password):
		self.password_hash = make_password(raw_password)

	def check_password(self, raw_password):
		return check_password(raw_password, self.password_hash)

	@property
	def password(self):
		"""Property que retorna password_hash (requerido por default_token_generator)"""
		return self.password_hash

	def get_email_field_name(self):
		"""Retorna el nombre del campo de email (requerido por default_token_generator)"""
		return 'correo'

	def __str__(self):
		return f"{self.nombre} {self.apellido} - {self.get_tipo_documento_display()} {self.documento}"
