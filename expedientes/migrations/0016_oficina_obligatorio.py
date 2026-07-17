from django.db import migrations, models


def asignar_oficina_default(apps, schema_editor):
    """Asigna 'plaza_patria' a los clientes existentes que no tengan oficina asignada."""
    Cliente = apps.get_model('expedientes', 'Cliente')
    Cliente.objects.filter(oficina='').update(oficina='plaza_patria')


class Migration(migrations.Migration):

    dependencies = [
        ('expedientes', '0015_add_como_supo_and_oficina_to_cliente'),
    ]

    operations = [
        migrations.RunPython(asignar_oficina_default, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='cliente',
            name='oficina',
            field=models.CharField(choices=[('plaza_patria', 'Plaza Patria'), ('plaza_patria_abajo', 'Plaza Patria Abajo'), ('otay', 'Otay')], help_text='¿Cuál oficina atendió al cliente?', max_length=30, verbose_name='Oficina que atendió'),
        ),
    ]
