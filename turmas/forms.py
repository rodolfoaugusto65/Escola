from django import forms
from .models import Turma
import re


class TurmaForm(forms.ModelForm):

    class Meta:
        model = Turma
        fields = [
            'ano_letivo',
            'etapa',
            'ano_escolar',
            'nome',
            'turno',
            'max_alunos',
            'professor_conselheiro',
            'aluno_lider'
        ]
        widgets = {
            'ano_letivo': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 2026'}),
            'etapa': forms.Select(attrs={'class': 'form-select'}),
            'ano_escolar': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 6º, 9º, 3º'}),
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: A, B, C, Alfa, Beta'}),
            'turno': forms.Select(attrs={'class': 'form-select'}),
            'max_alunos': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'professor_conselheiro': forms.Select(attrs={'class': 'form-select'}),
            'aluno_lider': forms.Select(attrs={'class': 'form-select'}),
        }

    # 🔹 Regra: Ano Escolar deve ser "número + º"
    def clean_ano_escolar(self):
        valor = self.cleaned_data['ano_escolar'].strip()

        if not re.fullmatch(r'\d+º', valor):
            raise forms.ValidationError(
                'Use apenas número seguido de º. Exemplo: 6º, 9º, 3º'
            )

        return valor

    # 🔹 Regra: Nome da turma deve ser apenas letra ou Alfa/Beta etc
    def clean_nome(self):
        valor = self.cleaned_data['nome'].strip()

        if not re.fullmatch(r'[A-Za-zÀ-ÿ]+', valor):
            raise forms.ValidationError(
                'Use apenas letras. Exemplo: A, B, C, Alfa, Beta'
            )

        return valor.capitalize()
