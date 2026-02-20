from django.db import models
from django.contrib.auth.hashers import check_password, make_password


class RegistroVisitante(models.Model):
	ROLES = [
		('interno', 'Usuario Interno (SENA)'),
		('externo', 'Usuario Externo'),
	]
	
	correo = models.EmailField(unique=True)
	documento = models.CharField(max_length=20, unique=True)
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
		return f"{self.documento} - {self.correo} ({self.get_rol_display()})"
