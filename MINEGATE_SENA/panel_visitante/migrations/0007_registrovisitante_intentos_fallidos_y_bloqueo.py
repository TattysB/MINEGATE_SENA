from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("panel_visitante", "0006_alter_registrovisitante_table"),
    ]

    operations = [
        migrations.AddField(
            model_name="registrovisitante",
            name="bloqueado_hasta",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="registrovisitante",
            name="intentos_fallidos",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
