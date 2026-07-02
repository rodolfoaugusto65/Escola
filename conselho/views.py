from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from datetime import date
from .models import ConselhoClasse, ConselhoAluno
from .forms import ConselhoForm
from .services import gerar_conselho
import datetime
from datetime import date
from django.contrib import messages
from django.urls import reverse

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet


# 🔹 Base padrão
def get_base_template(request):
    if request.headers.get("HX-Request"):
        return "core/base_partial.html"
    return "core/base.html"


# 📋 LISTA
from datetime import date
from django.shortcuts import render


def lista_conselhos(request):
    conselhos = list(
        ConselhoClasse.objects
        .select_related(
            "criado_por",
            "turma"
        )
        .prefetch_related(
            "alunos",
            "alunos__aluno"
        )
        .order_by("-criado_em")
    )

    finalizados = 0
    rascunhos = 0

    for conselho in conselhos:

        alunos = list(conselho.alunos.all())

        total = len(alunos)

        concluidos = sum(
            1
            for a in alunos
            if any([
                a.faltas,
                a.disciplina,
                a.aprendizagem,
                a.apa,
                a.chamar_familia,
                a.reclassificacao,
                a.busca_ativa,
                a.afastamento,
                a.plano_recomposicao,
                a.observacao,
            ])
        )

        pendentes = max(0, total - concluidos)

        percentual = (
            int((concluidos / total) * 100)
            if total
            else 0
        )

        conselho.total_alunos = total
        conselho.concluidos = concluidos
        conselho.pendentes = pendentes
        conselho.percentual = percentual

        if percentual == 100:
            conselho.percentual_cor = "success"
        elif percentual >= 50:
            conselho.percentual_cor = "warning"
        else:
            conselho.percentual_cor = "danger"

        novo_status = (
            "finalizado"
            if total and concluidos == total
            else "rascunho"
        )

        if conselho.status != novo_status:
            conselho.status = novo_status
            conselho.save(
                update_fields=["status"]
            )

        if novo_status == "finalizado":
            finalizados += 1
        else:
            rascunhos += 1

    total_geral = len(conselhos)

    ultimo_conselho = (
        conselhos[0]
        if conselhos
        else None
    )

    percentual_geral = (
        int(
            (finalizados / total_geral) * 100
        )
        if total_geral
        else 0
    )

    # usar o ano atual e não o ano do último conselho
    ano_atual = date.today().year

    # relatórios sem repetição
    relatorios = (
        ConselhoClasse.objects
        .values(
            "bimestre",
            "ano"
        )
        .distinct()
        .order_by(
            "-ano",
            "-bimestre"
        )
    )

    return render(
        request,
        "conselho/lista.html",
        {
            "conselhos": conselhos,
            "relatorios": relatorios,
            "total_geral": total_geral,
            "finalizados": finalizados,
            "rascunhos": rascunhos,
            "percentual_geral": percentual_geral,
            "ano_atual": ano_atual,
            "ultimo_conselho": ultimo_conselho,
            "base_template": get_base_template(request),
        }
    )

# ➕ CRIAR CONSELHO
def criar_conselho(request):

    if request.method == "POST":
        form = ConselhoForm(request.POST)

        print("FORM VALID:", form.is_valid())
        print("ERROS:", form.errors)

        if form.is_valid():
            conselho = gerar_conselho(
                turma=form.cleaned_data["turma"],
                bimestre=form.cleaned_data["bimestre"],
                ano=form.cleaned_data["ano"],
                usuario=request.user
            )

            return redirect("conselho:preencher", conselho.id)

    else:
        form = ConselhoForm()

    return render(request, "conselho/form.html", {
        "form": form,
        "base_template": get_base_template(request)
    })


# 🧠 PREENCHIMENTO DO CONSELHO
def preencher_conselho(request, pk):
    conselho = get_object_or_404(ConselhoClasse, pk=pk)

    alunos = conselho.alunos.select_related(
        "aluno"
    ).order_by("aluno__nome")

    if request.method == "POST":
        for a in alunos:
            prefix = f"aluno_{a.id}"

            # CAMPOS PEDAGÓGICOS
            a.faltas = request.POST.get(
                f"{prefix}_faltas"
            )

            a.disciplina = request.POST.get(
                f"{prefix}_disciplina"
            )

            a.aprendizagem = request.POST.get(
                f"{prefix}_aprendizagem"
            )

            a.apa = request.POST.get(
                f"{prefix}_apa"
            )

            a.chamar_familia = request.POST.get(
                f"{prefix}_familia"
            )

            a.reclassificacao = request.POST.get(
                f"{prefix}_reclass"
            )

            # NOVOS CAMPOS
            a.busca_ativa = request.POST.get(
                f"{prefix}_busca_ativa"
            )

            a.afastamento = request.POST.get(
                f"{prefix}_afastamento"
            )

            a.plano_recomposicao = request.POST.get(
                f"{prefix}_plano_recomposicao"
            )

            a.observacao = request.POST.get(
                f"{prefix}_obs"
            )

            # PAED
            paed = request.POST.get(
                f"{prefix}_paed"
            )

            novo_valor = paed == "on"

            if a.aluno.aluno_paed != novo_valor:
                a.aluno.aluno_paed = novo_valor
                a.aluno.save(
                    update_fields=["aluno_paed"]
                )

            a.save()

            total = alunos.count()
            concluidos = sum(
                1
                for a in alunos
                if any([
                    a.faltas,
                    a.disciplina,
                    a.aprendizagem,
                    a.apa,
                    a.chamar_familia,
                    a.reclassificacao,
                    a.busca_ativa,
                    a.afastamento,
                    a.plano_recomposicao,
                    a.observacao,
                ])
            )

            conselho.status = (
                "finalizado"
                if total and concluidos == total
                else "rascunho"
            )

            conselho.save(update_fields=["status"])

            return redirect(
                "conselho:painel",
                conselho.id
            )

    return render(request, "conselho/preencher.html", {
        "conselho": conselho,
        "alunos": alunos,
        "base_template": get_base_template(request)
    })


# 📊 DETALHE
def detalhe_conselho(request, pk):
    conselho = get_object_or_404(
        ConselhoClasse,
        pk=pk
    )

    alunos = conselho.alunos.select_related(
        "aluno"
    ).order_by(
        "aluno__nome"
    )

    criticos = alunos.filter(
        classificacao="critico"
    ).count()

    return render(
        request,
        "conselho/detalhe.html",
        {
            "conselho": conselho,
            "alunos": alunos,
            "criticos": criticos,
            "base_template": get_base_template(
                request
            )
        }
    )


# 📝 ATA
def gerar_ata(request, pk):
    conselho = get_object_or_404(
        ConselhoClasse,
        pk=pk
    )

    alunos = conselho.alunos.select_related(
        "aluno"
    )

    context = {
        "conselho": conselho,
        "alunos": alunos,

        "criticos": alunos.filter(
            classificacao="critico"
        ),

        "prioritarios": alunos.exclude(
            prioridade="baixa"
        ),

        "familia": alunos.filter(
            chamar_familia="sim"
        ),

        "apa": alunos.filter(
            apa="sim"
        ),

        "reclassificacao": alunos.filter(
            reclassificacao="sim"
        ),

        "indisciplina": alunos.filter(
            disciplina="ind"
        ),

        "baixa_aprendizagem": alunos.filter(
            aprendizagem="nao"
        ),

        "faltosos": alunos.filter(
            faltas="faltoso"
        ),

        "busca_ativa": alunos.filter(
            busca_ativa="sim"
        ),

        "afastados": alunos.filter(
            afastamento="sim"
        ),

        "plano_pendente": alunos.filter(
            plano_recomposicao="nao_feito"
        ),

        "base_template": get_base_template(
            request
        ),
    }

    return render(
        request,
        "conselho/ata.html",
        context
    )

# 📄 PDF DA ATA
def gerar_ata_pdf(request, pk):
    conselho = get_object_or_404(
        ConselhoClasse,
        pk=pk
    )

    response = HttpResponse(
        content_type="application/pdf"
    )

    response[
        "Content-Disposition"
    ] = f'attachment; filename="ata_{pk}.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4
    )

    styles = getSampleStyleSheet()

    elementos = []

    elementos.append(
        Paragraph(
            "ATA DO CONSELHO DE CLASSE",
            styles["Title"]
        )
    )

    elementos.append(Spacer(1, 12))

    elementos.append(
        Paragraph(
            f"Turma: {conselho.turma}",
            styles["Normal"]
        )
    )

    elementos.append(
        Paragraph(
            f"Bimestre: {conselho.bimestre}",
            styles["Normal"]
        )
    )

    elementos.append(
        Paragraph(
            f"Ano: {conselho.ano}",
            styles["Normal"]
        )
    )

    elementos.append(Spacer(1, 12))

    elementos.append(
        Paragraph(
            f"Foi realizado o conselho da turma {conselho.turma}, "
            f"com análise pedagógica dos alunos.",
            styles["Normal"]
        )
    )

    elementos.append(Spacer(1, 12))

    dados = [[
        "Aluno",
        "Faltas",
        "Disciplina",
        "Aprendizagem",
        "Busca Ativa",
        "Afastamento",
        "Plano Rec.",
        "Ocorr.",
        "Classificação"
    ]]

    for a in conselho.alunos.all():
        dados.append([
            str(a.aluno),
            a.get_faltas_display()
            if a.faltas else "-",

            a.get_disciplina_display()
            if a.disciplina else "-",

            a.get_aprendizagem_display()
            if a.aprendizagem else "-",

            a.get_busca_ativa_display()
            if a.busca_ativa else "-",

            a.get_afastamento_display()
            if a.afastamento else "-",

            a.get_plano_recomposicao_display()
            if a.plano_recomposicao else "-",

            str(a.total_ocorrencias),
            a.classificacao
        ])

    tabela = Table(dados)

    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elementos.append(tabela)
    elementos.append(Spacer(1, 24))

    elementos.append(
        Paragraph(
            "Assinaturas:",
            styles["Heading2"]
        )
    )

    elementos.append(Spacer(1, 30))

    elementos.append(
        Paragraph(
            "__________________________",
            styles["Normal"]
        )
    )

    elementos.append(
        Paragraph(
            "Professor(a)",
            styles["Normal"]
        )
    )

    elementos.append(Spacer(1, 20))

    elementos.append(
        Paragraph(
            "__________________________",
            styles["Normal"]
        )
    )

    elementos.append(
        Paragraph(
            "Coordenação",
            styles["Normal"]
        )
    )

    elementos.append(Spacer(1, 20))

    elementos.append(
        Paragraph(
            "__________________________",
            styles["Normal"]
        )
    )

    elementos.append(
        Paragraph(
            "Direção",
            styles["Normal"]
        )
    )

    doc.build(elementos)

    return response


# 📈 RELATÓRIO PEDAGÓGICO
def relatorio_pedagogico(request, pk):
    conselho = get_object_or_404(
        ConselhoClasse,
        pk=pk
    )

    alunos = conselho.alunos.select_related(
        "aluno"
    )

    context = {
        "conselho": conselho,

        "reclassificacao": alunos.filter(
            reclassificacao="sim"
        ),

        "familia": alunos.filter(
            chamar_familia="sim"
        ),

        "apa": alunos.filter(
            apa="sim"
        ),

        "indisciplina": alunos.filter(
            disciplina="ind"
        ),

        "baixa_aprendizagem": alunos.filter(
            aprendizagem="nao"
        ),

        "faltosos": alunos.filter(
            faltas="faltoso"
        ),

        "criticos": alunos.filter(
            classificacao="critico"
        ),

        "busca_ativa": alunos.filter(
            busca_ativa="sim"
        ),

        "afastados": alunos.filter(
            afastamento="sim"
        ),

        "plano_pendente": alunos.filter(
            plano_recomposicao="nao_feito"
        ),

        # INDICADORES
        "total_alunos": alunos.count(),

        "total_criticos": alunos.filter(
            classificacao="critico"
        ).count(),

        "total_faltosos": alunos.filter(
            faltas="faltoso"
        ).count(),

        "total_apa": alunos.filter(
            apa="sim"
        ).count(),

        "total_busca_ativa": alunos.filter(
            busca_ativa="sim"
        ).count(),

        "total_afastados": alunos.filter(
            afastamento="sim"
        ).count(),

        "total_plano": alunos.filter(
            plano_recomposicao="nao_feito"
        ).count(),

        "base_template": get_base_template(
            request
        ),
    }

    return render(
        request,
        "conselho/relatorio.html",
        context
    )


# 📊 RELATÓRIO GERAL POR BIMESTRE
def relatorio_bimestre(request, bimestre, ano):
    conselhos = ConselhoClasse.objects.filter(
        bimestre=bimestre,
        ano=ano
    )

    alunos = (
        ConselhoAluno.objects
        .filter(
            conselho__in=conselhos
        )
        .select_related(
            "aluno",
            "conselho"
        )
        .order_by(
            "aluno__nome"
        )
    )

    criticos = alunos.filter(
        classificacao="critico"
    )

    atencao = alunos.filter(
        classificacao="atencao"
    )

    regulares = alunos.filter(
        classificacao="regular"
    )

    busca_ativa = alunos.filter(
        busca_ativa="sim"
    )

    faltosos = alunos.filter(
        faltas="faltoso"
    )

    paed = alunos.filter(
        aluno__aluno_paed=True
    )

    context = {
        "bimestre": bimestre,
        "ano": ano,

        "alunos": alunos,

        "criticos": criticos,
        "atencao": atencao,
        "regulares": regulares,
        "busca_ativa": busca_ativa,
        "faltosos": faltosos,
        "paed": paed,

        "total_alunos": alunos.count(),
        "total_criticos": criticos.count(),
        "total_atencao": atencao.count(),
        "total_regulares": regulares.count(),
        "total_busca_ativa": busca_ativa.count(),
        "total_faltosos": faltosos.count(),
        "total_paed": paed.count(),

        "conselhos": conselhos,
        "base_template": get_base_template(request),
    }

    return render(
        request,
        "conselho/relatorio_bimestre.html",
        context
    )

# Escolher modo
def escolher_modo(request, pk):
    conselho = get_object_or_404(ConselhoClasse, pk=pk)

    return render(request, "conselho/escolher_modo.html", {
        "conselho": conselho,
        "base_template": get_base_template(request)
    })

# painel conselho
def painel_conselho(request, pk):
    conselho = get_object_or_404(
        ConselhoClasse,
        pk=pk
    )

    alunos = (
        conselho.alunos
        .select_related("aluno")
        .order_by("aluno__nome")
    )

    concluidos = 0

    for a in alunos:
        a.preenchido = any([
            a.faltas,
            a.disciplina,
            a.aprendizagem,
            a.apa,
            a.chamar_familia,
            a.reclassificacao,
            a.busca_ativa,
            a.afastamento,
            a.plano_recomposicao,
            a.observacao,
        ])

        if a.preenchido:
            concluidos += 1

    total = alunos.count()

    pendentes = total - concluidos

    percentual = (
        int((concluidos / total) * 100)
        if total else 0
    )

    # Corrige status de conselhos antigos
    novo_status = (
        "finalizado"
        if total and concluidos == total
        else "rascunho"
    )

    if conselho.status != novo_status:
        conselho.status = novo_status
        conselho.save(update_fields=["status"])

    return render(
        request,
        "conselho/painel.html",
        {
            "conselho": conselho,
            "alunos": alunos,
            "concluidos": concluidos,
            "pendentes": pendentes,
            "percentual": percentual,
            "total": total,
            "base_template": get_base_template(request),
        }
    )

# preencher_aluno
from django.contrib import messages
from django.urls import reverse


def preencher_aluno(request, pk):
    conselho = get_object_or_404(
        ConselhoClasse,
        pk=pk
    )

    alunos = list(
        conselho.alunos.select_related(
            "aluno"
        ).order_by(
            "aluno__nome"
        )
    )

    if not alunos:
        messages.warning(
            request,
            "Nenhum aluno encontrado para este conselho."
        )

        return redirect(
            "conselho:detalhe",
            conselho.id
        )

    try:
        indice = int(
            request.GET.get(
                "indice",
                request.POST.get("indice", 0)
            )
        )
    except (TypeError, ValueError):
        indice = 0

    indice = max(
        0,
        min(indice, len(alunos) - 1)
    )

    atual = alunos[indice]

    # IDADE
    idade = None

    if atual.aluno.data_nascimento:
        hoje = date.today()

        idade = (
            hoje.year
            - atual.aluno.data_nascimento.year
            - (
                (hoje.month, hoje.day)
                <
                (
                    atual.aluno.data_nascimento.month,
                    atual.aluno.data_nascimento.day
                )
            )
        )

    # FUNÇÃO PARA VERIFICAR SE O ALUNO FOI PREENCHIDO
    def aluno_preenchido(a):
        return any([
            a.faltas,
            a.disciplina,
            a.aprendizagem,
            a.apa,
            a.chamar_familia,
            a.reclassificacao,
            a.busca_ativa,
            a.afastamento,
            a.plano_recomposicao,
            a.observacao,
        ])

    # PERCENTUAL DE PREENCHIMENTO
    concluidos = sum(
        1
        for a in alunos
        if aluno_preenchido(a)
    )

    percentual = (
        int((concluidos / len(alunos)) * 100)
        if alunos else 0
    )

    # =========================
    # SALVAR
    # =========================

    if request.method == "POST":

        atual = alunos[indice]

        prefix = f"aluno_{atual.id}"

        atual.faltas = request.POST.get(
            f"{prefix}_faltas"
        )

        atual.disciplina = request.POST.get(
            f"{prefix}_disciplina"
        )

        atual.aprendizagem = request.POST.get(
            f"{prefix}_aprendizagem"
        )

        atual.apa = request.POST.get(
            f"{prefix}_apa"
        )

        atual.chamar_familia = request.POST.get(
            f"{prefix}_familia"
        )

        atual.reclassificacao = request.POST.get(
            f"{prefix}_reclass"
        )

        atual.busca_ativa = request.POST.get(
            f"{prefix}_busca_ativa"
        )

        atual.afastamento = request.POST.get(
            f"{prefix}_afastamento"
        )

        atual.plano_recomposicao = request.POST.get(
            f"{prefix}_plano_recomposicao"
        )

        atual.observacao = request.POST.get(
            f"{prefix}_obs"
        )

        # PAED
        paed = request.POST.get(
            f"{prefix}_paed"
        )

        novo_valor = paed == "on"

        if atual.aluno.aluno_paed != novo_valor:
            atual.aluno.aluno_paed = novo_valor

            atual.aluno.save(
                update_fields=[
                    "aluno_paed"
                ]
            )

        atual.save()

        # RECALCULA STATUS
        concluidos = sum(
            1
            for a in alunos
            if aluno_preenchido(a)
        )

        novo_status = (
            "finalizado"
            if concluidos == len(alunos)
            else "rascunho"
        )

        if conselho.status != novo_status:
            conselho.status = novo_status

            conselho.save(
                update_fields=["status"]
            )

        acao = request.POST.get(
            "acao",
            "proximo"
        )

        # SALVAR E VOLTAR AO PAINEL
        if acao == "salvar":
            return redirect(
                "conselho:painel",
                conselho.id
            )

        # ALUNO ANTERIOR
        if acao == "anterior":
            novo_indice = max(
                0,
                indice - 1
            )

        # PRÓXIMO ALUNO
        else:

            # ÚLTIMO ALUNO
            if indice >= len(alunos) - 1:

                conselho.status = "finalizado"

                conselho.save(
                    update_fields=["status"]
                )

                return redirect(
                    "conselho:ata",
                    conselho.id
                )

            novo_indice = indice + 1

        url = reverse(
            "conselho:preencher_aluno",
            kwargs={
                "pk": conselho.id
            }
        )

        response = redirect(
            f"{url}?indice={novo_indice}"
        )

        # HTMX
        if request.headers.get("HX-Request"):
            response["HX-Redirect"] = (
                f"{url}?indice={novo_indice}"
            )

        return response

    return render(
        request,
        "conselho/preencher_aluno.html",
        {
            "conselho": conselho,
            "aluno": atual,
            "indice": indice,
            "total": len(alunos),
            "idade": idade,
            "percentual": percentual,
            "base_template": get_base_template(
                request
            ),
        }
    )

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from django.views.decorators.http import require_POST

@require_POST
def excluir_conselho(request, pk):
    conselho = get_object_or_404(
        ConselhoClasse,
        pk=pk
    )

    conselho.delete()

    messages.success(
        request,
        "Conselho excluído com sucesso."
    )

    return HttpResponse(status=204)