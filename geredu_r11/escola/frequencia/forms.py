from django import forms
from .models import Frequencia


class FrequenciaForm(forms.ModelForm):

    class Meta:
        model = Frequencia
        fields = ['turma', 'data']

        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'})
        }