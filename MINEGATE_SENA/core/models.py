from django.db import models
import mimetypes


PAGINA_INFORMATIVA_UPLOAD_DIR = "img/"


class ContenidoPaginaInformativa(models.Model):
	titulo_principal = models.CharField(max_length=200, default="Centro Minero de Morcá")
	texto_principal = models.TextField(
		default="Agenda tu experiencia minera de forma fácil, segura y digital."
	)
	imagen_principal = models.ImageField(
		upload_to=PAGINA_INFORMATIVA_UPLOAD_DIR, blank=True, null=True
	)

	texto_secundario = models.TextField(
		default="Ven, visita el SENA y vive la minería como una experiencia de aprendizaje."
	)
	imagen_secundaria = models.ImageField(
		upload_to=PAGINA_INFORMATIVA_UPLOAD_DIR, blank=True, null=True
	)

	texto_descripcion = models.TextField(
		default=(
			"El SENA Centro Minero de Morcá, a través de la plataforma SICAM, "
			"ofrece un sistema digital para la gestión y programación de visitas "
			"a la mina didáctica."
		)
	)
	imagen_terciaria = models.ImageField(
		upload_to=PAGINA_INFORMATIVA_UPLOAD_DIR, blank=True, null=True
	)

	titulo_galeria = models.CharField(
		max_length=200, default="Explora Nuestras Instalaciones"
	)
	descripcion_galeria = models.TextField(
		default="Conoce la mina didáctica y las experiencias que viven nuestros aprendices."
	)

	actualizado_en = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Contenido de página informativa"
		verbose_name_plural = "Contenido de página informativa"
		db_table = "contenido_pagina_informativa"

	def save(self, *args, **kwargs):
		self.pk = 1
		super().save(*args, **kwargs)

	@classmethod
	def obtener(cls):
		objeto, _ = cls.objects.get_or_create(pk=1)
		return objeto

	def __str__(self):
		return "Configuración de la página informativa"


class ElementoEncabezadoInformativo(models.Model):
	titulo = models.CharField(max_length=200, blank=True)
	texto = models.TextField(blank=True)
	imagen = models.ImageField(upload_to=PAGINA_INFORMATIVA_UPLOAD_DIR)
	orden = models.PositiveIntegerField(default=0)
	activo = models.BooleanField(default=True)
	creado_en = models.DateTimeField(auto_now_add=True)
	actualizado_en = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Elemento de encabezado informativo"
		verbose_name_plural = "Elementos de encabezado informativo"
		ordering = ["orden", "id"]
		db_table = "elemento_encabezado_informativo"

	def __str__(self):
		base = self.titulo.strip() if self.titulo else "Diapositiva"
		return f"{base} (#{self.id})"


class ElementoGaleriaInformativa(models.Model):
	TIPO_IMAGEN = "imagen"
	TIPO_VIDEO = "video"
	TIPOS_ARCHIVO = (
		(TIPO_IMAGEN, "Imagen"),
		(TIPO_VIDEO, "Video"),
	)

	tipo = models.CharField(max_length=10, choices=TIPOS_ARCHIVO, default=TIPO_IMAGEN)
	archivo = models.FileField(upload_to=PAGINA_INFORMATIVA_UPLOAD_DIR)
	titulo = models.CharField(max_length=120)
	descripcion = models.CharField(max_length=255, blank=True)
	orden = models.PositiveIntegerField(default=0)
	activo = models.BooleanField(default=True)
	creado_en = models.DateTimeField(auto_now_add=True)
	actualizado_en = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Elemento de galería informativa"
		verbose_name_plural = "Elementos de galería informativa"
		ordering = ["orden", "id"]
		db_table = "elemento_galeria_informativa"

	def __str__(self):
		return f"{self.get_tipo_display()}: {self.titulo}"

	@property
	def mime_type(self):
		nombre = getattr(self.archivo, "name", "")
		mime, _ = mimetypes.guess_type(nombre)
		if mime:
			return mime

		if self.tipo == self.TIPO_VIDEO:
			return "video/mp4"
		return "image/jpeg"


class ConfiguracionBackupAutomatico(models.Model):
	FRECUENCIA_6H = "6h"
	FRECUENCIA_12H = "12h"
	FRECUENCIA_24H = "24h"
	FRECUENCIA_48H = "48h"
	FRECUENCIA_72H = "72h"
	FRECUENCIA_168H = "168h"

	FRECUENCIAS = (
		(FRECUENCIA_6H, "Cada 6 horas"),
		(FRECUENCIA_12H, "Cada 12 horas"),
		(FRECUENCIA_24H, "Cada 24 horas"),
		(FRECUENCIA_48H, "Cada 48 horas"),
		(FRECUENCIA_72H, "Cada 72 horas"),
		(FRECUENCIA_168H, "Cada 7 días"),
	)

	activo = models.BooleanField(default=False)
	frecuencia = models.CharField(max_length=5, choices=FRECUENCIAS, default=FRECUENCIA_24H)
	ultima_ejecucion = models.DateTimeField(null=True, blank=True)
	actualizado_en = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Configuración de backup automático"
		verbose_name_plural = "Configuración de backups automáticos"
		db_table = "configuracion_backup_automatico"

	def save(self, *args, **kwargs):
		self.pk = 1
		super().save(*args, **kwargs)

	@classmethod
	def obtener(cls):
		objeto, _ = cls.objects.get_or_create(pk=1)
		return objeto

	def horas_frecuencia(self):
		try:
			return int(str(self.frecuencia).replace("h", ""))
		except (TypeError, ValueError):
			return 24

	def __str__(self):
		estado = "Activo" if self.activo else "Inactivo"
		return f"Backup automático ({estado})"
