from django import forms
from django.core.exceptions import ValidationError
from .models import Cliente, Expediente, Documento, Movimiento, Evento, Tarea, EvidenciaTarea, PlantillaContrato, Contrato, ComentarioTarea
from django.contrib.auth.models import User

# ── Formulario de Cliente ─────────────────────
class ClienteForm(forms.ModelForm):
    class Meta:
        model  = Cliente
        fields = ['ci', 'nombre_completo', 'telefono', 'email',
                  'direccion', 'abogado_asignado', 'notas_internas']
        widgets = {
            'ci':               forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 1234567 LP'}),
            'nombre_completo':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre completo'}),
            'telefono':         forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 76543210'}),
            'email':            forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
            'direccion':        forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'abogado_asignado': forms.Select(attrs={'class': 'form-select'}),
            'notas_internas':   forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                'placeholder': 'Notas internas (no visibles al cliente)'}),
        }


# ── Formulario de Expediente ──────────────────
class ExpedienteForm(forms.ModelForm):
    class Meta:
        model  = Expediente
        fields = ['numero_expediente', 'nurej', 'juzgado', 'materia',
                  'tipo_proceso', 'descripcion', 'abogado_asignado', 'estado', 'fecha_conclusion']
        widgets = {
            'numero_expediente': forms.TextInput(attrs={'class': 'form-control'}),
            'nurej':             forms.TextInput(attrs={'class': 'form-control'}),
            'juzgado':           forms.TextInput(attrs={'class': 'form-control'}),
            'materia':           forms.Select(attrs={'class': 'form-select'}),
            'tipo_proceso':      forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion':       forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'abogado_asignado':  forms.Select(attrs={'class': 'form-select'}),
            'estado':            forms.Select(attrs={'class': 'form-select'}),
            'fecha_conclusion':  forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


# ── Formulario de Documento (con validación de archivo) ──
class DocumentoForm(forms.ModelForm):
    class Meta:
        model  = Documento
        fields = ['titulo', 'tipo', 'archivo', 'descripcion']
        widgets = {
            'titulo':      forms.TextInput(attrs={'class': 'form-control'}),
            'tipo':        forms.Select(attrs={'class': 'form-select'}),
            'archivo':     forms.FileInput(attrs={
                               'class': 'form-control',
                               'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.zip',
                           }),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def clean_archivo(self):
        archivo = self.cleaned_data.get('archivo')
        if not archivo:
            return archivo
        nombre = archivo.name.lower()
        aceptados = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.zip']
        if not any(nombre.endswith(ext) for ext in aceptados):
            raise ValidationError('Formato no permitido. Usa PDF, DOC, DOCX, JPG, PNG o ZIP.')
        if archivo.size > 10 * 1024 * 1024:
            raise ValidationError('El archivo es demasiado grande. El límite es 10 MB.')
        return archivo


# ── Formulario de Movimiento ──────────────────
class MovimientoForm(forms.ModelForm):
    class Meta:
        model  = Movimiento
        fields = ['tipo', 'fecha', 'descripcion']
        widgets = {
            'tipo':        forms.Select(attrs={'class': 'form-select'}),
            'fecha':       forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# ── CasoForm (compatibilidad con vistas antiguas) ─
class CasoForm(forms.ModelForm):
    class Meta:
        model  = Expediente
        fields = ['numero_expediente', 'nurej', 'materia', 'descripcion', 'estado']
        widgets = {
            'numero_expediente': forms.TextInput(attrs={'class': 'form-control'}),
            'nurej':             forms.TextInput(attrs={'class': 'form-control'}),
            'materia':           forms.Select(attrs={'class': 'form-select'}),
            'descripcion':       forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estado':            forms.Select(attrs={'class': 'form-select'}),
        }

# ── Formulario de Evento (Agenda) ─────────────────────────────
class EventoForm(forms.ModelForm):
    class Meta:
        model  = Evento
        fields = ['titulo', 'tipo', 'expediente', 'fecha_hora',
                  'modalidad', 'lugar', 'enlace_virtual', 'descripcion']
        widgets = {
            'titulo':         forms.TextInput(attrs={'class': 'form-control'}),
            'tipo':           forms.Select(attrs={'class': 'form-select'}),
            'expediente':     forms.Select(attrs={'class': 'form-select'}),
            'fecha_hora':     forms.DateTimeInput(
                                  attrs={'class': 'form-control', 'type': 'datetime-local'},
                                  format='%Y-%m-%dT%H:%M'),
            'modalidad':      forms.Select(attrs={'class': 'form-select'}),
            'lugar':          forms.TextInput(attrs={'class': 'form-control',
                                  'placeholder': 'Ej: Juzgado 3ro Civil, Sala 2'}),
            'enlace_virtual': forms.URLInput(attrs={'class': 'form-control',
                                  'placeholder': 'https://meet.google.com/...'}),
            'descripcion':    forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo muestra expedientes activos en el selector
        self.fields['expediente'].queryset = Expediente.objects.filter(
            activo=True).select_related('cliente').order_by('cliente__nombre_completo')
        self.fields['expediente'].empty_label = "— Sin expediente específico —"
        # Formato correcto para datetime-local
        if self.instance and self.instance.pk and self.instance.fecha_hora:
            self.initial['fecha_hora'] = self.instance.fecha_hora.strftime('%Y-%m-%dT%H:%M')

# ── Formulario de Tarea ───────────────────────
class TareaForm(forms.ModelForm):
    class Meta:
        model  = Tarea
        fields = ['titulo', 'descripcion', 'expediente', 'asignada_a',
                  'prioridad', 'estado', 'fecha_limite',
                  'horas_estimadas', 'es_recurrente', 'frecuencia_recurrencia']
        widgets = {
            'titulo':       forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion':  forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'expediente':   forms.Select(attrs={'class': 'form-select'}),
            'asignada_a':   forms.Select(attrs={'class': 'form-select'}),
            'prioridad':    forms.Select(attrs={'class': 'form-select'}),
            'estado':       forms.Select(attrs={'class': 'form-select'}),
            'fecha_limite': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'horas_estimadas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0', 'placeholder': 'ej. 2.5'}),
            'es_recurrente': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'frecuencia_recurrencia': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['expediente'].queryset = Expediente.objects.filter(
            activo=True).select_related('cliente').order_by('cliente__nombre_completo')
        self.fields['expediente'].empty_label = "— Sin expediente específico —"
        self.fields['asignada_a'].queryset = User.objects.filter(is_active=True).order_by('first_name')
        self.fields['frecuencia_recurrencia'].required = False

# ── Formulario de Evidencia ───────────────────
class EvidenciaForm(forms.ModelForm):
    class Meta:
        model  = EvidenciaTarea
        fields = ['archivo', 'descripcion']
        widgets = {
            'archivo':     forms.FileInput(attrs={
                               'class': 'form-control',
                               'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.zip',
                           }),
            'descripcion': forms.TextInput(attrs={
                               'class': 'form-control',
                               'placeholder': 'Descripción breve de la evidencia',
                           }),
        }

# ── Formulario de Plantilla ───────────────────
class PlantillaContratoForm(forms.ModelForm):
    class Meta:
        model  = PlantillaContrato
        fields = ['nombre', 'tipo', 'contenido']
        widgets = {
            'nombre':    forms.TextInput(attrs={'class': 'form-control'}),
            'tipo':      forms.Select(attrs={'class': 'form-select'}),
            'contenido': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 20,
                'style': 'font-family: monospace; font-size: .85rem;',
                'placeholder': (
                    "Escribe aquí el texto del contrato.\n\n"
                    "Variables disponibles:\n"
                    "{{cliente_nombre}} — Nombre completo del cliente\n"
                    "{{cliente_ci}}     — Cédula de identidad\n"
                    "{{cliente_direccion}} — Dirección del cliente\n"
                    "{{abogado_nombre}} — Nombre del abogado\n"
                    "{{fecha_hoy}}      — Fecha actual\n"
                    "{{expediente_nurej}} — NUREJ del expediente\n"
                    "{{monto}}          — Monto en Bs.\n"
                    "{{ciudad}}         — Ciudad"
                )
            }),
        }


# ── Formulario para generar contrato ─────────
class GenerarContratoForm(forms.ModelForm):
    plantilla = forms.ModelChoiceField(
        queryset=PlantillaContrato.objects.filter(activa=True),
        required=False,
        empty_label="— Escribir contrato manualmente —",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Usar plantilla"
    )

    class Meta:
        model  = Contrato
        fields = ['titulo', 'plantilla', 'cliente', 'expediente', 'monto', 'ciudad', 'contenido_final']
        widgets = {
            'titulo':          forms.TextInput(attrs={'class': 'form-control'}),
            'cliente':         forms.Select(attrs={'class': 'form-select'}),
            'expediente':      forms.Select(attrs={'class': 'form-select'}),
            'monto':           forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 1500.00'}),
            'ciudad':          forms.TextInput(attrs={'class': 'form-control'}),
            'contenido_final': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 20,
                'style': 'font-family: monospace; font-size: .85rem;',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].queryset = Cliente.objects.filter(activo=True).order_by('nombre_completo')
        self.fields['expediente'].queryset = Expediente.objects.filter(activo=True).select_related('cliente')
        self.fields['expediente'].empty_label = "— Sin expediente específico —"
        self.fields['contenido_final'].required = False

class ComentarioTareaForm(forms.ModelForm):
    class Meta:
        model  = ComentarioTarea
        fields = ['texto']
        widgets = {
            'texto': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Escribe un comentario o avance…',
            }),
        }
        labels = {'texto': ''}