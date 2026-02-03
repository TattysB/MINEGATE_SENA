from django.db import migrations


def create_samples(apps, schema_editor):
    Notification = apps.get_model('notificaciones', 'Notification')
    User = apps.get_model('auth', 'User')
    try:
        user = User.objects.first()
        if not user:
            return
        Notification.objects.create(user=user, title='¡Bienvenido a MineGate!', message='Sistema de gestión de visitas iniciado correctamente', priority=2)
        Notification.objects.create(user=user, title='Documentos pendientes', message='Tienes documentos pendientes de revisión', priority=3)
    except Exception:
        # Fail silently in case auth.User not available or other issues
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('notificaciones', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_samples, reverse_code=migrations.RunPython.noop),
    ]
