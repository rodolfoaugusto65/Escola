from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from datetime import datetime
from core.utils import render_smart
from .models import Frequencia, FrequenciaAluno
from alunos.models import Aluno
from turmas.models import Turma


def frequencia_aluno(request, aluno_id):
    aluno = get_object_or_404(Aluno, id=aluno_id)

    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    registros = FrequenciaAluno.objects.filter(aluno=aluno)

    if data_inicio:
        registros = registros.filter(frequencia__data__gte=data_inicio)

    if data_fim:
        registros = registros.filter(frequencia__data__lte=data_fim)

    total = registros.count()
    presencas = registros.filter(presente=True).count()
    faltas = total - presencas

    contexto = {
        'aluno': aluno,
        'registros': registros.select_related('frequencia', 'frequencia__turma'),
        'total': total,
        'presencas': presencas,
        'faltas': faltas,
        'percentual': (presencas / total * 100) if total else 0,
        'filtros': request.GET
    }

    return render(request, 'frequencia/aluno.html', contexto)


@login_required
def lista_frequencias(request):
    turmas = Turma.objects.all()
    alunos = Aluno.objects.all()

    turma_id = request.GET.get('turma')
    aluno_q = request.GET.get('aluno')
    data_ini = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    registros = FrequenciaAluno.objects.select_related(
        'aluno', 'frequencia', 'frequencia__turma'
    )

    if turma_id:
        registros = registros.filter(frequencia__turma_id=turma_id)

    if aluno_q:
        registros = registros.filter(
            Q(aluno__nome__icontains=aluno_q) |
            Q(aluno__matricula__icontains=aluno_q)
        )

    if data_ini and data_fim:
        registros = registros.filter(
            frequencia__data__range=[data_ini, data_fim]
        )

    resumo = registros.values(
        'aluno__id',
        'aluno__nome',
        'aluno__matricula'
    ).annotate(
        presencas=Count('id', filter=Q(presente=True)),
        faltas=Count('id', filter=Q(presente=False)),
        total=Count('id')
    )

    for r in resumo:
        r['percentual'] = (
            (r['presencas'] / r['total']) * 100 if r['total'] else 0
        )

    contexto = {
        'turmas': turmas,
        'alunos': alunos,
        'resumo': resumo,
        'request': request
    }

    template, contexto = render_smart(
        request,
        'frequencia/lista.html',
        contexto
    )

    return render(request, template, contexto)


@login_required
def criar_frequencia(request):
    turmas = Turma.objects.all()
    alunos = []

    turma_id = request.GET.get('turma')
    data = request.GET.get('data')

    if turma_id:
        alunos = Aluno.objects.filter(turma_id=turma_id)

    if request.method == 'POST':
        turma_id = request.POST.get('turma')
        data = request.POST.get('data')

        if not turma_id or not data:
            return redirect(f'/frequencia/lancar/?turma={turma_id}&data={data}')

        turma = get_object_or_404(Turma, id=turma_id)
        data = datetime.strptime(data, '%Y-%m-%d').date()

        frequencia, _ = Frequencia.objects.get_or_create(
            turma=turma,
            data=data
        )

        for aluno in alunos:
            presente = request.POST.get(f'presente_{aluno.id}') == 'on'
            FrequenciaAluno.objects.update_or_create(
                frequencia=frequencia,
                aluno=aluno,
                defaults={'presente': presente}
            )

        return redirect('lista_frequencia')

    return render(request, 'frequencia/criar.html', {
        'turmas': turmas,
        'alunos': alunos,
        'turma_id': turma_id,
        'data': data
    })


@login_required
def detalhe_frequencia(request, pk):
    frequencia = get_object_or_404(Frequencia, pk=pk)
    registros = frequencia.registros.select_related('aluno')

    return render(request, 'frequencia/detalhe.html', {
        'frequencia': frequencia,
        'registros': registros
    })


@login_required
def imprimir_frequencia(request):
    turma = request.GET.get('turma')
    aluno = request.GET.get('aluno')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    registros = FrequenciaAluno.objects.select_related(
        'aluno', 'frequencia', 'frequencia__turma'
    )

    if turma:
        registros = registros.filter(frequencia__turma_id=turma)

    if aluno:
        registros = registros.filter(
            Q(aluno__nome__icontains=aluno) |
            Q(aluno__matricula__icontains=aluno)
        )

    if data_inicio and data_fim:
        registros = registros.filter(frequencia__data__range=[data_inicio, data_fim])

    return render(request, 'frequencia/imprimir.html', {
        'registros': registros,
        'filtros': request.GET
    })


def frequencia_imprimir(request):
    turma = request.GET.get('turma')
    aluno = request.GET.get('aluno')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    registros = Frequencia.objects.all()

    if turma:
        registros = registros.filter(turma_id=turma)

    if aluno:
        registros = registros.filter(aluno__nome__icontains=aluno)

    if data_inicio:
        registros = registros.filter(data__gte=data_inicio)

    if data_fim:
        registros = registros.filter(data__lte=data_fim)

    return render(request, 'frequencia/imprimir.html', {
        'registros': registros
    })


@login_required
def imprimir_relatorio(request):
    # mesma lógica da lista_frequencias
    # renderiza template limpo para impressão
    return render(request, 'frequencia/imprimir.html', contexto)



@login_required
def relatorios_frequencia(request):
    return lista_frequencias(request)


@login_required
def frequencia_detalhada(request):
    turma = request.GET.get('turma')
    aluno = request.GET.get('aluno')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    registros = FrequenciaAluno.objects.select_related(
        'aluno', 'frequencia', 'frequencia__turma'
    )

    if turma:
        registros = registros.filter(frequencia__turma_id=turma)

    if aluno:
        registros = registros.filter(
            Q(aluno__nome__icontains=aluno) |
            Q(aluno__matricula__icontains=aluno)
        )

    if data_inicio and data_fim:
        registros = registros.filter(
            frequencia__data__range=[data_inicio, data_fim]
        )

    datas = sorted(set(r.frequencia.data for r in registros))

    alunos = {}
    for r in registros:
        alunos.setdefault(r.aluno, {})[r.frequencia.data] = r.presente

    return render(request, 'frequencia/detalhado.html', {
        'alunos': alunos,
        'datas': datas,
        'turmas': Turma.objects.all(),
        'filtros': request.GET
    })


#@login_required
#def lista_lancamentos(request):
    #lancamentos = Frequencia.objects.select_related('turma').order_by('-data')
    #
    #turma = request.GET.get('turma')
    #data_inicio = request.GET.get('data_inicio')
    #data_fim = request.GET.get('data_fim')
    #
    #if turma:
     #   lancamentos = lancamentos.filter(turma_id=turma)
     #
    #if data_inicio and data_fim:
     #   lancamentos = lancamentos.filter(data__range=[data_inicio, data_fim])
     #
    #return render(request, 'frequencia/lancamentos.html', {
   #     'lancamentos': lancamentos,
  #      'turmas': Turma.objects.all()
 #   })

@login_required
def lista_lancamentos(request):
    frequencias = (
        Frequencia.objects
        .select_related('turma')
        .prefetch_related('registros')
        .order_by('-data')
    )

    return render(request, 'frequencia/lancamentos.html', {
        'frequencias': frequencias
    })


@login_required
def editar_frequencia(request, pk):
    frequencia = get_object_or_404(Frequencia, pk=pk)

    if request.method == 'POST':
        form = FrequenciaForm(request.POST, instance=frequencia)
        if form.is_valid():
            form.save()
            messages.success(request, 'Frequência atualizada com sucesso.')
            return redirect('lista_lancamentos')
    else:
        form = FrequenciaForm(instance=frequencia)

    return render(request, 'frequencia/editar.html', {
        'form': form,
        'frequencia': frequencia
    })


@login_required
def excluir_frequencia(request, pk):
    frequencia = get_object_or_404(Frequencia, pk=pk)

    if request.method == 'POST':
        frequencia.delete()
        messages.success(request, 'Frequência excluída com sucesso.')
        return redirect('lista_lancamentos')

    return render(request, 'frequencia/excluir.html', {
        'frequencia': frequencia
    })
