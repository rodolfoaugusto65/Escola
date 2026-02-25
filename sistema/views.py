from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from usuarios.models import Usuario
from .models import AppModulo
from .forms import AppModuloForm


def somente_admin_coord(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.perfil not in ["ADMIN", "COORD"]:
            return redirect("lista_ocorrencias")
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@somente_admin_coord
def lista_modulos(request):
    modulos = AppModulo.objects.all()

    return render(request, "sistema/lista.html", {
        "modulos": modulos
    })


@login_required
@somente_admin_coord
def criar_modulo(request):
    form = AppModuloForm(request.POST or None)

    if form.is_valid():
        form.save()
        return redirect("lista_modulos")

    return render(request, "sistema/form.html", {"form": form})


@login_required
@somente_admin_coord
def editar_modulo(request, pk):
    modulo = get_object_or_404(AppModulo, pk=pk)
    form = AppModuloForm(request.POST or None, instance=modulo)

    if form.is_valid():
        form.save()
        return redirect("lista_modulos")

    return render(request, "sistema/form.html", {"form": form})
