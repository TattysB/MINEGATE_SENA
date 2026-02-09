from django.db import models


class Availability(models.Model):
	date = models.DateField()
	time = models.TimeField()
	# optional: who configured
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['date', 'time']
		unique_together = ('date', 'time')

	def __str__(self):
		return f"{self.date} {self.time}" 
