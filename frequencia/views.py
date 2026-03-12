from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from core.utils import render_smart
from .models import Frequencia, FrequenciaAluno
from .forms import FrequenciaForm
from alunos.models import Aluno
from turmas.models import Turma


# =====================================================
# FREQUENCIA POR ALUNO
# =====================================================

@login_required
def frequencia_aluno(request, aluno_id):

    aluno = get_object_or_404(Aluno, id=aluno_id)

    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")

    registros = FrequenciaAluno.objects.filter(aluno=aluno)

    if data_inicio:
        registros = registros.filter(frequencia__data__gte=data_inicio)

    if data_fim:
        registros = registros.filter(frequencia__data__lte=data_fim)

    total = registros.count()
    presencas = registros.filter(presente=True).count()
    faltas = total - presencas

    contexto = {
        "aluno": aluno,
        "registros": registros.select_related("frequencia", "frequencia__turma"),
        "total": total,
        "presencas": presencas,
        "faltas": faltas,
        "percentual": (presencas / total * 100) if total else 0,
        "filtros": request.GET
    }

    return render(request, "frequencia/aluno.html", contexto)


# =====================================================
# DASHBOARD FREQUENCIA
# =====================================================

@login_required
def lista_frequencias(request):

    turmas = Turma.objects.all()

    turma_id = request.GET.get("turma")
    aluno_q = request.GET.get("aluno")
    data_ini = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")

    registros = FrequenciaAluno.objects.select_related(
        "aluno", "frequencia", "frequencia__turma"
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

    hoje = timezone.localdate()

    # =====================================================
    # RESUMO DO DIA
    # =====================================================

    registros_dia = FrequenciaAluno.objects.filter(
        frequencia__data=hoje
    )

    presencas_dia = registros_dia.filter(presente=True).count()
    faltas_dia = registros_dia.filter(presente=False).count()
    total_dia = registros_dia.count()

    turmas_dia = Frequencia.objects.filter(data=hoje).values(
        "turma"
    ).distinct().count()

    resumo_dia = {
        "data": hoje,
        "turmas": turmas_dia,
        "total_alunos": total_dia,
        "presencas": presencas_dia,
        "faltas": faltas_dia,
        "percentual": (presencas_dia / total_dia * 100) if total_dia else 0
    }

    # =====================================================
    # RESUMO POR TURMA
    # =====================================================

    resumo_turmas = registros.values(
        "frequencia__id",
        "frequencia__data",
        "frequencia__turma__id",
        "frequencia__turma__nome",
        "frequencia__turma__ano_escolar"
    ).annotate(
        presencas=Count("id", filter=Q(presente=True)),
        faltas=Count("id", filter=Q(presente=False)),
        total=Count("id")
    ).order_by("-frequencia__data")

    total_presencas = 0
    total_faltas = 0

    for r in resumo_turmas:

        r["percentual"] = (r["presencas"] / r["total"] * 100) if r["total"] else 0

        total_presencas += r["presencas"]
        total_faltas += r["faltas"]

    # =====================================================
    # GRAFICO DIA
    # =====================================================

    dados_dia = FrequenciaAluno.objects.filter(
        frequencia__data=hoje
    ).values(
        "frequencia__turma__nome",
        "frequencia__turma__ano_escolar"
    ).annotate(
        presencas=Count("id", filter=Q(presente=True)),
        faltas=Count("id", filter=Q(presente=False)),
        total=Count("id")
    )

    grafico_dia = {
        "labels": [
            f'{d["frequencia__turma__ano_escolar"]}{d["frequencia__turma__nome"]}'
            for d in dados_dia
        ],
        "presencas": [d["presencas"] for d in dados_dia],
        "faltas": [d["faltas"] for d in dados_dia],
        "percentual": [
            round((d["presencas"] / d["total"]) * 100, 1) if d["total"] else 0
            for d in dados_dia
        ]
    }
    # =====================================================
    # GRAFICO TURNO
    # =====================================================

    dados_turno = FrequenciaAluno.objects.values(
        "frequencia__turma__turno"
    ).annotate(
        presencas=Count("id", filter=Q(presente=True)),
        faltas=Count("id", filter=Q(presente=False))
    )

    grafico_turno = {
        "labels": [d["frequencia__turma__turno"] for d in dados_turno],
        "presencas": [d["presencas"] for d in dados_turno],
        "faltas": [d["faltas"] for d in dados_turno]
    }

    # =====================================================
    # GRAFICO SEMANA
    # =====================================================

    inicio_semana = hoje - timedelta(days=6)

    dados_semana = FrequenciaAluno.objects.filter(
        frequencia__data__range=[inicio_semana, hoje]
    ).values(
        "frequencia__data"
    ).annotate(
        presentes=Count("id", filter=Q(presente=True)),
        total=Count("id")
    ).order_by("frequencia__data")

    grafico_semana = {
        "labels": [d["frequencia__data"].strftime("%d/%m") for d in dados_semana],
        "presentes": [d["presentes"] for d in dados_semana],
        "percentual": [
            round((d["presentes"] / d["total"]) * 100, 1) if d["total"] else 0
            for d in dados_semana
        ]
    }

    contexto = {
        "turmas": turmas,
        "resumo_turmas": resumo_turmas,
        "resumo_dia": resumo_dia,
        "total_presencas": total_presencas,
        "total_faltas": total_faltas,
        "grafico_dia": grafico_dia,
        "grafico_turno": grafico_turno,
        "grafico_semana": grafico_semana,
        "request": request
    }

    template, contexto = render_smart(
        request,
        "frequencia/lista.html",
        contexto
    )

    return render(request, template, contexto)


# =====================================================
# CRIAR FREQUENCIA
# =====================================================

from django.utils import timezone

@login_required
def criar_frequencia(request):

    turmas = Turma.objects.all()

    turma_id = request.GET.get("turma")

    # define data padrão como hoje
    data = request.GET.get("data")
    if not data:
        data = timezone.localdate().isoformat()

    alunos = []

    if turma_id:
        alunos = Aluno.objects.filter(turma_id=turma_id).order_by("nome")

    if request.method == "POST":

        turma_id = request.POST.get("turma")
        data = request.POST.get("data")

        turma = get_object_or_404(Turma, id=turma_id)

        data = datetime.strptime(data, "%Y-%m-%d").date()

        frequencia, _ = Frequencia.objects.get_or_create(
            turma=turma,
            data=data
        )

        alunos = Aluno.objects.filter(turma_id=turma_id)

        for aluno in alunos:

            presente = request.POST.get(f"presente_{aluno.id}") == "on"

            FrequenciaAluno.objects.update_or_create(
                frequencia=frequencia,
                aluno=aluno,
                defaults={"presente": presente}
            )

        return redirect("lista_frequencia")

    return render(request, "frequencia/criar.html", {
        "turmas": turmas,
        "alunos": alunos,
        "turma_id": turma_id,
        "data": data
    })


# =====================================================
# EDITAR
# =====================================================
@login_required
def editar_frequencia(request, pk):

    frequencia = get_object_or_404(
        Frequencia.objects.select_related("turma"),
        pk=pk
    )

    registros = (
        FrequenciaAluno.objects
        .filter(frequencia=frequencia)
        .select_related("aluno")
        .order_by("aluno__nome")
    )

    if request.method == "POST":

        for r in registros:

            presente = request.POST.get(f"presente_{r.aluno.id}") == "on"

            r.presente = presente
            r.save()

        return redirect("lista_frequencia")

    form = FrequenciaForm(instance=frequencia)

    return render(request, "frequencia/editar.html", {
        "form": form,
        "frequencia": frequencia,
        "registros": registros
    })


# =====================================================
# EXCLUIR
# =====================================================

@login_required
def excluir_frequencia(request, pk):

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método inválido."})

    if not request.user.pode_gerenciar_usuarios:
        return JsonResponse({
            "success": False,
            "error": "Sem permissão."
        })

    frequencia = get_object_or_404(Frequencia, pk=pk)

    frequencia.delete()

    return JsonResponse({"success": True})

@login_required
def lista_lancamentos(request):

    frequencias = (
        Frequencia.objects
        .select_related("turma")
        .prefetch_related("registros")
        .order_by("-data")
    )

    return render(request, "frequencia/lancamentos.html", {
        "frequencias": frequencias
    })

@login_required
def detalhe_frequencia(request, pk):

    frequencia = get_object_or_404(Frequencia.objects.select_related("turma"), pk=pk)

    registros = (
        FrequenciaAluno.objects
        .filter(frequencia=frequencia)
        .select_related("aluno")
        .order_by("aluno__nome")
    )

    return render(request, "frequencia/detalhe.html", {
        "frequencia": frequencia,
        "registros": registros
    })

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
        registros = registros.filter(
            frequencia__data__range=[data_inicio, data_fim]
        )

    return render(request, 'frequencia/imprimir.html', {
        'registros': registros,
        'filtros': request.GET
    })


@login_required
def frequencia_por_aluno(request):

    turma = request.GET.get("turma")
    aluno = request.GET.get("aluno")

    registros = FrequenciaAluno.objects.select_related(
        "aluno",
        "frequencia",
        "frequencia__turma"
    )

    if turma:
        registros = registros.filter(aluno__turma_id=turma)

    if aluno:
        registros = registros.filter(
            Q(aluno__nome__icontains=aluno) |
            Q(aluno__matricula__icontains=aluno)
        )

    resumo = registros.values(
        "aluno__id",
        "aluno__nome",
        "aluno__matricula",
        "aluno__turma__nome"
    ).annotate(
        presencas=Count("id", filter=Q(presente=True)),
        faltas=Count("id", filter=Q(presente=False)),
        total=Count("id")
    )

    for r in resumo:
        r["percentual"] = (
            r["presencas"] / r["total"] * 100
            if r["total"] else 0
        )

    contexto = {
        "resumo": resumo,
        "turmas": Turma.objects.all(),
        "request": request
    }

    template, contexto = render_smart(
        request,
        "frequencia/por_aluno.html",
        contexto
    )

    return render(request, template, contexto)


@login_required
def frequencia_aluno(request, aluno_id):

    aluno = get_object_or_404(Aluno, id=aluno_id)

    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")

    registros = (
        FrequenciaAluno.objects
        .select_related("frequencia", "frequencia__turma")
        .filter(aluno=aluno)
        .order_by("-frequencia__data")
    )

    # FILTROS
    if data_inicio:
        registros = registros.filter(frequencia__data__gte=data_inicio)

    if data_fim:
        registros = registros.filter(frequencia__data__lte=data_fim)

    # RESUMO
    resumo = registros.aggregate(
        total=Count("id"),
        presencas=Count("id", filter=Q(presente=True)),
        faltas=Count("id", filter=Q(presente=False)),
    )

    total = resumo["total"] or 0
    presencas = resumo["presencas"] or 0
    faltas = resumo["faltas"] or 0

    percentual = (presencas / total * 100) if total else 0

    contexto = {
        "aluno": aluno,
        "registros": registros,
        "total": total,
        "presencas": presencas,
        "faltas": faltas,
        "percentual": percentual,
        "filtros": request.GET
    }

    # PADRÃO DO SISTEMA
    template, contexto = render_smart(
        request,
        "frequencia/aluno.html",
        contexto
    )

    return render(request, template, contexto)


@login_required
def frequencia_imprimir(request):

    aluno_id = request.GET.get("aluno")
    data_inicio = request.GET.get("data_inicio")
    data_fim = request.GET.get("data_fim")

    aluno = get_object_or_404(Aluno, id=aluno_id)

    registros = FrequenciaAluno.objects.filter(aluno=aluno).select_related(
        "frequencia",
        "frequencia__turma"
    )

    if data_inicio:
        registros = registros.filter(frequencia__data__gte=data_inicio)

    if data_fim:
        registros = registros.filter(frequencia__data__lte=data_fim)

    total = registros.count()
    presencas = registros.filter(presente=True).count()
    faltas = total - presencas

    contexto = {
        "aluno": aluno,
        "registros": registros,
        "total": total,
        "presencas": presencas,
        "faltas": faltas,
        "percentual": (presencas / total * 100) if total else 0,
    }

    return render(request, "frequencia/imprimir.html", contexto)