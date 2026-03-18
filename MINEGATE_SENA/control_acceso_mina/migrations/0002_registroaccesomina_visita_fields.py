from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('control_acceso_mina', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='registroaccesomina',
            name='visita_id',
            field=models.PositiveIntegerField(blank=True, db_index=True, null=True, verbose_name='ID de Visita'),
        ),
        migrations.AddField(
            model_name='registroaccesomina',
            name='visita_tipo',
            field=models.CharField(blank=True, choices=[('interna', 'Interna'), ('externa', 'Externa')], db_index=True, max_length=10, null=True, verbose_name='Tipo de Visita'),
        ),
    ]
