from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import DocumentoAluno
from .forms import DocumentoAlunoForm
from .models import Aluno
from turmas.models import Turma
from .forms import AlunoForm
from core.utils import render_smart
from django.core.files.storage import default_storage
from ocorrencias.models import Ocorrencia
from frequencia.models import FrequenciaAluno

# ==================================================
# LISTA DE ALUNOS
# ==================================================
@login_required
def lista_alunos(request):

    alunos = (
        Aluno.objects
        .select_related("turma")
        .only(
            "id",
            "nome",
            "matricula",
            "data_nascimento",
            "turma_ano_letivo",
            "turma_ano_escolar",
            "turma_nome",
            "turma__nome",
            "turma__ano_escolar",
            "turma__turno"
        )
    )

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
    # ORDENAÇÃO SEGURA
    # =========================

    ordem = request.GET.get("ordem", "nome")

    campos_validos = [
        "nome", "-nome",
        "matricula", "-matricula",
        "data_nascimento", "-data_nascimento"
    ]

    if ordem not in campos_validos:
        ordem = "nome"

    alunos = alunos.order_by(ordem)

    # =========================
    # LIMITE DE REGISTROS
    # =========================

    try:
        limite = int(request.GET.get("limite", 20))
    except ValueError:
        limite = 20

    if limite not in [10, 20, 30, 40, 50]:
        limite = 20

    # =========================
    # PAGINAÇÃO
    # =========================

    paginator = Paginator(alunos, limite)
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

    turnos = Turma.objects.values_list(
        "turno",
        flat=True
    ).distinct().order_by("turno")

    anos = turmas_qs.values_list(
        "ano_escolar",
        flat=True
    ).distinct().order_by("ano_escolar")

    turmas = turmas_qs.values_list(
        "nome",
        flat=True
    ).distinct().order_by("nome")

    contexto = {
        "page_obj": page_obj,
        "turnos": turnos,
        "anos": anos,
        "turmas": turmas,
        "limite": limite
    }

    template, contexto = render_smart(
        request,
        "alunos/lista_alunos.html",
        contexto
    )

    return render(request, template, contexto)


# ==================================================
# CADASTRAR ALUNO
# ==================================================

@login_required
def cadastrar_aluno(request):

    if request.method == 'POST':

        form = AlunoForm(request.POST, request.FILES)

        if form.is_valid():

            aluno = form.save(commit=False)

            if request.user.is_authenticated:
                aluno.criado_por = request.user
                aluno.atualizado_por = request.user

            aluno.save()

            messages.success(request, "Aluno cadastrado com sucesso!")
            return redirect('lista_alunos')

        else:
            messages.error(request, "Corrija os erros antes de salvar.")

    else:
        form = AlunoForm()

    return render(
        request,
        'alunos/cadastrar_aluno.html',
        {'form': form}
    )


# ==================================================
# EDITAR ALUNO
# ==================================================
@login_required
def editar_aluno(request, id):

    aluno = get_object_or_404(Aluno, id=id)

    # =========================
    # CONTADOR DE LAUDOS PAED
    # =========================
    total_laudos = aluno.documentos.count()

    if request.method == 'POST':

        form = AlunoForm(
            request.POST,
            request.FILES,
            instance=aluno
        )

        if form.is_valid():

            aluno = form.save(commit=False)

            # =========================
            # REMOVER FOTO (SE EXISTIR)
            # =========================
            if request.POST.get("foto-clear"):

                # foto principal
                if aluno.foto:
                    try:
                        if default_storage.exists(aluno.foto.name):
                            default_storage.delete(aluno.foto.name)
                    except Exception:
                        pass

                # thumbnail
                if getattr(aluno, "foto_thumb", None):
                    try:
                        if default_storage.exists(aluno.foto_thumb.name):
                            default_storage.delete(aluno.foto_thumb.name)
                    except Exception:
                        pass

                aluno.foto = None
                aluno.foto_thumb = None

            # =========================
            # AUDITORIA
            # =========================
            if request.user.is_authenticated:
                aluno.atualizado_por = request.user

            aluno.save()

            messages.success(request, "Aluno atualizado com sucesso!")
            return redirect('lista_alunos')

        else:
            messages.error(request, "Corrija os erros antes de salvar.")

    else:
        form = AlunoForm(instance=aluno)

    return render(
        request,
        'alunos/cadastrar_aluno.html',
        {
            'form': form,
            'aluno': aluno,
            'total_laudos': total_laudos
        }
    )

# ==================================================
# EXCLUIR ALUNO
# ==================================================

@require_POST
@login_required
def excluir_aluno(request, pk):

    aluno = get_object_or_404(Aluno, pk=pk)

    try:

        aluno.delete()

        return JsonResponse({
            "success": True,
            "message": "Aluno excluído com sucesso!"
        })

    except Exception:

        return JsonResponse({
            "success": False,
            "error": "Erro interno ao excluir."
        })


# ==================================================
# RELATÓRIO COMPLETO DO ALUNO
# ==================================================
@login_required
def relatorio_aluno_completo(request, aluno_id):

    # =========================
    # BUSCAR ALUNO (ID OU MATRÍCULA)
    # =========================

    aluno = Aluno.objects.select_related("turma").filter(
        id=aluno_id
    ).first()

    if not aluno:
        aluno = Aluno.objects.select_related("turma").filter(
            matricula=aluno_id
        ).first()

    if not aluno:
        raise Http404("Aluno não encontrado")

    # =========================
    # DOCUMENTOS PAED
    # =========================

    documentos_paed = DocumentoAluno.objects.filter(
        aluno=aluno
    ).order_by("-data_laudo")

    # =========================
    # OCORRÊNCIAS
    # =========================

    ocorrencias = Ocorrencia.objects.filter(
        aluno=aluno
    ).order_by("-data")

    total_ocorrencias = ocorrencias.count()

    # =========================
    # FREQUÊNCIA
    # =========================

    frequencias = FrequenciaAluno.objects.filter(
        aluno=aluno
    ).select_related("frequencia")

    total_aulas = frequencias.count()

    total_presencas = frequencias.filter(
        presente=True
    ).count()

    percentual_frequencia = 0

    if total_aulas > 0:
        percentual_frequencia = round(
            (total_presencas / total_aulas) * 100,
            1
        )

    # =========================
    # ÚLTIMO DIA PRESENTE
    # =========================

    ultimo_dia_presente = frequencias.filter(
        presente=True
    ).order_by("-frequencia__data").values_list(
        "frequencia__data",
        flat=True
    ).first()

    # =========================
    # CONTEXTO
    # =========================

    contexto = {
        "aluno": aluno,
        "documentos_paed": documentos_paed,
        "ocorrencias": ocorrencias[:10],  # últimas ocorrências
        "total_ocorrencias": total_ocorrencias,
        "percentual_frequencia": percentual_frequencia,
        "ultimo_dia_presente": ultimo_dia_presente,
    }

    return render(
        request,
        "alunos/relatorio_aluno_completo.html",
        contexto
    )

# ==================================================
# RELATÓRIO DE ALUNOS
# ==================================================

@login_required
def relatorio_alunos(request):

    alunos = Aluno.objects.select_related("turma").all()

    query = request.GET.get('q')
    tipo = request.GET.get('tipo')

    if query:

        if tipo == 'matricula':
            alunos = alunos.filter(matricula__icontains=query)

        else:
            alunos = alunos.filter(nome__icontains=query)

    turma_id = request.GET.get('turma')

    if turma_id:
        alunos = alunos.filter(turma_id=turma_id)

    if request.GET.get('dependencia') == '1':
        alunos = alunos.filter(possui_dependencia=True)

    if request.GET.get('trabalhador') == '1':
        alunos = alunos.filter(aluno_trabalhador=True)

    if request.GET.get('paed') == '1':
        alunos = alunos.filter(aluno_paed=True)

    if request.GET.get('transferido') == '1':
        alunos = alunos.filter(transferido=True)

    total = alunos.count()
    total_paed = alunos.filter(aluno_paed=True).count()
    total_dependencia = alunos.filter(possui_dependencia=True).count()
    total_transferidos = alunos.filter(transferido=True).count()

    mostrar = request.GET.get("mostrar", 10)

    try:
        mostrar = int(mostrar)
    except:
        mostrar = 10

    paginator = Paginator(
        alunos.order_by("nome"),
        mostrar
    )

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    turmas = Turma.objects.all().order_by('ano_letivo')

    context = {
        'alunos': alunos.order_by('nome'),
        'page_obj': page_obj,
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

from django.urls import reverse

@login_required
def documentos_aluno(request, aluno_id):

    aluno = get_object_or_404(Aluno, id=aluno_id)

    # =========================
    # ORIGEM DA NAVEGAÇÃO
    # =========================
    next_url = request.GET.get("next")

    if not next_url:
        next_url = request.META.get("HTTP_REFERER")

    if not next_url or "/editar/" not in next_url:
        next_url = reverse("editar_aluno", args=[aluno.id])

    # destino do botão voltar
    voltar_aluno = reverse("editar_aluno", args=[aluno.id])

    # =========================
    # VERIFICA PAED
    # =========================
    if not aluno.aluno_paed:
        messages.warning(request, "Este aluno não pertence ao programa PAED.")
        return redirect("relatorio_aluno_completo", aluno.id)

    documentos = aluno.documentos.all().order_by("-data_laudo")

    # =========================
    # SALVAR DOCUMENTO
    # =========================
    if request.method == "POST":

        form = DocumentoAlunoForm(request.POST, request.FILES)

        if form.is_valid():

            documento = form.save(commit=False)
            documento.aluno = aluno
            documento.save()

            messages.success(request, "Laudo anexado com sucesso.")

            return redirect(f"{request.path}?next={next_url}")

    else:
        form = DocumentoAlunoForm()

    # =========================
    # RENDER
    # =========================
    return render(request, "alunos/documentos_aluno.html", {
        "aluno": aluno,
        "documentos": documentos,
        "form": form,
        "next": next_url,
        "voltar_aluno": voltar_aluno
    })
@login_required
def editar_documento(request, doc_id):

    documento = get_object_or_404(DocumentoAluno, id=doc_id)
    aluno = documento.aluno

    next_url = request.GET.get("next")

    if request.method == "POST":

        form = DocumentoAlunoForm(
            request.POST,
            request.FILES,
            instance=documento
        )

        if form.is_valid():
            form.save()

            messages.success(request, "Laudo atualizado com sucesso.")

            if next_url:
                return redirect(next_url)

            return redirect("documentos_aluno", aluno_id=aluno.id)

    else:
        form = DocumentoAlunoForm(instance=documento)

    return render(request, "alunos/editar_documento.html", {
        "form": form,
        "documento": documento,
        "aluno": aluno,
        "next": next_url
    })


@login_required
def excluir_documento(request, doc_id):

    documento = get_object_or_404(DocumentoAluno, id=doc_id)
    aluno_id = documento.aluno.id

    next_url = request.GET.get("next")

    # apagar arquivo no storage (Cloud / S3 / R2)
    if documento.arquivo:
        documento.arquivo.delete(save=False)

    documento.delete()

    messages.success(request, "Laudo excluído com sucesso.")

    if next_url:
        return redirect(next_url)

    return redirect("documentos_aluno", aluno_id=aluno_id)


@login_required
def detalhe_documento(request, doc_id):

    documento = get_object_or_404(DocumentoAluno, id=doc_id)

    next_url = request.GET.get("next")

    return render(
        request,
        "alunos/detalhe_documento.html",
        {
            "documento": documento,
            "aluno": documento.aluno,
            "next": next_url
        }
    )


@login_required
@require_POST
def atualizar_paed(request, aluno_id):

    aluno = get_object_or_404(Aluno, id=aluno_id)

    valor = request.POST.get("paed") == "true"

    aluno.aluno_paed = valor
    aluno.save(update_fields=["aluno_paed"])

    return JsonResponse({
        "success": True,
        "paed": aluno.aluno_paed
    })