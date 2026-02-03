from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'priority', 'read', 'created_at')
    list_filter = ('priority', 'read', 'created_at')
    search_fields = ('title', 'message', 'user__username', 'user__email')
from django.contrib import admin

# Register your models here.
