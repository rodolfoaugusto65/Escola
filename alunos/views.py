from django.shortcuts import render, get_object_or_404, redirect
from .models import Aluno
from turmas.models import Turma
from .forms import AlunoForm
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

def lista_alunos(request):
    alunos = Aluno.objects.all().order_by('nome')
    return render(request, 'alunos/lista_alunos.html', {'alunos': alunos})

def cadastrar_aluno(request):

    if request.method == 'POST':
        form = AlunoForm(request.POST)

        if form.is_valid():
            aluno = form.save()

            if request.user.is_authenticated:
                aluno.criado_por = request.user
                aluno.atualizado_por = request.user
                aluno.save(update_fields=["criado_por", "atualizado_por"])

            messages.success(request, "Aluno cadastrado com sucesso!")
            return redirect('lista_alunos')

        else:
            messages.error(request, "Corrija os erros antes de salvar.")

    else:
        form = AlunoForm()

    return render(request, 'alunos/cadastrar_aluno.html', {'form': form})


def editar_aluno(request, id):

    aluno = get_object_or_404(Aluno, id=id)

    if request.method == 'POST':
        form = AlunoForm(request.POST, instance=aluno)

        if form.is_valid():
            aluno = form.save(commit=False)

            if request.user.is_authenticated:
                aluno.atualizado_por = request.user

            aluno.save()

            messages.success(request, "Aluno atualizado com sucesso!")
            return redirect('lista_alunos')

        else:
            messages.error(request, "Corrija os erros antes de salvar.")

    else:
        form = AlunoForm(instance=aluno)

    return render(request, 'alunos/cadastrar_aluno.html', {
        'form': form,
        'aluno': aluno
    })


@require_POST
@login_required
def excluir_aluno(request, pk):
    try:
        aluno = Aluno.objects.get(pk=pk)
        aluno.delete()

        return JsonResponse({
            "success": True,
            "message": "Aluno excluído com sucesso!"
        })

    except Aluno.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Aluno não encontrado."
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": "Erro interno ao excluir."
        })

def relatorio_aluno_completo(request, aluno_id):
    aluno = get_object_or_404(Aluno, id=aluno_id)
    return render(request, 'alunos/relatorio_aluno_completo.html', {
        'aluno': aluno
    })

def relatorio_alunos(request):

    alunos = Aluno.objects.all()

    # =========================
    # FILTRO TEXTO
    # =========================
    query = request.GET.get('q')
    tipo = request.GET.get('tipo')

    if query:
        if tipo == 'matricula':
            alunos = alunos.filter(matricula__icontains=query)
        else:
            alunos = alunos.filter(nome__icontains=query)

    # =========================
    # FILTRO TURMA
    # =========================
    turma_id = request.GET.get('turma')
    if turma_id:
        alunos = alunos.filter(turma_id=turma_id)

    # =========================
    # FILTROS BOOLEANOS
    # =========================
    if request.GET.get('dependencia') == '1':
        alunos = alunos.filter(possui_dependencia=True)

    if request.GET.get('trabalhador') == '1':
        alunos = alunos.filter(aluno_trabalhador=True)

    if request.GET.get('paed') == '1':
        alunos = alunos.filter(aluno_paed=True)

    if request.GET.get('transferido') == '1':
        alunos = alunos.filter(transferido=True)

    # =========================
    # CONTADORES
    # =========================
    total = alunos.count()
    total_paed = alunos.filter(aluno_paed=True).count()
    total_dependencia = alunos.filter(possui_dependencia=True).count()
    total_transferidos = alunos.filter(transferido=True).count()

    turmas = Turma.objects.all().order_by('ano_letivo')

    return render(request, 'alunos/relatorio_alunos.html', {
        'alunos': alunos.order_by('nome'),
        'turmas': turmas,
        'total': total,
        'total_paed': total_paed,
        'total_dependencia': total_dependencia,
        'total_transferidos': total_transferidos
    })