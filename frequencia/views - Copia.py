from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from alunos.models import Aluno
from .models import Frequencia, FrequenciaAluno
from .forms import FrequenciaForm
from django.db.models import Count, Q

@login_required
def lista_frequencias(request):
    frequencias = (
        Frequencia.objects
        .select_related('turma')
        .annotate(
            total_alunos=Count('registros'),
            presentes=Count('registros', filter=Q(registros__presente=True)),
            faltas=Count('registros', filter=Q(registros__presente=False)),
        )
        .order_by('-data')
    )

    return render(
        request,
        'frequencia/lista.html',
        {'frequencias': frequencias}
    )



@login_required
def criar_frequencia(request):
    alunos = []
    turma_id = request.GET.get("turma")

    form = FrequenciaForm(request.POST or None)

    if turma_id:
        alunos = Aluno.objects.filter(turma_id=turma_id).order_by("nome")

        # Pré-seleciona a turma no formulário
        form.fields["turma"].initial = turma_id

    if request.method == "POST" and form.is_valid():
        frequencia = form.save()

        for aluno in alunos:
            presente = request.POST.get(f"presente_{aluno.id}") == "on"
            FrequenciaAluno.objects.create(
                frequencia=frequencia,
                aluno=aluno,
                presente=presente
            )

        return redirect("lista_frequencia")

    return render(
        request,
        "frequencia/criar.html",
        {
            "form": form,
            "alunos": alunos,
        }
    )



@login_required
def detalhe_frequencia(request, pk):
    frequencia = get_object_or_404(Frequencia, pk=pk)
    registros = frequencia.registros.select_related('aluno')

    return render(
        request,
        'frequencia/detalhe.html',
        {
            'frequencia': frequencia,
            'registros': registros
        }
    )



@login_required
def relatorios_frequencia(request):
    frequencias = Frequencia.objects.select_related('turma')
    return render(request, 'frequencia/relatorios.html', {
        'frequencias': frequencias
    })


@login_required
def imprimir_frequencia(request, pk):
    frequencia = get_object_or_404(Frequencia, pk=pk)
    registros = frequencia.registros.select_related('aluno')

    return render(
        request,
        'frequencia/imprimir.html',
        {
            'frequencia': frequencia,
            'registros': registros
        }
    )
