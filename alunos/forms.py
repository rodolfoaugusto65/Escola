from django import forms
from django.utils import timezone

from .models import Aluno, DocumentoAluno
import os
import uuid

class AlunoForm(forms.ModelForm):

    class Meta:
        model = Aluno


        fields = [
            'matricula', 'nome', 'data_nascimento', 'data_matricula', 'turma', 'email',

            'nome_pai', 'nome_mae',
            'telefone_responsavel', 'nome_telefone_responsavel',
            'telefone_responsavel2', 'nome_telefone_responsavel2',

            # FOTO
            'foto',

            # 🔹 INDICADORES ADMINISTRATIVOS
            'recomposicao',
            'possui_dependencia',
            'aluno_trabalhador',

            # 🔹 PROGRAMAS
            'aluno_paed',
            'observacao_paed',
            'aluno_busca_ativa',
            'numero_ficai',

            # 🔹 SITUAÇÃO
            'transferido',
            'data_transferencia',
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

            'foto': 'Foto do aluno',

            'recomposicao': 'Em Recomposição de Aprendizagem',
            'possui_dependencia': 'Aluno com Dependência',
            'aluno_trabalhador': 'Aluno Trabalhador / Estagiário / Menor Aprendiz',

            'aluno_paed': 'Aluno PAED',
            'observacao_paed': 'Informações sobre PAED',
            'aluno_busca_ativa': 'Aluno em Busca Ativa',
            'numero_ficai': 'Número da Ficha FICAI',

            'transferido': 'Aluno Transferido',
            'data_transferencia': 'Data da Transferência',
        }

        widgets = {

            'matricula': forms.TextInput(attrs={'class': 'form-control'}),
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),

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

            'turma': forms.Select(attrs={'class': 'form-select'}),

            'observacao_paed': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control'}
            ),

            "foto": forms.FileInput(attrs={
                "class": "form-control form-control-sm",
                "accept": "image/*"
            })
        }

    # =========================
    # VALIDAÇÕES
    # =========================

    def clean(self):

        cleaned_data = super().clean()

        transferido = cleaned_data.get("transferido")
        data_transferencia = cleaned_data.get("data_transferencia")

        if transferido and not data_transferencia:
            raise forms.ValidationError(
                "Informe a data da transferência."
            )

        if data_transferencia and data_transferencia > timezone.now().date():
            raise forms.ValidationError(
                "A data da transferência não pode ser futura."
            )

        return cleaned_data
    # =========================
    # VALIDAÇÃO DA FOTO
    # =========================

    def clean_foto(self):

        foto = self.cleaned_data.get("foto")

        # Se não enviou nova foto, não validar tamanho
        if not foto:
            return foto

        try:
            # Se for upload novo terá atributo size
            if hasattr(foto, "size") and foto.size > 5 * 1024 * 1024:
                raise forms.ValidationError(
                    "A foto deve ter no máximo 5MB."
                )

        except FileNotFoundError:
            # Caso o arquivo antigo tenha sido removido do storage
            return None

        return foto

    # =========================
    # SALVAR COM INFORMAÇÕES DA TURMA
    # =========================

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

        



# ==================================================
# FORMULÁRIO DE LAUDOS (PAED)
# ==================================================

class DocumentoAlunoForm(forms.ModelForm):

    arquivo = forms.FileField(required=False, allow_empty_file=True)

    class Meta:

        model = DocumentoAluno

        fields = [
            "tipo_laudo",
            "data_laudo",
            "descricao",
            "arquivo"
        ]

        widgets = {

            "tipo_laudo": forms.TextInput(
                attrs={"class": "form-control"}
            ),

            "data_laudo": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date"
                }
            ),

            "descricao": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3
                }
            ),

            "arquivo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "application/pdf"
                }
            )
        }

    # =========================
    # VALIDAR PDF
    # =========================

    def clean_arquivo(self):

        arquivo = self.cleaned_data.get("arquivo")

        if arquivo and arquivo.name and not arquivo.name.lower().endswith(".pdf"):
            raise forms.ValidationError(
                "Somente arquivos PDF são permitidos."
            )

        return arquivo
    
    def delete(self, *args, **kwargs):
        if self.arquivo:
            self.arquivo.delete(save=False)
    
        super().delete(*args, **kwargs)