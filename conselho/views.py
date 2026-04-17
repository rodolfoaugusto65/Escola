from django.shortcuts import render, redirect, get_object_or_404
from .models import ConselhoClasse
from .forms import ConselhoForm
from .services import gerar_conselho
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse

# 🔹 Base padrão
def get_base_template(request):
    if request.headers.get("HX-Request"):
        return "core/base_partial.html"
    return "core/base.html"

# 📋 LISTA
def lista_conselhos(request):
    conselhos = ConselhoClasse.objects.all().order_by("-criado_em")

    return render(request, "conselho/lista.html", {
        "conselhos": conselhos,
        "base_template": get_base_template(request)
    })


# ➕ CRIAR CONSELHO
def criar_conselho(request):

    if request.method == "POST":
        form = ConselhoForm(request.POST)

        # 🔥 DEBUG (pode remover depois)
        print("FORM VALID:", form.is_valid())
        print("ERROS:", form.errors)

        if form.is_valid():
            conselho = gerar_conselho(
                turma=form.cleaned_data["turma"],
                bimestre=form.cleaned_data["bimestre"],
                ano=form.cleaned_data["ano"],
                usuario=request.user
            )

            # 🔥 REDIRECIONA PARA TELA DE LANÇAMENTO
            return redirect("conselho:preencher", conselho.id)

    else:
        form = ConselhoForm()

    return render(request, "conselho/form.html", {
        "form": form,
        "base_template": get_base_template(request)
    })


# 🧠 NOVA TELA (LANÇAMENTO DO CONSELHO)
def preencher_conselho(request, pk):
    conselho = get_object_or_404(ConselhoClasse, pk=pk)
    alunos = conselho.alunos.all()

    if request.method == "POST":

        for a in alunos:
            prefix = f"aluno_{a.id}"

            a.faltas = request.POST.get(f"{prefix}_faltas")
            a.disciplina = request.POST.get(f"{prefix}_disciplina")
            a.aprendizagem = request.POST.get(f"{prefix}_aprendizagem")
            a.apa = request.POST.get(f"{prefix}_apa")
            a.chamar_familia = request.POST.get(f"{prefix}_familia")
            a.reclassificacao = request.POST.get(f"{prefix}_reclass")
            a.observacao = request.POST.get(f"{prefix}_obs")

            a.save()

        # 🔥 após salvar → vai para detalhe
        return redirect("conselho:detalhe", conselho.id)

    return render(request, "conselho/preencher.html", {
        "conselho": conselho,
        "alunos": alunos,
        "base_template": get_base_template(request)
    })


# 📊 DETALHE
def detalhe_conselho(request, pk):
    conselho = get_object_or_404(ConselhoClasse, pk=pk)

    return render(request, "conselho/detalhe.html", {
        "conselho": conselho,
        "alunos": conselho.alunos.all(),
        "base_template": get_base_template(request)
    })


# 📝 ATA
def gerar_ata(request, pk):
    conselho = get_object_or_404(ConselhoClasse, pk=pk)

    return render(request, "conselho/ata.html", {
        "conselho": conselho,
        "criticos": conselho.alunos.filter(classificacao="critico"),
        "prioritarios": conselho.alunos.exclude(prioridade="baixa"),
        "base_template": get_base_template(request)
    })

def gerar_ata_pdf(request, pk):
    conselho = get_object_or_404(ConselhoClasse, pk=pk)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ata_{pk}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()

    elementos = []

    # 🏫 TÍTULO
    elementos.append(Paragraph("ATA DO CONSELHO DE CLASSE", styles["Title"]))
    elementos.append(Spacer(1, 12))

    # 📊 DADOS
    elementos.append(Paragraph(f"Turma: {conselho.turma}", styles["Normal"]))
    elementos.append(Paragraph(f"Bimestre: {conselho.bimestre}", styles["Normal"]))
    elementos.append(Paragraph(f"Ano: {conselho.ano}", styles["Normal"]))
    elementos.append(Spacer(1, 12))

    # 📋 TEXTO
    elementos.append(Paragraph(
        f"Foi realizado o conselho da turma {conselho.turma}, com análise pedagógica dos alunos.",
        styles["Normal"]
    ))
    elementos.append(Spacer(1, 12))

    # 📊 TABELA
    dados = [
        ["Aluno", "Faltas", "Disciplina", "Aprendizagem", "Ocorr.", "Classificação"]
    ]

    for a in conselho.alunos.all():
        dados.append([
            str(a.aluno),
            a.get_faltas_display() if a.faltas else "-",
            a.get_disciplina_display() if a.disciplina else "-",
            a.get_aprendizagem_display() if a.aprendizagem else "-",
            str(a.total_ocorrencias),
            a.classificacao
        ])

    tabela = Table(dados)

    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elementos.append(tabela)
    elementos.append(Spacer(1, 24))

    # ✍️ ASSINATURAS
    elementos.append(Paragraph("Assinaturas:", styles["Heading2"]))
    elementos.append(Spacer(1, 30))

    elementos.append(Paragraph("__________________________", styles["Normal"]))
    elementos.append(Paragraph("Professor(a)", styles["Normal"]))
    elementos.append(Spacer(1, 20))

    elementos.append(Paragraph("__________________________", styles["Normal"]))
    elementos.append(Paragraph("Coordenação", styles["Normal"]))
    elementos.append(Spacer(1, 20))

    elementos.append(Paragraph("__________________________", styles["Normal"]))
    elementos.append(Paragraph("Direção", styles["Normal"]))

    doc.build(elementos)

    return response