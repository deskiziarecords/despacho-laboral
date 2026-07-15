from django import forms
from .models import CashMovement, Office, Partner, WorkWeek, PartnerLoan


class CashMovementForm(forms.ModelForm):
    class Meta:
        model = CashMovement
        fields = ['oficina', 'fecha', 'tipo', 'categoria', 'monto', 'descripcion', 'referencia']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'}),
            'oficina': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'}),
            'tipo': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent', 'id': 'id_tipo'}),
            'categoria': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent', 'id': 'id_categoria'}),
            'monto': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent', 'step': '0.01', 'placeholder': '0.00'}),
            'descripcion': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent', 'rows': 3, 'placeholder': 'Describe el movimiento...'}),
            'referencia': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent', 'placeholder': 'N° de expediente, factura, etc.'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['oficina'].queryset = Office.objects.filter(activa=True)
        self.fields['semana'].queryset = WorkWeek.objects.filter(estado='abierta')
        # Initial category choices based on default tipo (ingreso)
        self.fields['categoria'].choices = CashMovement.CATEGORIA_INGRESO_CHOICES


class PartnerForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = ['nombre', 'porcentaje_participacion', 'telefono', 'email', 'activo', 'notas']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500', 'placeholder': 'Nombre completo del socio'}),
            'porcentaje_participacion': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500', 'step': '0.01', 'placeholder': '25.00'}),
            'telefono': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500', 'placeholder': 'Teléfono'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500', 'placeholder': 'email@ejemplo.com'}),
            'activo': forms.CheckboxInput(attrs={'class': 'rounded border-gray-300'}),
            'notas': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500', 'rows': 3}),
        }


class WorkWeekForm(forms.ModelForm):
    class Meta:
        model = WorkWeek
        fields = ['numero', 'fecha_inicio', 'fecha_fin', 'estado', 'notas']
        widgets = {
            'numero': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500', 'placeholder': '1-52'}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'estado': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'notas': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500', 'rows': 3}),
        }


class PartnerLoanForm(forms.ModelForm):
    class Meta:
        model = PartnerLoan
        fields = ['socio_origen', 'socio_destino', 'monto', 'fecha', 'concepto', 'estado', 'fecha_pago', 'notas']
        widgets = {
            'socio_origen': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'socio_destino': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'monto': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500', 'step': '0.01', 'placeholder': '0.00'}),
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'concepto': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500', 'placeholder': 'Ej: Préstamo personal'}),
            'estado': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'fecha_pago': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'notas': forms.Textarea(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['socio_origen'].queryset = Partner.objects.filter(activo=True)
        self.fields['socio_destino'].queryset = Partner.objects.filter(activo=True)
