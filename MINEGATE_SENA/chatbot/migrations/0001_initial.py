from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PreguntaFrecuente",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("pregunta", models.CharField(max_length=280, unique=True)),
                ("respuesta", models.TextField()),
                ("palabras_clave", models.CharField(blank=True, max_length=280)),
                ("activa", models.BooleanField(default=True)),
                ("prioridad", models.PositiveSmallIntegerField(default=5)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Pregunta frecuente",
                "verbose_name_plural": "Preguntas frecuentes",
                "ordering": ("-prioridad", "pregunta"),
            },
        ),
    ]
