from django import forms
from .models import Caso # Antes decía TuModelo, cámbialo a Caso

class CasoForm(forms.ModelForm):
    class Meta:
        model = Caso # Aquí también debe decir Caso
        fields = '__all__'
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'numero_caso': forms.TextInput(attrs={'class': 'form-control'}),
            'cliente': forms.TextInput(attrs={'class': 'form-control'}),
            'materia': forms.Select(attrs={'class': 'form-select'}),
            'juzgado': forms.TextInput(attrs={'class': 'form-control'}),
            'nurej': forms.TextInput(attrs={'class': 'form-control'}),
            'abogado_asignado': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }