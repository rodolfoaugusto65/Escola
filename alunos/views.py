from django.shortcuts import render, get_object_or_404, redirect
from .models import Aluno
from turmas.models import Turma
from .forms import AlunoForm
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.utils import render_smart
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404

def lista_alunos(request):

    alunos = Aluno.objects.select_related("turma").all()

    # =========================
    # PARÂMETROS
    # =========================

    busca = request.GET.get("busca")
    turno = request.GET.get("turno")
    ano = request.GET.get("ano")
    turma = request.GET.get("turma")

    # =========================
    # BUSCA INTELIGENTE
    # =========================

    if busca:
        alunos = alunos.filter(
            Q(nome__icontains=busca) |
            Q(matricula__icontains=busca) |
            Q(turma__nome__icontains=busca) |
            Q(turma__ano_escolar__icontains=busca)
        )

    # =========================
    # FILTROS
    # =========================

    if turno:
        alunos = alunos.filter(turma__turno=turno)

    if ano:
        alunos = alunos.filter(turma__ano_escolar=ano)

    if turma:
        alunos = alunos.filter(turma__nome=turma)

    # =========================
    # ORDENAÇÃO
    # =========================

    ordem = request.GET.get("ordem", "nome")

    if ordem == "nome":
        alunos = alunos.order_by("nome")

    elif ordem == "-nome":
        alunos = alunos.order_by("-nome")

    elif ordem == "matricula":
        alunos = alunos.order_by("matricula")

    elif ordem == "-matricula":
        alunos = alunos.order_by("-matricula")

    elif ordem == "data_nascimento":
        alunos = alunos.order_by("data_nascimento")

    elif ordem == "-data_nascimento":
        alunos = alunos.order_by("-data_nascimento")

    else:
        alunos = alunos.order_by("nome")

    # =========================
    # PAGINAÇÃO
    # =========================

    paginator = Paginator(alunos, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # =========================
    # FILTROS DINÂMICOS
    # =========================

    turmas_qs = Turma.objects.all()

    if turno:
        turmas_qs = turmas_qs.filter(turno=turno)

    if ano:
        turmas_qs = turmas_qs.filter(ano_escolar=ano)

    turnos = Turma.objects.values_list("turno", flat=True).distinct().order_by("turno")

    anos = turmas_qs.values_list(
        "ano_escolar",
        flat=True
    ).distinct().order_by("ano_escolar")

    turmas = turmas_qs.values_list(
        "nome",
        flat=True
    ).distinct().order_by("nome")

    # =========================
    # CONTEXTO
    # =========================

    contexto = {
        "page_obj": page_obj,
        "turnos": turnos,
        "anos": anos,
        "turmas": turmas
    }

    template, contexto = render_smart(
        request,
        "alunos/lista_alunos.html",
        contexto
    )

    return render(request, template, contexto)

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

    aluno = None

    # tenta buscar pela matrícula
    aluno = Aluno.objects.filter(matricula=aluno_id).first()

    # se não encontrou tenta pelo ID
    if not aluno and str(aluno_id).isdigit():
        aluno = Aluno.objects.filter(id=int(aluno_id)).first()

    if not aluno:
        raise Http404("Aluno não encontrado")

    return render(request, 'alunos/relatorio_aluno_completo.html', {
        'aluno': aluno
    })



@login_required
def relatorio_alunos(request):

    alunos = Aluno.objects.select_related("turma").all()

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

    # =========================
    # PAGINAÇÃO MODERNA
    # =========================
    mostrar = request.GET.get("mostrar", 10)

    try:
        mostrar = int(mostrar)
    except:
        mostrar = 10

    paginator = Paginator(alunos.order_by("nome"), mostrar)

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # =========================
    # TURMAS
    # =========================
    turmas = Turma.objects.all().order_by('ano_letivo')

    # =========================
    # CONTEXTO
    # =========================
    context = {
        'alunos': alunos.order_by('nome'),  # mantém compatibilidade
        'page_obj': page_obj,               # usado na tabela
        'mostrar': mostrar,
        'turmas': turmas,
        'total': total,
        'total_paed': total_paed,
        'total_dependencia': total_dependencia,
        'total_transferidos': total_transferidos
    }

    template, context = render_smart(
        request,
        'alunos/relatorio_alunos.html',
        context
    )

    return render(request, template, context)