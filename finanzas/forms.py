from django import forms
from .models import CashMovement, Office


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
        # Initial category choices based on default tipo (ingreso)
        self.fields['categoria'].choices = CashMovement.CATEGORIA_INGRESO_CHOICES
