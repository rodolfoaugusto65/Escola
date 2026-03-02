from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Turma
from .forms import TurmaForm
from core.utils import render_smart

@login_required
def lista_turmas(request):
    turmas = Turma.objects.all()

    context = {
        'turmas': turmas
    }

    template, context = render_smart(
        request,
        'turmas/lista_turmas.html',
        context
    )

    return render(request, template, context)


@login_required
def cadastrar_turma(request):
    form = TurmaForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Turma cadastrada com sucesso!")
            return redirect('lista_turmas')
        else:
            messages.error(request, "Erro ao cadastrar turma. Verifique os campos.")

    return render(request, 'turmas/cadastrar_turma.html', {'form': form})


@login_required
def editar_turma(request, id):
    turma = get_object_or_404(Turma, id=id)
    form = TurmaForm(request.POST or None, instance=turma)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Turma atualizada com sucesso!")
            return redirect('lista_turmas')
        else:
            messages.error(request, "Erro ao atualizar turma.")

    return render(request, 'turmas/editar_turma.html', {'form': form, 'turma': turma})


@login_required
def excluir_turma(request, id):
    turma = get_object_or_404(Turma, id=id)

    if request.method == 'POST':
        turma.delete()
        messages.success(request, "Turma excluída com sucesso!")
        return redirect('lista_turmas')

    messages.error(request, "Método inválido para exclusão.")
    return redirect('lista_turmas')


@login_required
def relatorio_turmas(request):
    turmas = Turma.objects.all()
    return render(request, 'turmas/relatorio_turmas.html', {'turmas': turmas})