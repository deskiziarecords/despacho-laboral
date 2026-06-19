from django.contrib import admin
from django.utils import timezone
from .models import Office, SettlementPayment, Expense, Commission, Employee, Payroll, CashMovement


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'responsable', 'telefono', 'activa', 'created_at']
    list_filter = ['activa', 'created_at']
    search_fields = ['nombre', 'responsable', 'direccion']
    list_editable = ['activa']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = [
        ('Información General', {
            'fields': ['nombre', 'direccion', 'telefono', 'responsable']
        }),
        ('Estado', {
            'fields': ['activa']
        }),
        ('Metadatos', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(SettlementPayment)
class SettlementPaymentAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'cliente', 'expediente', 'monto_formateado', 'forma_pago', 'oficina', 'registrado_por']
    list_filter = ['forma_pago', 'oficina', 'fecha']
    search_fields = ['cliente__nombre', 'cliente__curp', 'expediente__numero', 'notas']
    date_hierarchy = 'fecha'
    autocomplete_fields = ['cliente', 'expediente', 'oficina', 'registrado_por']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = [
        ('Información del Pago', {
            'fields': ['fecha', 'cliente', 'expediente', 'monto', 'forma_pago', 'oficina']
        }),
        ('Notas', {
            'fields': ['notas']
        }),
        ('Auditoría', {
            'fields': ['registrado_por', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    def monto_formateado(self, obj):
        return f'${obj.monto:,.2f}'
    monto_formateado.short_description = 'Monto'
    monto_formateado.admin_order_field = 'monto'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            # Si el admin no seleccionó explícitamente quién registró, asignar al usuario actual
            if not obj.registrado_por_id:
                obj.registrado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'categoria', 'monto_formateado', 'oficina', 'proveedor', 'registrado_por']
    list_filter = ['categoria', 'oficina', 'fecha']
    search_fields = ['descripcion', 'proveedor', 'folio_fiscal']
    date_hierarchy = 'fecha'
    autocomplete_fields = ['oficina', 'registrado_por']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = [
        ('Información del Gasto', {
            'fields': ['fecha', 'categoria', 'monto', 'descripcion', 'proveedor', 'folio_fiscal', 'oficina']
        }),
        ('Auditoría', {
            'fields': ['registrado_por', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    def monto_formateado(self, obj):
        return f'${obj.monto:,.2f}'
    monto_formateado.short_description = 'Monto'
    monto_formateado.admin_order_field = 'monto'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            if not obj.registrado_por_id:
                obj.registrado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'asesor', 'monto_convenio_formateado', 'porcentaje', 'monto_comision_formateado', 'estado', 'oficina']
    list_filter = ['estado', 'oficina', 'fecha']
    search_fields = ['asesor__username', 'asesor__first_name', 'asesor__last_name', 'expediente__numero', 'notas']
    date_hierarchy = 'fecha'
    autocomplete_fields = ['expediente', 'asesor', 'oficina', 'registrado_por']
    readonly_fields = ['monto_comision', 'created_at', 'updated_at']
    list_editable = ['estado']
    fieldsets = [
        ('Información de la Comisión', {
            'fields': ['fecha', 'expediente', 'asesor', 'oficina']
        }),
        ('Cálculo', {
            'fields': ['monto_convenio', 'porcentaje', 'monto_comision'],
            'description': 'El monto de comisión se calcula automáticamente: monto_del_convenio × porcentaje ÷ 100'
        }),
        ('Estado de Pago', {
            'fields': ['estado', 'fecha_pago']
        }),
        ('Notas', {
            'fields': ['notas']
        }),
        ('Auditoría', {
            'fields': ['registrado_por', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    def monto_convenio_formateado(self, obj):
        return f'${obj.monto_convenio:,.2f}'
    monto_convenio_formateado.short_description = 'Convenio'
    monto_convenio_formateado.admin_order_field = 'monto_convenio'

    def monto_comision_formateado(self, obj):
        return f'${obj.monto_comision:,.2f}'
    monto_comision_formateado.short_description = 'Comisión'
    monto_comision_formateado.admin_order_field = 'monto_comision'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            if not obj.registrado_por_id:
                obj.registrado_por = request.user
        # Si cambia a pagada y no tiene fecha, asignar hoy
        if obj.estado == 'pagada' and not obj.fecha_pago:
            obj.fecha_pago = timezone.now().date()
        super().save_model(request, obj, form, change)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'puesto', 'periodo_pago', 'salario_formateado', 'oficina', 'activo']
    list_filter = ['puesto', 'periodo_pago', 'oficina', 'activo']
    search_fields = ['nombre', 'telefono', 'email', 'notas']
    list_editable = ['activo']
    autocomplete_fields = ['oficina']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = [
        ('Información General', {
            'fields': ['nombre', 'puesto', 'periodo_pago', 'oficina']
        }),
        ('Salario', {
            'fields': ['salario']
        }),
        ('Contacto', {
            'fields': ['telefono', 'email']
        }),
        ('Estatus', {
            'fields': ['activo', 'notas']
        }),
        ('Metadatos', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    def salario_formateado(self, obj):
        return f'${obj.salario:,.2f}'
    salario_formateado.short_description = 'Salario'
    salario_formateado.admin_order_field = 'salario'


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['fecha_pago', 'empleado', 'periodo', 'salario_pagado_formateado', 'total_pagado_formateado', 'oficina', 'registrado_por']
    list_filter = ['periodo', 'oficina', 'fecha_pago']
    search_fields = ['empleado__nombre', 'notas']
    date_hierarchy = 'fecha_pago'
    autocomplete_fields = ['empleado', 'oficina', 'registrado_por']
    readonly_fields = ['total_pagado', 'created_at', 'updated_at']
    fieldsets = [
        ('Empleado y Período', {
            'fields': ['empleado', 'fecha_pago', 'periodo', 'periodo_inicio', 'periodo_fin']
        }),
        ('Montos', {
            'fields': ['salario_pagado', 'descuentos', 'total_pagado'],
            'description': 'El total se calcula automáticamente: salario_pagado - descuentos'
        }),
        ('Oficina', {
            'fields': ['oficina']
        }),
        ('Notas', {
            'fields': ['notas']
        }),
        ('Auditoría', {
            'fields': ['registrado_por', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    def salario_pagado_formateado(self, obj):
        return f'${obj.salario_pagado:,.2f}'
    salario_pagado_formateado.short_description = 'Salario'
    salario_pagado_formateado.admin_order_field = 'salario_pagado'

    def total_pagado_formateado(self, obj):
        return f'${obj.total_pagado:,.2f}'
    total_pagado_formateado.short_description = 'Total'
    total_pagado_formateado.admin_order_field = 'total_pagado'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            if not obj.registrado_por_id:
                obj.registrado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(CashMovement)
class CashMovementAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'oficina', 'tipo', 'categoria', 'monto_formateado', 'descripcion_resumida', 'registrado_por']
    list_filter = ['tipo', 'categoria', 'oficina', 'fecha']
    search_fields = ['descripcion', 'referencia']
    date_hierarchy = 'fecha'
    autocomplete_fields = ['oficina', 'registrado_por']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = [
        ('Información del Movimiento', {
            'fields': ['oficina', 'fecha', 'tipo', 'categoria', 'monto']
        }),
        ('Detalle', {
            'fields': ['descripcion', 'referencia']
        }),
        ('Auditoría', {
            'fields': ['registrado_por', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    def monto_formateado(self, obj):
        return f'${obj.monto:,.2f}'
    monto_formateado.short_description = 'Monto'
    monto_formateado.admin_order_field = 'monto'

    def descripcion_resumida(self, obj):
        return obj.descripcion[:60] + '…' if len(obj.descripcion) > 60 else obj.descripcion
    descripcion_resumida.short_description = 'Descripción'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            if not obj.registrado_por_id:
                obj.registrado_por = request.user
        super().save_model(request, obj, form, change)
