from django.db import models
from django.conf import settings


class Notification(models.Model):
	PRIORITY_LOW = 1
	PRIORITY_NORMAL = 2
	PRIORITY_HIGH = 3

	PRIORITY_CHOICES = (
		(PRIORITY_LOW, 'Baja'),
		(PRIORITY_NORMAL, 'Normal'),
		(PRIORITY_HIGH, 'Alta'),
	)

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
	title = models.CharField(max_length=200)
	message = models.TextField(blank=True)
	priority = models.PositiveSmallIntegerField(choices=PRIORITY_CHOICES, default=PRIORITY_NORMAL)
	read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.title} ({'leída' if self.read else 'nueva'})"
