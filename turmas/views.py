from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Turma
from .forms import TurmaForm
from core.utils import render_smart
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse



@login_required
def lista_turmas(request):

    turmas = Turma.objects.select_related("professor_conselheiro").all()

    # =========================
    # BUSCA
    # =========================

    busca = request.GET.get("busca")

    if busca:
        turmas = turmas.filter(
            Q(nome__icontains=busca) |
            Q(ano_escolar__icontains=busca) |
            Q(etapa__icontains=busca) |
            Q(turno__icontains=busca) |
            Q(ano_letivo__icontains=busca)
        )

    # =========================
    # FILTROS
    # =========================

    ano = request.GET.get("ano")
    serie = request.GET.get("serie")
    turma = request.GET.get("turma")
    turno = request.GET.get("turno")

    if ano:
        turmas = turmas.filter(ano_letivo=ano)

    if serie:
        turmas = turmas.filter(ano_escolar=serie)

    if turma:
        turmas = turmas.filter(nome=turma)

    if turno:
        turmas = turmas.filter(turno=turno)

    # =========================
    # ORDENAÇÃO
    # =========================

    ordem = request.GET.get("ordem", "ano_escolar")

    if ordem == "ano_letivo":
        turmas = turmas.order_by("ano_letivo")

    elif ordem == "etapa":
        turmas = turmas.order_by("etapa")

    elif ordem == "ano_escolar":
        turmas = turmas.order_by("ano_escolar")

    elif ordem == "nome":
        turmas = turmas.order_by("nome")

    elif ordem == "turno":
        turmas = turmas.order_by("turno")

    else:
        turmas = turmas.order_by("ano_escolar", "nome")

    # =========================
    # PAGINAÇÃO
    # =========================

    paginator = Paginator(turmas, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # =========================
    # DADOS PARA FILTROS
    # =========================

    anos = Turma.objects.values_list(
        "ano_letivo", flat=True
    ).distinct().order_by("ano_letivo")

    series = Turma.objects.values_list(
        "ano_escolar", flat=True
    ).distinct().order_by("ano_escolar")

    nomes_turma = Turma.objects.values_list(
        "nome", flat=True
    ).distinct().order_by("nome")

    turnos = Turma.objects.values_list(
        "turno", flat=True
    ).distinct().order_by("turno")

    context = {
        "page_obj": page_obj,
        "anos": anos,
        "series": series,
        "nomes_turma": nomes_turma,
        "turnos": turnos
    }

    template, context = render_smart(
        request,
        "turmas/lista_turmas.html",
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
def excluir_turma(request, pk):

    turma = get_object_or_404(Turma, pk=pk)

    turma.delete()

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": True})

    return redirect("lista_turmas")


@login_required
def relatorio_turmas(request):
    turmas = Turma.objects.all()
    return render(request, 'turmas/relatorio_turmas.html', {'turmas': turmas})