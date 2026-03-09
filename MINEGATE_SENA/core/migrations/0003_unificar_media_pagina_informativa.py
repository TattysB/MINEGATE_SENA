from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_elementoencabezadoinformativo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contenidopaginainformativa",
            name="imagen_principal",
            field=models.ImageField(blank=True, null=True, upload_to="pagina_informativa/img-copia/"),
        ),
        migrations.AlterField(
            model_name="contenidopaginainformativa",
            name="imagen_secundaria",
            field=models.ImageField(blank=True, null=True, upload_to="pagina_informativa/img-copia/"),
        ),
        migrations.AlterField(
            model_name="contenidopaginainformativa",
            name="imagen_terciaria",
            field=models.ImageField(blank=True, null=True, upload_to="pagina_informativa/img-copia/"),
        ),
        migrations.AlterField(
            model_name="elementoencabezadoinformativo",
            name="imagen",
            field=models.ImageField(upload_to="pagina_informativa/img-copia/"),
        ),
        migrations.AlterField(
            model_name="elementogaleriainformativa",
            name="archivo",
            field=models.FileField(upload_to="pagina_informativa/img-copia/"),
        ),
    ]
