from django import forms
from .models import Frequencia


class FrequenciaForm(forms.ModelForm):
    class Meta:
        model = Frequencia
        fields = ['turma', 'data', 'observacao']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
            'observacao': forms.Textarea(attrs={'rows': 3}),
        }
