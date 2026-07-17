from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expedientes', '0016_oficina_obligatorio'),
    ]

    operations = [
        # ─── Checkboxes de selección de conceptos ─────────────────
        migrations.AddField(
            model_name='calculolaboral',
            name='incluir_aguinaldo',
            field=models.BooleanField(default=True, verbose_name='Incluir aguinaldo'),
        ),
        migrations.AddField(
            model_name='calculolaboral',
            name='incluir_vacaciones',
            field=models.BooleanField(default=True, verbose_name='Incluir vacaciones'),
        ),
        migrations.AddField(
            model_name='calculolaboral',
            name='incluir_prima_vacacional',
            field=models.BooleanField(default=True, verbose_name='Incluir prima vacacional'),
        ),
        migrations.AddField(
            model_name='calculolaboral',
            name='incluir_prima_antiguedad',
            field=models.BooleanField(default=True, verbose_name='Incluir prima antigüedad'),
        ),
        migrations.AddField(
            model_name='calculolaboral',
            name='incluir_indemnizacion',
            field=models.BooleanField(default=True, verbose_name='Incluir indemnización 90 días'),
        ),
        migrations.AddField(
            model_name='calculolaboral',
            name='incluir_indemnizacion_20dias',
            field=models.BooleanField(default=False, verbose_name='Incluir 20 días por año'),
        ),
        migrations.AddField(
            model_name='calculolaboral',
            name='incluir_vacaciones_vencidas',
            field=models.BooleanField(default=False, verbose_name='Incluir vacaciones vencidas'),
        ),
        migrations.AddField(
            model_name='calculolaboral',
            name='incluir_horas_extras',
            field=models.BooleanField(default=False, verbose_name='Incluir horas extras'),
        ),
        migrations.AddField(
            model_name='calculolaboral',
            name='incluir_salarios_devengados',
            field=models.BooleanField(default=False, verbose_name='Incluir salarios devengados'),
        ),
        migrations.AddField(
            model_name='calculolaboral',
            name='incluir_dias_festivos',
            field=models.BooleanField(default=False, verbose_name='Incluir días festivos'),
        ),
        # ─── Nuevos resultados y campos de entrada ────────────────
        migrations.AddField(
            model_name='calculolaboral',
            name='indemnizacion_20dias',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Indemnización 20 días por año'),
        ),
        migrations.AddField(
            model_name='calculolaboral',
            name='dias_vacaciones_vencidos',
            field=models.PositiveIntegerField(default=0, help_text='Días de vacaciones de años anteriores que no se pagaron', verbose_name='Días de vacaciones vencidas'),
        ),
        migrations.AddField(
            model_name='calculolaboral',
            name='vacaciones_vencidas',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Vacaciones vencidas'),
        ),
        migrations.AddField(
            model_name='calculolaboral',
            name='horas_extra_cantidad',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Número total de horas extra trabajadas', max_digits=8, verbose_name='Cantidad de horas extra'),
        ),
        migrations.AddField(
            model_name='calculolaboral',
            name='horas_extras',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Horas extras'),
        ),
        migrations.AddField(
            model_name='calculolaboral',
            name='salarios_devengados',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Monto de salarios no pagados', max_digits=12, verbose_name='Salarios devengados'),
        ),
        migrations.AddField(
            model_name='calculolaboral',
            name='dias_festivos_cantidad',
            field=models.PositiveIntegerField(default=0, help_text='Número de días festivos laborados no pagados', verbose_name='Cantidad de días festivos'),
        ),
        migrations.AddField(
            model_name='calculolaboral',
            name='dias_festivos',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Días festivos'),
        ),
        # ─── Actualizar verbose_name del campo existente ──────────
        migrations.AlterField(
            model_name='calculolaboral',
            name='indemnizacion',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Indemnización constitucional (90 días)'),
        ),
    ]
