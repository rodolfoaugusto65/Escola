from django import forms
from .models import ConselhoClasse


class ConselhoForm(forms.ModelForm):

    BIMESTRES = [
        (1, "1º Bimestre"),
        (2, "2º Bimestre"),
        (3, "3º Bimestre"),
        (4, "4º Bimestre"),
    ]

    ANOS = [(ano, str(ano)) for ano in range(2024, 2036)]

    bimestre = forms.TypedChoiceField(
        choices=[("", "Selecione...")] + BIMESTRES,
        coerce=int
    )

    ano = forms.TypedChoiceField(
        choices=[("", "Selecione...")] + ANOS,
        coerce=int
    )

    class Meta:
        model = ConselhoClasse
        fields = ["turma", "bimestre", "ano"]