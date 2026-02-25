from django import forms
from django.utils import timezone
from .models import Ocorrencia
from alunos.models import Aluno


class OcorrenciaForm(forms.ModelForm):

    # Campos extras/override do ModelForm
    data = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"})
    )

    ficai_data = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"})
    )

    class Meta:
        model = Ocorrencia
        exclude = ["codigo", "usuario", "criado_em"]

        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
            "ficai_data": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 🔥 DATA AUTOMÁTICA
        if not self.instance.pk:
            self.fields["data"].initial = timezone.now().date()

        if self.instance.pk and self.instance.data:
            self.initial["data"] = self.instance.data

        if self.instance.pk and getattr(self.instance, "ficai_data", None):
            self.initial["ficai_data"] = self.instance.ficai_data

        # 🔥 FILTRO DE ALUNOS POR TURMA

        # padrão: nenhum aluno
        self.fields["aluno"].queryset = Aluno.objects.none()

        # se estiver editando
        if self.instance.pk and self.instance.turma:
            self.fields["aluno"].queryset = Aluno.objects.filter(
                turma=self.instance.turma
            )

        # se veio turma do POST (criação)
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

        # 🔥 sincroniza turma com a turma atual do aluno
        if obj.aluno and obj.aluno.turma:
            obj.turma = obj.aluno.turma

        if commit:
            obj.save()

        return obj
