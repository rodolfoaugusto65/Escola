from django import forms
from django.core.exceptions import ValidationError
from .models import Usuario
import re


# ======================================================
# 🧩 Função auxiliar para validar CPF
# ======================================================

def validar_cpf(cpf: str):
    """
    Valida o formato e os dígitos verificadores do CPF.
    Retorna o CPF limpo (somente números) se for válido.
    """
    cpf = re.sub(r'[^0-9]', '', cpf)

    if len(cpf) != 11 or cpf == cpf[0] * 11:
        raise ValidationError("CPF inválido.")

    soma1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = (soma1 * 10) % 11
    digito1 = 0 if digito1 == 10 else digito1

    soma2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = (soma2 * 10) % 11
    digito2 = 0 if digito2 == 10 else digito2

    if not (digito1 == int(cpf[9]) and digito2 == int(cpf[10])):
        raise ValidationError("CPF inválido.")

    return cpf


# ======================================================
# 🧾 FORMULÁRIO DE CADASTRO DE USUÁRIO
# ======================================================

class UsuarioForm(forms.ModelForm):

    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite uma senha segura'
        }),
        required=True
    )

    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'cpf', 'email', 'perfil', 'password']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Primeiro nome'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sobrenome'
            }),
            'cpf': forms.TextInput(attrs={
                'class': 'form-control cpf-mask',
                'placeholder': 'Digite o CPF'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'exemplo@dominio.com'
            }),
            'perfil': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf', '').strip()
        cpf = re.sub(r'[^0-9]', '', cpf)

        validar_cpf(cpf)

        if Usuario.objects.filter(cpf=cpf).exists():
            raise ValidationError("Já existe um usuário com este CPF.")

        return cpf

# ======================================================
# 👤 FORM PARA EDITAR PRÓPRIOS DADOS
# ======================================================

class EditarMeusDadosForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = [
            'first_name',
            'last_name',
            'email',
            'telefone',
            'endereco',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control telefone-mask'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control'}),
        }
# ======================================================
# ✏️ FORMULÁRIO DE EDIÇÃO DE USUÁRIO
# ======================================================

class EditarUsuarioForm(forms.ModelForm):
    """
    Formulário para edição de usuário com campo de status ativo/inativo.
    CPF é apenas leitura.
    """

    # Campo manual apenas leitura (mantém visualmente no form)
    perfil_gerencial = forms.BooleanField(
        label="Usuário com perfil gerencial",
        required=False,
        disabled=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'style': 'transform: scale(1.3); margin-top: 5px;',
            'title': 'Definido automaticamente pelo perfil'
        })
    )

    is_active = forms.BooleanField(
        label="Usuário Ativo",
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'style': 'transform: scale(1.3); margin-top: 5px;',
            'title': 'Ativar ou desativar este usuário'
        })
    )

    class Meta:
        model = Usuario
        # ⚠️ REMOVIDO do Meta.fields (mas mantido manualmente acima)
        fields = [
            'first_name',
            'last_name',
            'cpf',
            'email',
            'perfil',
            'telefone',
            'endereco',
            'is_active',
        ]

        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Primeiro nome'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sobrenome'
            }),
            'cpf': forms.TextInput(attrs={
                'class': 'form-control cpf-mask',
                'readonly': 'readonly',
                'title': 'O CPF não pode ser alterado'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'exemplo@dominio.com'
            }),
            'perfil': forms.Select(attrs={'class': 'form-select'}),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(65) 99999-9999'
            }),
            'endereco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Endereço completo'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Atualiza o valor automaticamente ao abrir o form
        if self.instance and self.instance.pk:
            self.fields['perfil_gerencial'].initial = self.instance.perfil_gerencial

    def clean_cpf(self):
        """
        Evita erro ao editar (CPF é fixo e não deve mudar).
        """
        return self.instance.cpf