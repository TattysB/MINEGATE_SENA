# Generated migration for adding password reset fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel_visitante', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='registrovisitante',
            name='reset_token',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='registrovisitante',
            name='reset_token_expires',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
