from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import get_template
#from xhtml2pdf import pisa
import openpyxl
from .models import Ocorrencia
from .forms import OcorrenciaForm
from alunos.models import Aluno
from turmas.models import Turma
from datetime import date
from openpyxl import Workbook
from django.http import JsonResponse
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator


def verificar_permissao(user):
    if user.is_superuser:
        return True
    
    grupos = user.groups.values_list("name", flat=True)
    
    if "Diretor" in grupos or "Coordenador" in grupos:
        return True
    
    raise PermissionDenied


@login_required
def lista_ocorrencias(request):

    ocorrencias = Ocorrencia.objects.select_related(
        "aluno", "turma"
    ).all()

    # ===== FILTROS =====
    busca = request.GET.get("busca")
    turma = request.GET.get("turma")
    aluno = request.GET.get("aluno")
    data = request.GET.get("data")

    if busca:
        ocorrencias = ocorrencias.filter(
            Q(codigo__icontains=busca) |
            Q(aluno__nome__icontains=busca) |
            Q(aluno__matricula__icontains=busca)
        )

    if turma:
        ocorrencias = ocorrencias.filter(turma_id=turma)

    if aluno:
        ocorrencias = ocorrencias.filter(aluno_id=aluno)

    if data:
        ocorrencias = ocorrencias.filter(data=data)

    # ===== ORDENAÇÃO DUPLA =====
    ordenar = request.GET.get("ordenar", "-data")

    campos_validos = [
        "codigo", "-codigo",
        "aluno__nome", "-aluno__nome",
        "turma__nome", "-turma__nome",
        "tipo_ocorrencia", "-tipo_ocorrencia",
        "status", "-status",
        "data", "-data",
    ]

    if ordenar in campos_validos:
        ocorrencias = ocorrencias.order_by(ordenar)

    # ===== PAGINAÇÃO =====
    paginator = Paginator(ocorrencias, 20)
    page = request.GET.get("page")
    ocorrencias = paginator.get_page(page)

    context = {
        "ocorrencias": ocorrencias,
        "turmas": Turma.objects.all(),
        "alunos": Aluno.objects.all(),

        "total": Ocorrencia.objects.count(),
        "abertas": Ocorrencia.objects.filter(status="ABERTA").count(),
        "andamento": Ocorrencia.objects.filter(status="ANDAMENTO").count(),
        "resolvidas": Ocorrencia.objects.filter(status="RESOLVIDA").count(),
    }

    return render(request, "ocorrencias/lista.html", context)


@login_required
def criar_ocorrencia(request):
    form = OcorrenciaForm(request.POST or None)

    if form.is_valid():
        obj = form.save(commit=False)
        obj.usuario = request.user
        obj.save()
        return redirect("lista_ocorrencias")

    return render(request, "ocorrencias/form.html", {"form": form})


@login_required
def editar_ocorrencia(request, pk):
    o = get_object_or_404(Ocorrencia, pk=pk)
    form = OcorrenciaForm(request.POST or None, instance=o)

    if form.is_valid():
        form.save()
        return redirect("detalhe_ocorrencia", pk=o.pk)

    return render(request, "ocorrencias/form.html", {"form": form})


@login_required
def detalhe_ocorrencia(request, pk):
    o = get_object_or_404(Ocorrencia, pk=pk)

    historico = Ocorrencia.objects.filter(
        aluno=o.aluno
    ).order_by("-data")

    return render(request, "ocorrencias/detalhe.html", {
        "o": o,
        "historico": historico,
    })


@login_required
def imprimir_ocorrencia(request, pk):
    o = get_object_or_404(Ocorrencia, pk=pk)
    return render(request, "ocorrencias/imprimir.html", {"o": o})


@login_required
def dashboard_ocorrencias(request):
    por_status = (
        Ocorrencia.objects
        .values("status")
        .annotate(total=Count("id"))
    )

    por_tipo = (
        Ocorrencia.objects
        .values("tipo_ocorrencia")
        .annotate(total=Count("id"))
    )

    recentes = Ocorrencia.objects.select_related(
        "aluno"
    ).order_by("-data")[:10]

    return render(request, "ocorrencias/dashboard.html", {
        "por_status": por_status,
        "por_tipo": por_tipo,
        "recentes": recentes
    })


@login_required
def relatorio_ocorrencias(request):
    ocorrencias = Ocorrencia.objects.select_related(
        "aluno", "turma"
    ).order_by("-data")

    return render(request, "ocorrencias/relatorio.html", {
        "ocorrencias": ocorrencias
    })


@login_required
def imprimir_por_aluno(request, aluno_id):
    aluno = get_object_or_404(Aluno, pk=aluno_id)

    ocorrencias = Ocorrencia.objects.filter(
        aluno=aluno
    ).order_by("-data")

    template = get_template("ocorrencias/imprimir_aluno.html")

    html = template.render({
        "aluno": aluno,
        "ocorrencias": ocorrencias
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'filename="relatorio_{aluno.nome}.pdf"'

    pisa.CreatePDF(html, dest=response)
    return response

@login_required
def dashboard_enterprise(request):

    status_qs = Ocorrencia.objects.values("status").annotate(total=Count("id"))
    tipo_qs = Ocorrencia.objects.values("tipo_ocorrencia").annotate(total=Count("id"))

    status_data = {
        "labels": [obj["status"] for obj in status_qs],
        "values": [obj["total"] for obj in status_qs]
    }

    tipo_data = {
        "labels": [obj["tipo_ocorrencia"] for obj in tipo_qs],
        "values": [obj["total"] for obj in tipo_qs]
    }

    return render(request,"ocorrencias/dashboard_enterprise.html", {
        "status_data": status_data,
        "tipo_data": tipo_data,
    })


@login_required
def export_excel_ocorrencias(request):

    wb = Workbook()
    ws = wb.active
    ws.title = "Ocorrências"

    # Cabeçalho
    ws.append([
        "Código",
        "Aluno",
        "Matrícula",
        "Turma",
        "Tipo",
        "Status",
        "Data",
        "Descrição",
        "Providências"
    ])

    ocorrencias = Ocorrencia.objects.select_related(
        "aluno", "turma"
    ).all()

    for o in ocorrencias:
        ws.append([
            o.codigo,
            str(o.aluno.nome),
            str(o.aluno.matricula),
            str(o.turma),  # ✅ CONVERTIDO
            o.get_tipo_ocorrencia_display(),
            o.get_status_display(),
            o.data.strftime("%d/%m/%Y") if o.data else "",
            o.descricao,
            o.providencias,
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=ocorrencias.xlsx"

    wb.save(response)
    return response

@login_required
def imprimir_pdf_enterprise(request):
    ocorrencias = Ocorrencia.objects.select_related("aluno","turma").all()
    template = get_template("ocorrencias/imprimir_pdf_cabecalho.html")

    html = template.render({
        "ocorrencias": ocorrencias,
        "hoje": date.today(),
        "escola_nome": "Sua Escola"
    })

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'filename="ocorrencias_relatorio.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response

@login_required
def get_alunos_por_turma(request):
    turma_id = request.GET.get("turma")

    alunos = Aluno.objects.filter(
        turma_id=turma_id
    ).values("id", "nome")

    return JsonResponse(list(alunos), safe=False)

#@login_required
#def buscar_aluno(request):
#    termo = request.GET.get("q")
#
#    if not termo:
#        return JsonResponse({}, safe=False)
#
#    aluno = Aluno.objects.filter(
#        Q(nome__icontains=termo) |
#        Q(matricula__icontains=termo)
#    ).select_related("turma").first()
#
#    if not aluno:
#        return JsonResponse({"erro": "Aluno não encontrado"})
#
#    return JsonResponse({
#        "id": aluno.id,
#        "nome": aluno.nome,
#        "turma_id": aluno.turma.id if aluno.turma else None,
#        "turma_nome": str(aluno.turma) if aluno.turma else ""
#    })


@login_required
def buscar_aluno(request):
    q = request.GET.get("q")

    alunos = Aluno.objects.filter(
        Q(nome__icontains=q) |
        Q(matricula__icontains=q)
    )[:5]

    data = []

    for a in alunos:
        data.append({
            "id": a.id,
            "nome": a.nome,
            "matricula": a.matricula,
            "turma_id": a.turma.id if a.turma else None
        })

    return JsonResponse(data, safe=False)

# 📄 Prontuário do aluno
@login_required
def prontuario_aluno(request, aluno_id):
    aluno = get_object_or_404(Aluno, pk=aluno_id)

    ocorrencias = Ocorrencia.objects.filter(
        aluno=aluno
    ).order_by("-data")

    return render(request, "ocorrencias/prontuario.html", {
        "aluno": aluno,
        "ocorrencias": ocorrencias
    })


# ⚡ Busca AJAX
@login_required
def busca_ajax(request):
    q = request.GET.get("q")

    ocorrencias = Ocorrencia.objects.filter(
        Q(aluno__nome__icontains=q) |
        Q(aluno__matricula__icontains=q) |
        Q(codigo__icontains=q)
    )[:10]

    data = [
        {
            "codigo": o.codigo,
            "aluno": o.aluno.nome,
            "status": o.get_status_display(),
            "data": o.data.strftime("%d/%m/%Y")
        }
        for o in ocorrencias
    ]

    return JsonResponse(data, safe=False)