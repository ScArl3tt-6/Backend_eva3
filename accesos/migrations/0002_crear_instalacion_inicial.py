# ============================================================
# accesos/migrations/0002_crear_instalacion_inicial.py
# Crea la única fila de Instalacion si todavía no existe ninguna.
# El aforo máximo por defecto se puede editar luego desde el Django
# Admin; esta migración solo garantiza que la fila exista (la pauta
# exige "una sola fila creada por migración de datos o por seed_data").
# ============================================================
from django.db import migrations


def crear_instalacion(apps, schema_editor):
    Instalacion = apps.get_model("accesos", "Instalacion")
    if not Instalacion.objects.exists():
        Instalacion.objects.create(nombre="FitLife", aforo_maximo=50)


def eliminar_instalacion(apps, schema_editor):
    apps.get_model("accesos", "Instalacion").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accesos", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(crear_instalacion, eliminar_instalacion),
    ]
