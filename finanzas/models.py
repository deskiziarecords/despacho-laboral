from django.db import models
from django.contrib.auth.models import User

from expedientes.models import Cliente, Expediente


class Office(models.Model):
    """
    Catálogo de oficinas / sucursales del despacho.
    
    Cada oficina tiene su propia operación y puede tener
    su propio registro de ingresos, gastos y caja diaria.
    """

    nombre = models.CharField('Nombre de la oficina', max_length=200, unique=True)
    direccion = models.TextField('Dirección', blank=True,
                                  help_text='Dirección completa de la oficina')
    telefono = models.CharField('Teléfono', max_length=15, blank=True)
    responsable = models.CharField('Responsable', max_length=200, blank=True,
                                    help_text='Nombre del encargado de la oficina')
    activa = models.BooleanField('¿Oficina activa?', default=True,
                                  help_text='Desmarca para desactivar la oficina sin eliminarla')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Oficina'
        verbose_name_plural = 'Oficinas'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['activa']),
        ]

    def __str__(self):
        return self.nombre


class SettlementPayment(models.Model):
    """
    Registro de pagos recibidos por convenios.
    
    Cada vez que un cliente paga un acuerdo (convenio), se registra aquí
    el ingreso con su forma de pago y oficina correspondiente.
    """

    FORMA_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia bancaria'),
        ('cheque', 'Cheque'),
        ('tarjeta_credito', 'Tarjeta de crédito'),
        ('tarjeta_debito', 'Tarjeta de débito'),
        ('deposito', 'Depósito'),
        ('otro', 'Otro'),
    ]

    fecha = models.DateField('Fecha de pago')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT,
                                 verbose_name='Cliente')
    expediente = models.ForeignKey(Expediente, on_delete=models.PROTECT,
                                    verbose_name='Expediente',
                                    help_text='Expediente relacionado al pago')
    monto = models.DecimalField('Monto', max_digits=12, decimal_places=2)
    forma_pago = models.CharField('Forma de pago', max_length=20,
                                   choices=FORMA_PAGO_CHOICES, default='efectivo')
    oficina = models.ForeignKey('Office', on_delete=models.PROTECT,
                                 verbose_name='Oficina',
                                 help_text='Oficina que recibe el pago')
    notas = models.TextField('Notas', blank=True,
                              help_text='Notas adicionales sobre el pago')

    # Auditoría
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT,
                                       verbose_name='Registrado por',
                                       related_name='pagos_registrados')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pago de Convenio'
        verbose_name_plural = 'Pagos de Convenios'
        ordering = ['-fecha', '-created_at']
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['forma_pago']),
            models.Index(fields=['oficina', 'fecha']),
        ]

    def __str__(self):
        return f"${self.monto:,.2f} - {self.cliente.nombre} ({self.fecha})"


class Expense(models.Model):
    """
    Registro de gastos operativos por oficina.
    
    Cada gasto se clasifica por categoría y se asocia a una oficina
    para poder calcular la utilidad real por sucursal.
    """

    CATEGORIA_CHOICES = [
        ('renta', 'Renta'),
        ('luz', 'Luz'),
        ('agua', 'Agua'),
        ('internet', 'Internet'),
        ('telefono', 'Teléfono'),
        ('papeleria', 'Papelería'),
        ('publicidad', 'Publicidad'),
        ('sueldos', 'Sueldos'),
        ('gasolina', 'Gasolina'),
        ('mantenimiento', 'Mantenimiento'),
        ('impuestos', 'Impuestos'),
        ('equipo', 'Equipo/Cómputo'),
        ('muebles', 'Muebles'),
        ('seguros', 'Seguros'),
        ('honorarios', 'Honorarios profesionales'),
        ('otro', 'Otro'),
    ]

    fecha = models.DateField('Fecha del gasto')
    categoria = models.CharField('Categoría', max_length=20,
                                  choices=CATEGORIA_CHOICES, default='otro')
    monto = models.DecimalField('Monto', max_digits=12, decimal_places=2)
    descripcion = models.TextField('Descripción', blank=True,
                                    help_text='Descripción o detalle del gasto')
    proveedor = models.CharField('Proveedor', max_length=200, blank=True,
                                  help_text='Nombre del proveedor o beneficiario')
    folio_fiscal = models.CharField('Folio fiscal / Factura', max_length=100, blank=True,
                                     help_text='Número de factura o comprobante')
    oficina = models.ForeignKey('Office', on_delete=models.PROTECT,
                                 verbose_name='Oficina',
                                 help_text='Oficina a la que pertenece el gasto')

    # Auditoría
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT,
                                       verbose_name='Registrado por',
                                       related_name='gastos_registrados')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Gasto Operativo'
        verbose_name_plural = 'Gastos Operativos'
        ordering = ['-fecha', '-created_at']
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['categoria']),
            models.Index(fields=['oficina', 'fecha']),
        ]

    def __str__(self):
        return f"{self.get_categoria_display()} - ${self.monto:,.2f} ({self.fecha})"


class Commission(models.Model):
    """
    Comisiones de asesores sobre convenios cerrados.
    
    Cuando un asesor cierra un convenio, se le asigna un porcentaje
    como comisión. Este modelo registra cada comisión generada,
    su estado de pago y el cálculo automático del monto.
    """

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada'),
    ]

    expediente = models.ForeignKey(Expediente, on_delete=models.PROTECT,
                                    verbose_name='Expediente',
                                    help_text='Expediente del convenio que generó la comisión')
    asesor = models.ForeignKey(User, on_delete=models.PROTECT,
                                verbose_name='Asesor',
                                limit_choices_to={'profile__rol': 'asesor'},
                                related_name='comisiones',
                                help_text='Asesor que recibe la comisión')
    fecha = models.DateField('Fecha')
    monto_convenio = models.DecimalField('Monto del convenio', max_digits=12, decimal_places=2,
                                          help_text='Monto total del convenio cerrado')
    porcentaje = models.DecimalField('Porcentaje de comisión', max_digits=5, decimal_places=2,
                                      help_text='Ej: 5.00 = 5%', default=5.00)
    monto_comision = models.DecimalField('Monto de comisión', max_digits=12, decimal_places=2,
                                          help_text='Calculado automáticamente')
    estado = models.CharField('Estado', max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    fecha_pago = models.DateField('Fecha de pago', null=True, blank=True)
    oficina = models.ForeignKey('Office', on_delete=models.PROTECT,
                                 verbose_name='Oficina',
                                 help_text='Oficina del asesor')
    notas = models.TextField('Notas', blank=True)

    # Auditoría
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT,
                                       verbose_name='Registrado por',
                                       related_name='comisiones_registradas')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Comisión'
        verbose_name_plural = 'Comisiones'
        ordering = ['-fecha', '-created_at']
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['estado']),
            models.Index(fields=['asesor', 'estado']),
            models.Index(fields=['oficina', 'fecha']),
        ]

    def __str__(self):
        return f"{self.asesor.get_full_name() or self.asesor.username} - ${self.monto_comision:,.2f} ({self.get_estado_display()})"

    def save(self, *args, **kwargs):
        # Calcular automáticamente el monto de comisión
        self.monto_comision = self.monto_convenio * self.porcentaje / 100
        super().save(*args, **kwargs)


class Employee(models.Model):
    """
    Catálogo de empleados del despacho.
    
    Incluye tanto al personal administrativo como a los asesores
    que reciben un salario base (nómina).
    """

    PUESTO_CHOICES = [
        ('administrativo', 'Administrativo'),
        ('asesor', 'Asesor jurídico'),
        ('supervisor', 'Supervisor jurídico'),
        ('contador', 'Contador'),
        ('recepcionista', 'Recepcionista'),
        ('auxiliar', 'Auxiliar'),
        ('director', 'Director'),
        ('otro', 'Otro'),
    ]

    PERIODO_PAGO_CHOICES = [
        ('semanal', 'Semanal'),
        ('quincenal', 'Quincenal'),
        ('mensual', 'Mensual'),
    ]

    nombre = models.CharField('Nombre completo', max_length=200)
    puesto = models.CharField('Puesto', max_length=30, choices=PUESTO_CHOICES, default='administrativo')
    periodo_pago = models.CharField('Periodo de pago', max_length=15,
                                     choices=PERIODO_PAGO_CHOICES, default='quincenal')
    salario = models.DecimalField('Salario', max_digits=10, decimal_places=2,
                                   help_text='Salario base del empleado')
    telefono = models.CharField('Teléfono', max_length=15, blank=True)
    email = models.EmailField('Email', blank=True)
    oficina = models.ForeignKey('Office', on_delete=models.PROTECT,
                                 verbose_name='Oficina',
                                 help_text='Oficina a la que está asignado')
    activo = models.BooleanField('¿Activo?', default=True,
                                  help_text='Desmarca cuando el empleado ya no trabaje aquí')
    notas = models.TextField('Notas', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['activo']),
            models.Index(fields=['oficina', 'activo']),
        ]

    def __str__(self):
        return f"{self.nombre} - {self.get_puesto_display()}"


class Payroll(models.Model):
    """
    Registro de pagos de nómina por período.
    
    Cada vez que se le paga a un empleado, se registra aquí
    el detalle del pago: período, monto pagado y oficina.
    """

    PERIODO_CHOICES = [
        ('semanal', 'Semanal'),
        ('quincenal', 'Quincenal'),
        ('mensual', 'Mensual'),
        ('extraordinario', 'Extraordinario'),
        ('aguinaldo', 'Aguinaldo'),
        ('prima_vacacional', 'Prima vacacional'),
        ('bono', 'Bono'),
    ]

    empleado = models.ForeignKey('Employee', on_delete=models.PROTECT,
                                  verbose_name='Empleado',
                                  related_name='pagos_nomina')
    fecha_pago = models.DateField('Fecha de pago')
    periodo = models.CharField('Período', max_length=20,
                                choices=PERIODO_CHOICES, default='quincenal')
    periodo_inicio = models.DateField('Inicio del período', null=True, blank=True,
                                       help_text='Inicio del período que cubre este pago')
    periodo_fin = models.DateField('Fin del período', null=True, blank=True,
                                    help_text='Fin del período que cubre este pago')
    salario_pagado = models.DecimalField('Salario pagado', max_digits=10, decimal_places=2,
                                          help_text='Monto pagado en este período')
    descuentos = models.DecimalField('Descuentos', max_digits=10, decimal_places=2,
                                      default=0, help_text='Descuentos aplicados (ISR, IMSS, etc.)')
    total_pagado = models.DecimalField('Total pagado', max_digits=10, decimal_places=2,
                                        help_text='Salario pagado - descuentos. Calculado automáticamente')
    oficina = models.ForeignKey('Office', on_delete=models.PROTECT,
                                 verbose_name='Oficina',
                                 help_text='Oficina que realiza el pago')
    notas = models.TextField('Notas', blank=True)

    # Auditoría
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT,
                                       verbose_name='Registrado por',
                                       related_name='nominas_registradas')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pago de Nómina'
        verbose_name_plural = 'Pagos de Nómina'
        ordering = ['-fecha_pago', '-created_at']
        indexes = [
            models.Index(fields=['fecha_pago']),
            models.Index(fields=['empleado', 'fecha_pago']),
            models.Index(fields=['oficina', 'fecha_pago']),
            models.Index(fields=['periodo']),
        ]

    def __str__(self):
        return f"{self.empleado.nombre} - ${self.total_pagado:,.2f} ({self.fecha_pago})"

    def save(self, *args, **kwargs):
        # Calcular total automáticamente
        self.total_pagado = self.salario_pagado - self.descuentos
        super().save(*args, **kwargs)


class CashMovement(models.Model):
    """
    Registro de caja diaria por oficina.
    
    Controla las entradas y salidas de efectivo del día a día.
    El saldo se calcula dinámicamente sumando ingresos y restando egresos
    agrupados por oficina y fecha.
    """

    TIPO_CHOICES = [
        ('ingreso', 'Ingreso'),
        ('egreso', 'Egreso'),
    ]

    CATEGORIA_INGRESO_CHOICES = [
        ('convenio', 'Pago de convenio'),
        ('cliente', 'Pago de cliente'),
        ('anticipo', 'Anticipo'),
        ('devolucion', 'Devolución'),
        ('otro_ingreso', 'Otro ingreso'),
    ]

    CATEGORIA_EGRESO_CHOICES = [
        ('papeleria', 'Papelería'),
        ('gasolina', 'Gasolina'),
        ('renta', 'Renta'),
        ('luz', 'Luz'),
        ('agua', 'Agua'),
        ('internet', 'Internet'),
        ('telefono', 'Teléfono'),
        ('viaticos', 'Viáticos'),
        ('comisiones', 'Comisiones'),
        ('honorarios', 'Honorarios'),
        ('otro_egreso', 'Otro egreso'),
    ]

    CATEGORIA_CHOICES = CATEGORIA_INGRESO_CHOICES + CATEGORIA_EGRESO_CHOICES

    oficina = models.ForeignKey('Office', on_delete=models.PROTECT,
                                 verbose_name='Oficina',
                                 help_text='Oficina donde se registra el movimiento')
    fecha = models.DateField('Fecha')
    tipo = models.CharField('Tipo', max_length=10, choices=TIPO_CHOICES)
    categoria = models.CharField('Categoría', max_length=20, choices=CATEGORIA_CHOICES)
    monto = models.DecimalField('Monto', max_digits=12, decimal_places=2)
    descripcion = models.TextField('Descripción', blank=True,
                                    help_text='Detalle del movimiento')
    referencia = models.CharField('Referencia', max_length=200, blank=True,
                                   help_text='Número de expediente, factura o nota relacionada')

    # Auditoría
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT,
                                       verbose_name='Registrado por',
                                       related_name='caja_registrada')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Movimiento de Caja'
        verbose_name_plural = 'Movimientos de Caja'
        ordering = ['-fecha', '-created_at']
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['tipo']),
            models.Index(fields=['categoria']),
            models.Index(fields=['oficina', 'fecha', 'tipo']),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.get_categoria_display()} - ${self.monto:,.2f} ({self.oficina.nombre})"

    def clean(self):
        """
        Valida que la categoría sea coherente con el tipo (ingreso/egreso).
        """
        from django.core.exceptions import ValidationError
        super().clean()
        cat_ingreso_keys = [c[0] for c in self.CATEGORIA_INGRESO_CHOICES]
        if self.tipo == 'ingreso' and self.categoria not in cat_ingreso_keys:
            raise ValidationError({
                'categoria': 'La categoría seleccionada no corresponde a un ingreso.'
            })
        if self.tipo == 'egreso' and self.categoria in cat_ingreso_keys:
            raise ValidationError({
                'categoria': 'La categoría seleccionada no corresponde a un egreso.'
            })
