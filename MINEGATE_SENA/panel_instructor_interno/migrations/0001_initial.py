from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Programa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=300, unique=True, verbose_name='Nombre del Programa')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('activo', models.BooleanField(default=True, verbose_name='Activo')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                ('creado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='programas_creados', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
            ],
            options={
                'verbose_name': 'Programa',
                'verbose_name_plural': 'Programas',
                'ordering': ['nombre'],
            },
        ),
        migrations.CreateModel(
            name='Ficha',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.PositiveIntegerField(unique=True, verbose_name='Número de Ficha')),
                ('jornada', models.CharField(choices=[('mañana', 'Mañana'), ('tarde', 'Tarde'), ('noche', 'Noche'), ('mixta', 'Mixta')], default='mañana', max_length=20, verbose_name='Jornada')),
                ('cantidad_aprendices', models.PositiveIntegerField(default=0, verbose_name='Cantidad de Aprendices')),
                ('activa', models.BooleanField(default=True, verbose_name='Activa')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                ('creado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fichas_creadas', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
                ('programa', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='fichas', to='panel_instructor_interno.programa', verbose_name='Programa')),
            ],
            options={
                'verbose_name': 'Ficha',
                'verbose_name_plural': 'Fichas',
                'ordering': ['-numero'],
            },
        ),
    ]
