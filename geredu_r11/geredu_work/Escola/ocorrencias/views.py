from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import get_template
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
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import fonts
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from io import BytesIO
from core.utils import render_smart
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Count
from django.urls import reverse
from django.db.models import Max



def verificar_permissao(user):
    if user.is_superuser:
        return True
    
    grupos = user.groups.values_list("name", flat=True)
    
    if "Diretor" in grupos or "Coordenador" in grupos:
        return True
    
    raise PermissionDenied


@login_required
def lista_ocorrencias(request):

# 🔐 BLOQUEIO DE PERMISSÃO
    if not request.user.pode_gerenciar_usuarios:
        return HttpResponseForbidden("Você não possui permissão para acessar este módulo.")
    
    ocorrencias = Ocorrencia.objects.select_related(
        "aluno", "turma"
    ).all()

    # ===== FILTROS =====
    busca = request.GET.get("busca")
    turma = request.GET.get("turma")
    aluno = request.GET.get("aluno") or request.GET.get("matricula")
    status = request.GET.get("status")
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
        # tenta por matrícula primeiro
        ocorrencias_matricula = ocorrencias.filter(aluno__matricula=aluno)

        if ocorrencias_matricula.exists():
            ocorrencias = ocorrencias_matricula
        else:
            # fallback para ID
            if str(aluno).isdigit():
                ocorrencias = ocorrencias.filter(aluno_id=int(aluno))

    if status:
        ocorrencias = ocorrencias.filter(status=status)

    if data:
        ocorrencias = ocorrencias.filter(data=data)

    # ===== ORDENAÇÃO =====
    ordenar = request.GET.get("ordenar", "-data")

    campos_validos = [
        "codigo", "-codigo",
        "aluno__nome", "-aluno__nome",
        "turma__nome", "-turma__nome",
        "tipo_ocorrencia", "-tipo_ocorrencia",
        "status", "-status",
        "data", "-data",
    ]

    if ordenar not in campos_validos:
        ordenar = "-data"

    ocorrencias = ocorrencias.order_by(ordenar)

    # ===== PAGINAÇÃO MODERNA =====
    mostrar = request.GET.get("mostrar", 10)

    try:
        mostrar = int(mostrar)
    except:
        mostrar = 10

    paginator = Paginator(ocorrencias, mostrar)

    page = request.GET.get("page")
    page_obj = paginator.get_page(page)

    # ===== CONTADORES (RESPEITANDO FILTROS) =====
    base = ocorrencias

    context = {
        "ocorrencias": page_obj,
        "page_obj": page_obj,
        "mostrar": mostrar,

        "turmas": Turma.objects.all().order_by("ano_escolar", "nome"),
        "alunos": Aluno.objects.all().order_by("nome"),

        "total": base.count(),
        "abertas": base.filter(status="ABERTA").count(),
        "andamento": base.filter(status="ANDAMENTO").count(),
        "resolvidas": base.filter(status="RESOLVIDA").count(),
    }

    template, context = render_smart(
        request,
        "ocorrencias/lista.html",
        context
    )

    return render(request, template, context)



@login_required
def criar_ocorrencia(request):

    aluno_id = request.GET.get("aluno")
    matricula = request.GET.get("matricula")

    aluno = None

    if matricula:
        aluno = Aluno.objects.filter(matricula=matricula).first()

    elif aluno_id:
        aluno = Aluno.objects.filter(pk=aluno_id).first()

    form = OcorrenciaForm(request.POST or None)

    if aluno:
        form.initial["aluno"] = aluno
        form.initial["turma"] = aluno.turma

    if request.method == "POST":

        if form.is_valid():

            obj = form.save(commit=False)
            obj.usuario = request.user
            obj.save()

            if request.headers.get("x-requested-with") == "XMLHttpRequest":

                return JsonResponse({
                    "success": True,
                    "ocorrencia_id": obj.id,
                    "url_impressao": reverse("imprimir_ocorrencia", args=[obj.id]),
                    "redirect": reverse("lista_ocorrencias")
                })

            return redirect("lista_ocorrencias")

    total_ocorrencias = 0
    ocorrencias_resumo = []

    if aluno:
        qs = (
            Ocorrencia.objects
            .filter(aluno=aluno)
            .values("tipo_ocorrencia")
            .annotate(total=Count("id"))
        )

        ocorrencias_resumo = list(qs)
        total_ocorrencias = sum(o["total"] for o in ocorrencias_resumo)

    context = {
        "form": form,
        "aluno": aluno,
        "total_ocorrencias": total_ocorrencias,
        "ocorrencias_resumo": ocorrencias_resumo,
    }

    return render(request, "ocorrencias/form.html", context)


@login_required
def editar_ocorrencia(request, pk):

    o = get_object_or_404(Ocorrencia, pk=pk)

    if request.method == "POST":
        form = OcorrenciaForm(request.POST, instance=o)

        if form.is_valid():
            form.save()
            return redirect("detalhe_ocorrencia", pk=o.pk)

    else:
        form = OcorrenciaForm(instance=o)

    return render(request, "ocorrencias/form.html", {
        "form": form,
        "ocorrencia": o
    })


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
    ocorrencias = Ocorrencia.objects.filter(aluno=aluno).order_by("-data")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"Relatório de Ocorrências - {aluno.nome}", styles["Heading1"]))
    elements.append(Spacer(1, 12))

    data = [["Código", "Tipo", "Status", "Data"]]

    for o in ocorrencias:
        data.append([
            o.codigo,
            o.get_tipo_ocorrencia_display(),
            o.get_status_display(),
            o.data.strftime("%d/%m/%Y") if o.data else ""
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    return HttpResponse(buffer, content_type="application/pdf")

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
    ocorrencias = Ocorrencia.objects.select_related("aluno", "turma").all()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("Relatório Geral de Ocorrências", styles["Heading1"]))
    elements.append(Spacer(1, 12))

    data = [["Código", "Aluno", "Turma", "Status", "Data"]]

    for o in ocorrencias:
        data.append([
            o.codigo,
            o.aluno.nome,
            str(o.turma),
            o.get_status_display(),
            o.data.strftime("%d/%m/%Y") if o.data else ""
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    return HttpResponse(buffer, content_type="application/pdf")

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



@login_required
@require_POST
def excluir_ocorrencia(request, pk):

    if not request.user.pode_gerenciar_usuarios:
        raise PermissionDenied

    ocorrencia = get_object_or_404(Ocorrencia, pk=pk)
    codigo = ocorrencia.codigo

    try:
        ocorrencia.delete()

    except IntegrityError:
        msg = "Não foi possível excluir a ocorrência por dependências no banco."

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': msg}, status=400)

        messages.error(request, msg)
        return redirect('lista_ocorrencias')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'Ocorrência {codigo} excluída com sucesso.'
        })

    messages.success(request, f"🗑️ Ocorrência {codigo} excluída com sucesso.")
    return redirect('lista_ocorrencias')


def contador_ocorrencias(request, aluno_id):

    aluno = Aluno.objects.get(id=aluno_id)

    qtd = Ocorrencia.objects.filter(aluno=aluno).count()

    return JsonResponse({
        "nome": aluno.nome,
        "ocorrencias": qtd
    })


from django.db.models import Count, Max
from django.urls import reverse

@login_required
def alerta_ocorrencias(request):

    aluno_id = request.GET.get("aluno")

    if not aluno_id:
        return JsonResponse({"total": 0})

    aluno = Aluno.objects.get(id=aluno_id)

    tipos = (
        Ocorrencia.objects
        .filter(aluno_id=aluno_id)
        .values("tipo_ocorrencia")
        .annotate(total=Count("id"))
    )

    status = (
        Ocorrencia.objects
        .filter(aluno_id=aluno_id)
        .values("status")
        .annotate(total=Count("id"))
    )

    ultima = (
        Ocorrencia.objects
        .filter(aluno_id=aluno_id)
        .aggregate(data=Max("data"))
    )

    return JsonResponse({
        "nome": aluno.nome,
        "total": sum(o["total"] for o in tipos),
        "tipos": list(tipos),
        "status": list(status),
        "ultima": ultima["data"],
        "relatorio": reverse("prontuario_aluno", args=[aluno_id])
    })