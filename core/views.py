from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def home_view(request):
    usuario = request.user
    contexto = {
        'nome_completo': usuario.get_full_name(),
        'perfil': usuario.get_perfil_display() if hasattr(usuario, 'get_perfil_display') else '',
        'cpf': usuario.cpf,
    }
    return render(request, 'core/home.html', contexto)


