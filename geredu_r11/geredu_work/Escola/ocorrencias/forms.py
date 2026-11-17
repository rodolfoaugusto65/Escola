from django import forms
from django.utils import timezone
from .models import Ocorrencia
from alunos.models import Aluno


class OcorrenciaForm(forms.ModelForm):

    data = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"},
            format="%Y-%m-%d"
        )
    )

    ficai_data = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={"type": "date"},
            format="%Y-%m-%d"
        )
    )

    class Meta:
        model = Ocorrencia
        exclude = ["codigo", "usuario", "criado_em"]

        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "ficai_data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 🔥 DATA AUTOMÁTICA
        if not self.instance.pk:
            self.fields["data"].initial = timezone.now().date()

        if self.instance.pk and self.instance.data:
            self.fields["data"].initial = self.instance.data

        if self.instance.pk and getattr(self.instance, "ficai_data", None):
            self.fields["ficai_data"].initial = self.instance.ficai_data

        # 🔥 FILTRO DE ALUNOS POR TURMA

        self.fields["aluno"].queryset = Aluno.objects.none()

        # edição
        if self.instance.pk and self.instance.turma:
            self.fields["aluno"].queryset = Aluno.objects.filter(
                turma=self.instance.turma
            )

        # criação via POST
        if "turma" in self.data:
            try:
                turma_id = int(self.data.get("turma"))
                self.fields["aluno"].queryset = Aluno.objects.filter(
                    turma_id=turma_id
                )
            except (ValueError, TypeError):
                pass

    def save(self, commit=True):
        obj = super().save(commit=False)

        # sincroniza turma com aluno
        if obj.aluno and obj.aluno.turma:
            obj.turma = obj.aluno.turma

        if commit:
            obj.save()

        return obj