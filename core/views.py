from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .utils import render_smart

@login_required
def home_view(request):
    usuario = request.user

    contexto = {
        'nome_completo': usuario.get_full_name(),
        'perfil': usuario.get_perfil_display() if hasattr(usuario, 'get_perfil_display') else '',
        'cpf': usuario.cpf,
    }

    template, contexto = render_smart(request, "core/home.html", contexto)
    return render(request, template, contexto)


