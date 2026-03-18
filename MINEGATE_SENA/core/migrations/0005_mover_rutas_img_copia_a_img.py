from django.db import migrations


RUTA_ANTIGUA = "pagina_informativa/img-copia/"
RUTA_NUEVA = "img/"


def _migrar_campo(apps, model_name, field_name):
    model = apps.get_model("core", model_name)
    for obj in model.objects.all().iterator():
        valor = getattr(obj, field_name)
        if not valor:
            continue
        ruta = str(valor)
        if not ruta.startswith(RUTA_ANTIGUA):
            continue

        setattr(obj, field_name, ruta.replace(RUTA_ANTIGUA, RUTA_NUEVA, 1))
        obj.save(update_fields=[field_name])


def forwards(apps, schema_editor):
    _migrar_campo(apps, "ContenidoPaginaInformativa", "imagen_principal")
    _migrar_campo(apps, "ContenidoPaginaInformativa", "imagen_secundaria")
    _migrar_campo(apps, "ContenidoPaginaInformativa", "imagen_terciaria")
    _migrar_campo(apps, "ElementoEncabezadoInformativo", "imagen")
    _migrar_campo(apps, "ElementoGaleriaInformativa", "archivo")


def backwards(apps, schema_editor):
    # No revertimos automáticamente para evitar inconsistencias en archivos físicos.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_unificar_media_img"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
