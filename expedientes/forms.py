from django import forms
from .models import Expediente, Cliente, Documento, Nota, SolicitudConciliacion, WhatsAppMessage, CalculoLaboral
from django.contrib.auth.models import User


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'curp', 'rfc', 'telefono', 'whatsapp', 'email',
                   'fecha_nacimiento', 'genero',
                   'direccion_calle', 'direccion_numero', 'direccion_cp', 'direccion_colonia',
                   'empresa', 'empresa_actividad', 'empresa_telefono', 'empresa_razon_social',
                   'empresa_calle', 'empresa_numero', 'empresa_colonia', 'empresa_cp', 'empresa_referencias',
                   'tipo_persona_citado',
                   'puesto', 'salario', 'periodo_pago', 'horas_semanales', 'jornada',
                   'fecha_ingreso', 'fecha_salida',
                   'como_supo', 'oficina',
                   'asesoria_gratuita_ofrecida', 'asesoria_gratuita_agendada', 'fecha_asesoria_gratuita']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Nombre completo del cliente'}),
            'curp': forms.TextInput(attrs={'class': 'input', 'placeholder': '18 caracteres (ej: AEMR890312HDFLNN01)', 'id': 'id_curp'}),
            'rfc': forms.TextInput(attrs={'class': 'input', 'placeholder': 'RFC (opcional)'}),
            'telefono': forms.TextInput(attrs={'class': 'input', 'placeholder': '+52 55 1234 5678'}),
            'whatsapp': forms.TextInput(attrs={'class': 'input', 'placeholder': '+52 55 1234 5678'}),
            'email': forms.EmailInput(attrs={'class': 'input', 'placeholder': 'cliente@email.com'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'input', 'type': 'date', 'id': 'id_fecha_nacimiento'}),
            'genero': forms.Select(attrs={'class': 'input', 'id': 'id_genero'}),
            'como_supo': forms.Select(attrs={'class': 'input'}),
            'oficina': forms.Select(attrs={'class': 'input'}),
            'direccion_calle': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Calle'}),
            'direccion_numero': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Número'}),
            'direccion_cp': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Código Postal'}),
            'direccion_colonia': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Colonia / Ejido / Poblado'}),
            'empresa': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Nombre de la empresa/patrón'}),
            'empresa_actividad': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Ej: Manufactura, Comercio, Servicios'}),
            'empresa_telefono': forms.TextInput(attrs={'class': 'input', 'placeholder': '+52 55 1234 5678'}),
            'empresa_razon_social': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Razón social o nombre comercial'}),
            'empresa_calle': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Calle'}),
            'empresa_numero': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Número'}),
            'empresa_colonia': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Colonia'}),
            'empresa_cp': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Código Postal'}),
            'empresa_referencias': forms.Textarea(attrs={'class': 'input', 'rows': 2, 'placeholder': 'Referencias cercanas al domicilio'}),
            'tipo_persona_citado': forms.Select(attrs={'class': 'input'}),
            'puesto': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Puesto del trabajador'}),
            'salario': forms.NumberInput(attrs={'class': 'input'}),
            'periodo_pago': forms.Select(attrs={'class': 'input'}),
            'horas_semanales': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'Ej: 40'}),
            'jornada': forms.Select(attrs={'class': 'input'}),
            'fecha_ingreso': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'fecha_salida': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'asesoria_gratuita_ofrecida': forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500'}),
            'asesoria_gratuita_agendada': forms.CheckboxInput(attrs={'class': 'w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500'}),
            'fecha_asesoria_gratuita': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
        }


class SolicitudConciliacionForm(forms.ModelForm):
    class Meta:
        model = SolicitudConciliacion
        exclude = ['expediente', 'created_at', 'updated_at']
        widgets = {
            'unidad_sede': forms.TextInput(attrs={'class': 'input text-center font-semibold'}),
            'fecha_solicitud': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'edad': forms.NumberInput(attrs={'class': 'input'}),
            'fecha_conflicto': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'horas_semanales': forms.NumberInput(attrs={'class': 'input'}),
            'periodo_pago': forms.RadioSelect(),
            'citatorio_entrega': forms.RadioSelect(),
            'traductor_lengua': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Ej: Mixteco, Zapoteco, Inglés...'}),
            'firma_nombre': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Nombre completo del solicitante'}),
            'firma_fecha': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'objeto_despido': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'objeto_terminacion_voluntaria': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'objeto_antiguedad': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'objeto_rescision': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'objeto_prestaciones': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'objeto_preferencia': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'objeto_ascenso': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'objeto_acoso': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'discapacidad_motriz': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'discapacidad_visual': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'discapacidad_auditiva': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'discapacidad_psicosocial': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'discapacidad_habla': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
            'requiere_traductor': forms.CheckboxInput(attrs={'class': 'w-4 h-4'}),
        }


class ExpedienteForm(forms.ModelForm):
    class Meta:
        model = Expediente
        fields = ['cliente', 'asesor', 'estado', 'monto_reclamado', 'monto_convenio',
                   'fecha_audiencia', 'proxima_accion', 'notas',
                   'tipo_despido', 'prestaciones_reclamadas', 'folio', 'fecha_tramite',
                   'prioridad']
        widgets = {
            'cliente': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            }),
            'asesor': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            }),
            'estado': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            }),
            'monto_reclamado': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            }),
            'monto_convenio': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            }),
            'fecha_audiencia': forms.DateTimeInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'type': 'datetime-local',
            }),
            'proxima_accion': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'type': 'date',
            }),
            'notas': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'rows': 4,
                'placeholder': 'Notas internas del caso...'
            }),
            'tipo_despido': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            }),
            'prestaciones_reclamadas': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'rows': 3,
                'placeholder': 'Aguinaldo, vacaciones, prima vacacional, prima antigüedad, etc.'
            }),
            'folio': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Folio de conciliación'
            }),
            'fecha_tramite': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'type': 'date',
            }),
            'prioridad': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Solo mostrar asesores en el campo asesor
        self.fields['asesor'].queryset = User.objects.filter(profile__rol='asesor')
        self.fields['asesor'].label_from_instance = lambda obj: obj.get_full_name() or obj.username

        # Si el usuario es asesor, solo puede asignarse a sí mismo
        if user and hasattr(user, 'profile') and user.profile.rol == 'asesor':
            self.fields['asesor'].initial = user
            self.fields['asesor'].disabled = True

        # Si es creación, asignar asesor por defecto
        if not self.instance.pk and user:
            if hasattr(user, 'profile') and user.profile.rol == 'asesor':
                self.fields['asesor'].initial = user

        # Los asesores no pueden cambiar el asesor asignado
        if self.instance.pk and user and hasattr(user, 'profile') and user.profile.rol == 'asesor':
            self.fields['asesor'].disabled = True


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ['archivo', 'descripcion', 'tipo']
        widgets = {
            'descripcion': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Descripción del documento'
            }),
            'tipo': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            }),
            'archivo': forms.FileInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
            }),
        }


class NotaForm(forms.ModelForm):
    class Meta:
        model = Nota
        fields = ['contenido']
        widgets = {
            'contenido': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'rows': 3,
                'placeholder': 'Escribe una nota o comentario...'
            }),
        }
        labels = {
            'contenido': '',
        }


class CalculoLaboralForm(forms.ModelForm):
    """Formulario para editar parámetros del cálculo laboral."""
    class Meta:
        model = CalculoLaboral
        fields = ['periodo_pago', 'notas']
        widgets = {
            'periodo_pago': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            }),
            'notas': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'rows': 3,
                'placeholder': 'Anotaciones sobre este cálculo...',
            }),
        }


class SimulacionForm(forms.Form):
    """Formulario de simulación rápida para el asesor.
    
    Permite estimar prestaciones sin necesidad de tener un expediente.
    """
    salario = forms.DecimalField(
        label='Salario mensual',
        max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'placeholder': 'Ej: 15000.00',
        })
    )
    fecha_ingreso = forms.DateField(
        label='Fecha de ingreso',
        widget=forms.DateInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'type': 'date',
        })
    )
    fecha_salida = forms.DateField(
        label='Fecha de salida / despido',
        widget=forms.DateInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'type': 'date',
        })
    )
    periodo_pago = forms.ChoiceField(
        label='Periodo de pago',
        choices=[('mensual', 'Mensual'), ('quincenal', 'Quincenal'), ('semanal', 'Semanal'), ('diario', 'Diario')],
        initial='mensual',
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent',
        })
    )


class WhatsAppMessageForm(forms.ModelForm):
    class Meta:
        model = WhatsAppMessage
        fields = ['destino', 'tipo', 'mensaje', 'via']
        widgets = {
            'destino': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent',
                'placeholder': '+526641234567',
                'id': 'whatsapp-destino',
            }),
            'tipo': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent',
                'id': 'whatsapp-tipo',
            }),
            'mensaje': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent',
                'rows': 4,
                'placeholder': 'Escribe el mensaje a enviar...',
                'id': 'whatsapp-mensaje',
            }),
            'via': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent',
                'id': 'whatsapp-via',
            }),
        }
