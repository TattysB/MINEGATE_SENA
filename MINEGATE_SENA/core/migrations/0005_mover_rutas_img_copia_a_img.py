from django.db import migrations


RUTA_ANTIGUA = "pagina_informativa/img-copia/"
RUTA_NUEVA = "img/"


def _tabla_existente(tablas, opciones):
    for nombre in opciones:
        if nombre in tablas:
            return nombre
    return None


def _migrar_campo(schema_editor, tabla, campo):
    qn = schema_editor.quote_name
    schema_editor.execute(
        (
            f"UPDATE {qn(tabla)} "
            f"SET {qn(campo)} = REPLACE({qn(campo)}, %s, %s) "
            f"WHERE {qn(campo)} LIKE %s"
        ),
        [RUTA_ANTIGUA, RUTA_NUEVA, f"{RUTA_ANTIGUA}%"],
    )


def forwards(apps, schema_editor):
    tablas = set(schema_editor.connection.introspection.table_names())

    contenido = _tabla_existente(
        tablas,
        ["core_contenidopaginainformativa", "contenido_pagina_informativa"],
    )
    encabezado = _tabla_existente(
        tablas,
        ["core_elementoencabezadoinformativo", "elemento_encabezado_informativo"],
    )
    galeria = _tabla_existente(
        tablas,
        ["core_elementogaleriainformativa", "elemento_galeria_informativa"],
    )

    if contenido:
        _migrar_campo(schema_editor, contenido, "imagen_principal")
        _migrar_campo(schema_editor, contenido, "imagen_secundaria")
        _migrar_campo(schema_editor, contenido, "imagen_terciaria")

    if encabezado:
        _migrar_campo(schema_editor, encabezado, "imagen")

    if galeria:
        _migrar_campo(schema_editor, galeria, "archivo")


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
