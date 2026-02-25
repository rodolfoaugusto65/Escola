from django import forms
from .models import Aluno
from django.utils import timezone


class AlunoForm(forms.ModelForm):
    class Meta:
        model = Aluno
        fields = [
            'matricula', 'nome', 'data_nascimento', 'data_matricula', 'turma', 'email',
            'nome_pai', 'nome_mae', 'telefone_responsavel', 'nome_telefone_responsavel',
            'telefone_responsavel2', 'nome_telefone_responsavel2',

            # 🔹 INDICADORES ADMINISTRATIVOS (ADICIONADOS)
            'recomposicao',
            'possui_dependencia',
            'aluno_trabalhador',

            # 🔹 PROGRAMAS
            'aluno_paed', 'observacao_paed',
            'aluno_busca_ativa', 'numero_ficai',

            # 🔹 SITUAÇÃO
            'transferido', 'data_transferencia',
        ]

        labels = {
            'matricula': 'Matrícula',
            'nome': 'Nome Completo',
            'data_nascimento': 'Data de Nascimento',
            'data_matricula': 'Data da Matrícula',
            'turma': 'Turma',
            'email': 'E-mail do Aluno',
            'nome_pai': 'Nome do Pai',
            'nome_mae': 'Nome da Mãe',
            'telefone_responsavel': 'Telefone Responsável 1',
            'nome_telefone_responsavel': 'Nome do Responsável 1',
            'telefone_responsavel2': 'Telefone Responsável 2',
            'nome_telefone_responsavel2': 'Nome do Responsável 2',

            # 🔹 INDICADORES
            'recomposicao': 'Em Recomposição de Aprendizagem',
            'possui_dependencia': 'Aluno com Dependência',
            'aluno_trabalhador': 'Aluno Trabalhador / Estagiário / Menor Aprendiz',

            # 🔹 PROGRAMAS
            'aluno_paed': 'Aluno PAED',
            'observacao_paed': 'Informações sobre PAED',
            'aluno_busca_ativa': 'Aluno em Busca Ativa',
            'numero_ficai': 'Número da Ficha FICAI',

            # 🔹 SITUAÇÃO
            'transferido': 'Aluno Transferido',
            'data_transferencia': 'Data da Transferência',
        }

        widgets = {
            'data_nascimento': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'data_matricula': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'data_transferencia': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'observacao_paed': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control'}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        transferido = cleaned_data.get("transferido")
        data_transferencia = cleaned_data.get("data_transferencia")

        if transferido and not data_transferencia:
            raise forms.ValidationError("Informe a data da transferência.")

        if data_transferencia and data_transferencia > timezone.now().date():
            raise forms.ValidationError("A data da transferência não pode ser futura.")

        return cleaned_data

    def save(self, commit=True):
        aluno = super().save(commit=False)

        if aluno.turma:
            aluno.turma_ano_letivo = aluno.turma.ano_letivo
            aluno.turma_etapa = aluno.turma.etapa
            aluno.turma_ano_escolar = aluno.turma.ano_escolar
            aluno.turma_nome = aluno.turma.nome

        if commit:
            aluno.save()

        return aluno