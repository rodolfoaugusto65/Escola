from io import BytesIO
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from openpyxl import load_workbook

from alunos.models import Aluno
from turmas.models import Turma
from .models import RegistroMapeamento


NIVEIS = ["", "Nível 01", "Nível 02", "Nível 03", "Nível 04", "Nível 05"]
CAMPOS_TEXTO = ["professor_lp", "professor_mt", "observacoes"]
CAMPOS_NIVEL = [
    "diagnostico_lp", "lp_b1", "lp_b2", "lp_b3", "lp_b4",
    "diagnostico_mt", "mt_b1", "mt_b2", "mt_b3", "mt_b4",
]


def _ano_turma(turma):
    valor = (turma.ano_escolar or "").strip()
    return valor.replace(" Ano", "").replace(" ano", "").strip()


@login_required
@require_http_methods(["GET", "POST"])
def painel(request):
    ano_atual = timezone.localdate().year
    anos = list(Turma.objects.order_by().values_list("ano_letivo", flat=True).distinct())
    ano = request.POST.get("ano") if request.method == "POST" else request.GET.get("ano")
    try:
        ano = int(ano or (ano_atual if ano_atual in anos else (max(anos) if anos else ano_atual)))
    except (TypeError, ValueError):
        ano = ano_atual
    turmas = Turma.objects.filter(ano_letivo=ano).order_by("etapa", "ano_escolar", "nome", "turno")
    turma_id = request.POST.get("turma") if request.method == "POST" else request.GET.get("turma")
    turma = None
    if turma_id:
        turma = turmas.filter(pk=turma_id).first()
    busca = request.POST.get("q", "") if request.method == "POST" else request.GET.get("q", "")
    alunos = Aluno.objects.none()
    registros = {}
    if turma:
        alunos = Aluno.objects.filter(turma=turma, transferido=False).order_by("nome")
        if busca.strip():
            from django.db.models import Q
            alunos = alunos.filter(Q(nome__icontains=busca.strip()) | Q(matricula__icontains=busca.strip()))
        registros = {
            r.aluno_id: r for r in RegistroMapeamento.objects.filter(
                turma=turma, ano_letivo=ano, aluno_id__in=alunos.values("id")
            )
        }
    if request.method == "POST" and request.POST.get("acao") == "salvar":
        if not turma:
            messages.error(request, "Selecione uma turma antes de salvar.")
            return redirect("mapeamento_aprendizagem:painel")
        ids = request.POST.getlist("selecionados")
        alunos_validos = Aluno.objects.filter(turma=turma, transferido=False, pk__in=ids)
        salvos = 0
        with transaction.atomic():
            for aluno in alunos_validos:
                registro, _ = RegistroMapeamento.objects.get_or_create(
                    aluno=aluno, ano_letivo=ano,
                    defaults={"turma": turma, "criado_por": request.user},
                )
                registro.turma = turma
                registro.paede = request.POST.get(f"paede_{aluno.pk}", "").strip()
                registro.situacao = request.POST.get(f"situacao_{aluno.pk}", "Matriculado").strip() or "Matriculado"
                for campo in CAMPOS_TEXTO:
                    setattr(registro, campo, request.POST.get(f"{campo}_{aluno.pk}", "").strip())
                for campo in CAMPOS_NIVEL:
                    valor = request.POST.get(f"{campo}_{aluno.pk}", "").strip()
                    setattr(registro, campo, valor if valor in NIVEIS else "")
                registro.atualizado_por = request.user
                registro.save()
                salvos += 1
        messages.success(request, f"Mapeamento salvo para {salvos} estudante(s).")
        return redirect(f"{request.path}?ano={ano}&turma={turma.pk}")
    return render(request, "mapeamento_aprendizagem/painel.html", {
        "anos": anos, "ano": ano, "turmas": turmas, "turma": turma,
        "alunos": alunos, "registros": registros, "q": busca,
        "niveis": NIVEIS,
        "lp_campos": [("diagnostico_lp", "Diagnóstico"), ("lp_b1", "1º Bimestre"), ("lp_b2", "2º Bimestre"), ("lp_b3", "3º Bimestre"), ("lp_b4", "4º Bimestre")],
        "mt_campos": [("diagnostico_mt", "Diagnóstico"), ("mt_b1", "1º Bimestre"), ("mt_b2", "2º Bimestre"), ("mt_b3", "3º Bimestre"), ("mt_b4", "4º Bimestre")],
        "total_alunos": alunos.count() if turma else 0,
        "total_preenchidos": len(registros),
    })


@login_required
def exportar(request):
    ano = request.GET.get("ano")
    turma_id = request.GET.get("turma")
    try:
        ano = int(ano)
    except (TypeError, ValueError):
        ano = timezone.localdate().year
    registros = RegistroMapeamento.objects.select_related("aluno", "turma").filter(ano_letivo=ano)
    turma = None
    if turma_id:
        turma = get_object_or_404(Turma, pk=turma_id, ano_letivo=ano)
        registros = registros.filter(turma=turma)
    registros = registros.order_by("turma__etapa", "turma__ano_escolar", "turma__nome", "aluno__nome")

    modelo = Path(__file__).resolve().parent / "modelos" / "planilha_monitoramento_modelo.xlsx"
    wb = load_workbook(modelo)
    try:
        wb.calculation.fullCalcOnLoad = True
        wb.calculation.forceFullCalc = True
        wb.calculation.calcMode = "auto"
    except AttributeError:
        pass
    ws = wb["Mapeamento"]
    # Preserva cabeçalhos, mesclagens, estilos, validações e fórmulas das outras abas.
    for row in ws.iter_rows(min_row=9, max_row=1500, min_col=1, max_col=19):
        for cell in row:
            cell.value = None
    for idx, registro in enumerate(registros, start=9):
        if idx > 1500:
            break
        t = registro.turma
        valores = [
            _ano_turma(t), t.nome, t.get_turno_display(), registro.aluno.nome,
            registro.paede, registro.situacao, registro.professor_lp,
            registro.diagnostico_lp, registro.lp_b1, registro.lp_b2,
            registro.lp_b3, registro.lp_b4, registro.professor_mt,
            registro.diagnostico_mt, registro.mt_b1, registro.mt_b2,
            registro.mt_b3, registro.mt_b4, registro.observacoes,
        ]
        for col, valor in enumerate(valores, start=1):
            ws.cell(idx, col).value = valor
    ws["A2"] = "Unidade Escolar:"
    ws["D2"] = "EE RODOLFO AUGUSTO TRECHAUD CURVO"
    ws["A3"] = "Coordenador(a):"
    # Keep the source workbook's own sheet organization and dashboard formulas.
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    nome = f"Mapeamento_Monitoramento_{ano}"
    if turma:
        nome += f"_{turma.ano_escolar}_{turma.nome}_{turma.turno}"
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{nome}.xlsx"'
    return response
