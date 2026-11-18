from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.views.decorators.http import require_POST
from django.db import IntegrityError
from django.http import JsonResponse
from .forms import EditarMeusDadosForm
from .models import Usuario, PerfilAcesso
from .forms import UsuarioForm, EditarUsuarioForm
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from django.urls import reverse_lazy
from core.utils import render_smart

User = get_user_model()

# ======================================================
# 🔐 PERMISSÃO GERENCIAL
# ======================================================

def is_admin_ou_coord(user):
    return user.is_authenticated and user.pode_gerenciar_usuarios


# ======================================================
# 🔐 LOGIN (CPF)
# ======================================================

def login_view(request):
    if request.method == 'POST':
        cpf = request.POST.get('username')
        senha = request.POST.get('password')

        if cpf:
            cpf = ''.join(filter(str.isdigit, cpf))

        user = authenticate(request, username=cpf, password=senha)

        if user is not None:
            login(request, user)
            messages.success(request, f"Bem-vindo(a), {user.first_name}!")
            return redirect('home')
        else:
            messages.error(request, 'CPF ou senha incorretos.')

    return render(request, 'usuarios/login.html')


# ======================================================
# 🔐 LOGOUT
# ======================================================

def logout_view(request):
    logout(request)
    messages.info(request, "Você saiu do sistema.")
    return redirect('login')


# ======================================================
# 👤 PERFIL
# ======================================================

@login_required
def perfil_view(request):
    return render(request, 'usuarios/perfil.html', {'usuario': request.user})


# ======================================================
# ✏ EDITAR PRÓPRIOS DADOS
# ======================================================

@login_required
def editar_dados_view(request):
    user = request.user

    if request.method == 'POST':
        form = EditarMeusDadosForm(request.POST, instance=user)

        if form.is_valid():
            form.save()
            messages.success(request, 'Dados atualizados com sucesso!')
            return redirect('perfil')
        else:
            messages.error(request, 'Corrija os erros antes de salvar.')
    else:
        form = EditarMeusDadosForm(instance=user)

    return render(request, 'usuarios/editar_dados.html', {
        'form': form
    })


# ======================================================
# 🏢 LISTA GERENCIAL
# ======================================================



@login_required
@user_passes_test(is_admin_ou_coord)
def lista_usuarios_view(request):
    usuarios = Usuario.objects.all().order_by('first_name')

    contexto = {
        'usuarios': usuarios
    }

    template, contexto = render_smart(
        request,
        'usuarios/lista.html',
        contexto
    )

    return render(request, template, contexto)


# ======================================================
# ➕ CADASTRAR USUÁRIO
# ======================================================

@login_required
@user_passes_test(is_admin_ou_coord)
def cadastrar_usuario_view(request):

    if request.method == 'POST':
        form = UsuarioForm(request.POST)

        if form.is_valid():
            usuario = form.save(commit=False)

            usuario.username = ''.join(filter(str.isdigit, usuario.cpf))
            usuario.password = make_password(form.cleaned_data['password'])
            usuario.is_active = True

            usuario.save()

            messages.success(
                request,
                f'Usuário {usuario.get_full_name()} cadastrado com sucesso!'
            )

            return redirect('lista_usuarios')
    else:
        form = UsuarioForm()

    return render(request, 'usuarios/form.html', {
        'form': form,
        'titulo': 'Cadastrar Usuário'
    })


# ======================================================
# ✏ EDITAR USUÁRIO
# ======================================================

@login_required
@user_passes_test(is_admin_ou_coord)
def editar_usuario_view(request, pk):

    usuario = get_object_or_404(Usuario, pk=pk)

    if request.method == 'POST':
        form = EditarUsuarioForm(request.POST, instance=usuario)
        if not request.user.is_superuser:
            form.fields.pop("is_superuser", None)

        if form.is_valid():
            form.save()

            if request.user.pk == usuario.pk:
                update_session_auth_hash(request, usuario)

            status_txt = "ativo" if usuario.is_active else "inativo"

            messages.success(
                request,
                f"Usuário {usuario.get_full_name()} atualizado com sucesso! (Status: {status_txt})"
            )

            return redirect('lista_usuarios')
        else:
            messages.error(request, "Verifique os campos e tente novamente.")
    else:
        form = EditarUsuarioForm(instance=usuario)
        if not request.user.is_superuser:
            form.fields.pop("is_superuser", None)

    return render(request, 'usuarios/form.html', {
        'form': form,
        'titulo': 'Editar Usuário'
    })


# ======================================================
# 🔄 ALTERAR STATUS
# ======================================================

@login_required
@user_passes_test(is_admin_ou_coord)
@require_POST
def alternar_status_usuario(request, pk):

    usuario = get_object_or_404(Usuario, pk=pk)
    usuario.is_active = not usuario.is_active
    usuario.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'Status de {usuario.get_full_name()} atualizado com sucesso.',
            'new_status': usuario.is_active
        })

    messages.success(
        request,
        f'Status de {usuario.get_full_name()} atualizado.'
    )

    return redirect('lista_usuarios')


# ======================================================
# 🔑 RESETAR SENHA
# ======================================================

@login_required
@user_passes_test(is_admin_ou_coord)
@require_POST
def resetar_senha_usuario(request, pk):

    usuario = get_object_or_404(Usuario, pk=pk)

    nova_senha = "123456"
    usuario.password = make_password(nova_senha)
    usuario.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'Senha de {usuario.get_full_name()} redefinida para 123456.'
        })

    messages.success(
        request,
        f'🔑 A senha de {usuario.get_full_name()} foi redefinida.'
    )

    return redirect('lista_usuarios')


# ======================================================
# ❌ EXCLUIR USUÁRIO
# ======================================================

@login_required
@user_passes_test(is_admin_ou_coord)
@require_POST
def excluir_usuario(request, pk):

    usuario = get_object_or_404(User, pk=pk)

    if usuario.pk == request.user.pk:
        msg = "Você não pode excluir o seu próprio usuário."

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': msg}, status=400)

        messages.error(request, msg)
        return redirect('lista_usuarios')

    nome = usuario.get_full_name() or usuario.username

    try:
        usuario.delete()

    except IntegrityError:
        msg = "Não foi possível excluir o usuário por dependências no banco."

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': msg}, status=400)

        messages.error(request, msg)
        return redirect('lista_usuarios')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'Usuário {nome} excluído.'
        })

    messages.success(request, f"🗑️ Usuário {nome} foi excluído com sucesso.")
    return redirect('lista_usuarios')

#
# Editar sua Senha 
#

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'usuarios/mudar_senha.html'   # 👈 AQUI
    success_url = reverse_lazy('password_change_done')

    def form_valid(self, form):
        messages.success(self.request, 'Senha alterada com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao alterar senha. Verifique os campos.')
        return super().form_invalid(form)


class CustomPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = 'usuarios/password_change_done.html'

# Administração da matriz de perfis: restrita exclusivamente a superusuários.
from django.contrib.auth.decorators import user_passes_test as _user_passes_test
from django import forms as _forms
from django.db import transaction as _transaction

class PerfilAcessoForm(_forms.ModelForm):
    permissoes = _forms.MultipleChoiceField(choices=PerfilAcesso.AREAS, required=False, widget=_forms.CheckboxSelectMultiple)
    class Meta:
        model = PerfilAcesso
        fields = ("codigo", "nome", "descricao", "permissoes", "ativo")
        widgets = {"codigo": _forms.TextInput(attrs={"class":"form-control"}), "nome": _forms.TextInput(attrs={"class":"form-control"}), "descricao": _forms.Textarea(attrs={"class":"form-control","rows":2}), "ativo": _forms.CheckboxInput(attrs={"class":"form-check-input"})}

@login_required
@_user_passes_test(lambda u: u.is_superuser)
def gerenciar_perfis_view(request):
    editar = get_object_or_404(PerfilAcesso, pk=request.GET.get("editar")) if request.GET.get("editar", "").isdigit() else None
    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "excluir":
            perfil = get_object_or_404(PerfilAcesso, pk=request.POST.get("perfil_id"))
            if Usuario.objects.filter(perfil=perfil.codigo).exists():
                messages.error(request, "Este perfil está atribuído a usuários. Desative-o em vez de excluir.")
            else:
                perfil.delete(); messages.success(request, "Perfil excluído.")
            return redirect("gerenciar_perfis")
        instance = get_object_or_404(PerfilAcesso, pk=request.POST.get("perfil_id")) if request.POST.get("perfil_id") else None
        form = PerfilAcessoForm(request.POST, instance=instance)
        if form.is_valid():
            perfil = form.save(commit=False); perfil.permissoes = form.cleaned_data["permissoes"]; perfil.save()
            messages.success(request, "Perfil salvo com sucesso."); return redirect("gerenciar_perfis")
    else:
        form = PerfilAcessoForm(instance=editar)
    return render(request, "usuarios/perfis.html", {"form":form,"perfis":PerfilAcesso.objects.all(),"editar":editar})
