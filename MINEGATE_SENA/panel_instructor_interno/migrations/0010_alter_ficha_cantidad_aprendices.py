import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel_instructor_interno', '0009_alter_ficha_cantidad_aprendices_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ficha',
            name='cantidad_aprendices',
            field=models.PositiveIntegerField(
                default=1,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(100),
                ],
                verbose_name='Cantidad de Aprendices',
            ),
        ),
    ]
