from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calendario', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='availability',
            name='end_time',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='availability',
            unique_together={('date', 'time', 'end_time')},
        ),
    ]
