from django import forms
from .models import AppModulo
from usuarios.models import Usuario


class AppModuloForm(forms.ModelForm):

    perfis_permitidos = forms.MultipleChoiceField(
        choices=Usuario.PERFIS,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = AppModulo
        fields = "__all__"
