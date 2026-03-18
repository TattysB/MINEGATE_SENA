from django.db import models


class Availability(models.Model):
	date = models.DateField()
	time = models.TimeField()
	end_time = models.TimeField(null=True, blank=True)
	# optional: who configured
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['date', 'time', 'end_time']
		unique_together = ('date', 'time', 'end_time')
		db_table = 'availability'

	def __str__(self):
		if self.end_time:
			return f"{self.date} {self.time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"
		return f"{self.date} {self.time.strftime('%H:%M')}"


class ReservaHorario(models.Model):
	"""
	Modelo para rastrear reservas de horarios de visitas.
	- estado 'pendiente': aprobación inicial, bloquea el horario (se muestra naranja)
	- estado 'confirmada': visita confirmada definitivamente (se muestra rojo)
	"""
	ESTADO_CHOICES = [
		('pendiente', 'Pendiente de revisión'),
		('confirmada', 'Confirmada'),
	]
	
	fecha = models.DateField(verbose_name="Fecha de la visita")
	hora_inicio = models.TimeField(verbose_name="Hora de inicio")
	hora_fin = models.TimeField(verbose_name="Hora de fin")
	estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='pendiente')
	
	# Relación con visita (solo una será válida)
	visita_interna = models.ForeignKey(
		'visitaInterna.VisitaInterna',
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name='reservas_horario'
	)
	visita_externa = models.ForeignKey(
		'visitaExterna.VisitaExterna',
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name='reservas_horario'
	)
	
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	class Meta:
		ordering = ['fecha', 'hora_inicio']
		verbose_name = "Reserva de Horario"
		verbose_name_plural = "Reservas de Horarios"
		db_table = 'reserva_horario'
	
	def __str__(self):
		tipo = "Interna" if self.visita_interna else "Externa"
		return f"{self.fecha} {self.hora_inicio.strftime('%H:%M')}-{self.hora_fin.strftime('%H:%M')} ({tipo}) - {self.get_estado_display()}"
	
	@classmethod
	def crear_reserva_interna(cls, visita):
		"""Crea una reserva para una visita interna"""
		if visita.fecha_visita and visita.hora_inicio and visita.hora_fin:
			reserva, created = cls.objects.get_or_create(
				visita_interna=visita,
				defaults={
					'fecha': visita.fecha_visita,
					'hora_inicio': visita.hora_inicio,
					'hora_fin': visita.hora_fin,
					'estado': 'pendiente'
				}
			)
			return reserva
		return None
	
	@classmethod
	def crear_reserva_externa(cls, visita):
		"""Crea una reserva para una visita externa"""
		if visita.fecha_visita and visita.hora_inicio and visita.hora_fin:
			reserva, created = cls.objects.get_or_create(
				visita_externa=visita,
				defaults={
					'fecha': visita.fecha_visita,
					'hora_inicio': visita.hora_inicio,
					'hora_fin': visita.hora_fin,
					'estado': 'pendiente'
				}
			)
			return reserva
		return None
	
	@classmethod
	def confirmar_reserva(cls, visita, tipo='interna'):
		"""Confirma una reserva existente"""
		if tipo == 'interna':
			reserva = cls.objects.filter(visita_interna=visita).first()
		else:
			reserva = cls.objects.filter(visita_externa=visita).first()
		
		if reserva:
			reserva.estado = 'confirmada'
			reserva.save()
		return reserva

	@classmethod
	def liberar_reserva(cls, visita, tipo='interna'):
		"""Libera (elimina) la reserva asociada a una visita rechazada o cancelada."""
		if tipo == 'interna':
			qs = cls.objects.filter(visita_interna=visita)
		else:
			qs = cls.objects.filter(visita_externa=visita)
		deleted, _ = qs.delete()
		return deleted
	
	@classmethod
	def horario_disponible(cls, fecha, hora_inicio, hora_fin):
		"""Verifica si un horario está disponible (no hay reservas que se superpongan)"""
		# Buscar reservas que se superponen con el horario solicitado
		reservas_existentes = cls.objects.filter(
			fecha=fecha
		).filter(
			# Superposición: inicio1 < fin2 AND inicio2 < fin1
			hora_inicio__lt=hora_fin,
			hora_fin__gt=hora_inicio
		)
		return not reservas_existentes.exists()
