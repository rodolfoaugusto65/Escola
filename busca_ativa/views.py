import csv
import sqlite3
import tempfile
import os
import io
import hashlib
import json
import logging
import uuid
from pathlib import Path
from django.conf import settings
from decimal import Decimal, InvalidOperation
from io import BytesIO
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Count, Q, Exists, OuterRef, Subquery, DecimalField, Value, F
from django.db.models.functions import Coalesce, Greatest
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.dateparse import parse_date
from openpyxl import load_workbook
from django.core.files.base import ContentFile
from django.core.files import File
from django.utils.text import get_valid_filename
from django.core.paginator import Paginator

from alunos.models import Aluno
from frequencia.models import FrequenciaAluno
from core.file_storage import salvar_arquivo_geredu
from core.working_days import eh_dia_letivo, feriados_fixos_geredu
logger = logging.getLogger(__name__)

from .models import (
    AcaoBuscaAtiva, AcessoConsultaAluno, ImportacaoInfrequencia,
    SituacaoInfrequencia, HistoricoSituacaoInfrequencia, ConsultaFrequenciaLog, ComunicadoSistema,
    LeituraComunicado, CalendarioEscolar, DiaNaoLetivo, ImportacaoLote,
)


def gerencial(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, "pode_gerenciar_usuarios", False))


def _percent(value):
    if value in (None, ""):
        return Decimal("0")
    try:
        n = Decimal(str(value).replace("%", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal("0")
    # A planilha oficial armazena percentuais como fração (0.30 = 30%).
    if Decimal("0") <= n <= Decimal("1.5"):
        n *= 100
    return n.quantize(Decimal("0.01"))




def _sqlite_value(row, key, default=None):
    """Lê coluna opcional de backups SQLite de versões diferentes."""
    try:
        return row[key] if key in row.keys() else default
    except (AttributeError, IndexError, KeyError):
        return default

def _decimal_import(value):
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _snapshot_situacao(situacao):
    """Serializa somente valores primitivos para manter fotografia independente."""
    campos = ("codigo_fonte", "codigo_ged", "percentual_geral", "percentual_geral_final",
              "percentual_1_bim", "percentual_2_bim", "percentual_3_bim", "percentual_4_bim",
              "percentual_relatorio_25", "consta_relatorio_25", "faltas_geral", "faltas_final",
              "carga_horaria", "paed_na_fonte")
    return {campo: (str(getattr(situacao, campo)) if isinstance(getattr(situacao, campo), Decimal)
                    else getattr(situacao, campo)) for campo in campos}


def _active_action_subquery():
    today = timezone.localdate()
    return AcaoBuscaAtiva.objects.filter(
        aluno_id=OuterRef("aluno_id")
    ).exclude(status__in=["Concluída", "Cancelada"])


@login_required
@user_passes_test(gerencial)
def painel(request):
    """Fila de atendimento: só mostra sem ação vigente; concluídos reaparecem
    apenas quando uma importação posterior volta a sinalizar o estudante."""
    today = timezone.localdate()
    situacoes = SituacaoInfrequencia.objects.select_related("aluno", "aluno__turma").filter(ano_letivo=today.year)
    ultima_importacao = HistoricoSituacaoInfrequencia.objects.filter(
        aluno_id=OuterRef("aluno_id"), ano_letivo=today.year
    ).order_by("-importado_em")
    acao_concluida = AcaoBuscaAtiva.objects.filter(
        aluno_id=OuterRef("aluno_id"), status="Concluída"
    ).order_by("-atualizado_em")
    acao_vigente = AcaoBuscaAtiva.objects.filter(
        aluno_id=OuterRef("aluno_id")
    ).exclude(status__in=["Concluída", "Cancelada"])
    base = situacoes.annotate(
        ultima_integracao=Subquery(ultima_importacao.values("importado_em")[:1]),
        concluida_em=Subquery(acao_concluida.values("atualizado_em")[:1]),
        tem_acao_vigente=Exists(acao_vigente),
        tem_prazo_ativo=Exists(acao_vigente),
    ).annotate(
        concluido_apos_integracao=Q(concluida_em__isnull=False) &
            Q(ultima_integracao__isnull=False) & Q(concluida_em__gte=F("ultima_integracao"))
    ).annotate(
        percentual_considerado_db=Greatest("percentual_geral_final", "percentual_geral", "percentual_relatorio_25")
    )
    q = request.GET.get("q", "").strip()
    faixa = request.GET.get("faixa", "")
    turno = request.GET.get("turno", "")
    turma = request.GET.get("turma", "")
    percentual_min = request.GET.get("percentual_min", "").strip()
    percentual_max = request.GET.get("percentual_max", "").strip()
    base = base.filter(tem_acao_vigente=False).exclude(concluido_apos_integracao=True)
    if q:
        base = base.filter(Q(aluno__nome__icontains=q) | Q(aluno__matricula__icontains=q))
    if turno:
        base = base.filter(aluno__turma__turno=turno)
    if turma:
        base = base.filter(aluno__turma_id=turma)
    if percentual_min:
        try: base = base.filter(percentual_considerado_db__gte=Decimal(percentual_min))
        except InvalidOperation: pass
    if percentual_max:
        try: base = base.filter(percentual_considerado_db__lte=Decimal(percentual_max))
        except InvalidOperation: pass
    if faixa == "critico":
        base = base.filter(Q(percentual_geral_final__gte=25) | Q(percentual_geral__gte=25) | Q(percentual_relatorio_25__gte=25))
    elif faixa == "atencao":
        base = base.filter(Q(percentual_geral_final__gte=10) | Q(percentual_geral__gte=10) | Q(percentual_relatorio_25__gte=10)).exclude(
            Q(percentual_geral_final__gte=25) | Q(percentual_geral__gte=25) | Q(percentual_relatorio_25__gte=25))
    base = base.order_by("-percentual_considerado_db", "aluno__nome")
    pendentes = base
    total_estudantes = base.count()
    pagina_situacoes = Paginator(base, 50).get_page(request.GET.get("page"))
    from turmas.models import Turma
    turmas = Turma.objects.all().order_by("nome")
    turnos = getattr(Turma, "TURNOS", [])
    # Painéis complementares: não misturam ações em curso com a fila de novas ações.
    acoes_vencidas = AcaoBuscaAtiva.objects.filter(
        prazo__lt=today
    ).exclude(status__in=["Concluída", "Cancelada"]).select_related(
        "aluno", "aluno__turma", "responsavel"
    ).order_by("prazo", "aluno__nome")[:100]
    acoes_ativas = AcaoBuscaAtiva.objects.filter(
        Q(prazo__gte=today) | Q(prazo__isnull=True),
    ).exclude(status__in=["Concluída", "Cancelada"]).select_related(
        "aluno", "aluno__turma", "responsavel"
    ).order_by("prazo", "aluno__nome")[:100]
    alunos_prioridade = base.filter(
        Q(percentual_geral_final__gte=25) | Q(percentual_geral__gte=25) | Q(percentual_relatorio_25__gte=25)
    ).order_by("-percentual_geral_final", "aluno__nome")[:30]
    context = {
        "acoes_vencidas": acoes_vencidas,
        "total_acoes_vencidas": AcaoBuscaAtiva.objects.filter(prazo__lt=today).exclude(status__in=["Concluída", "Cancelada"]).count(),
        "acoes_ativas": acoes_ativas,
        "alunos_prioridade": alunos_prioridade,
        "situacoes": pagina_situacoes, "pagina_situacoes": pagina_situacoes,
        "total_estudantes": total_estudantes,
        "total_criticos": pendentes.filter(Q(percentual_geral_final__gte=25) | Q(percentual_geral__gte=25) | Q(percentual_relatorio_25__gte=25)).count(),
        "total_atencao": pendentes.filter(Q(percentual_geral_final__gte=10) | Q(percentual_geral__gte=10) | Q(percentual_relatorio_25__gte=10)).exclude(Q(percentual_geral_final__gte=25) | Q(percentual_geral__gte=25) | Q(percentual_relatorio_25__gte=25)).count(),
        "acoes_pendentes": AcaoBuscaAtiva.objects.filter(prazo__gte=today).exclude(status__in=["Concluída", "Cancelada"]).count(),
        "q": q, "faixa": faixa, "turno": turno, "turma": turma,
        "percentual_min": percentual_min, "percentual_max": percentual_max,
        "turmas": turmas, "turnos": turnos,
        "importacoes": ImportacaoInfrequencia.objects.all()[:10],
        "ultimos_repetidos": HistoricoSituacaoInfrequencia.objects.filter(apareceu_novamente=True).select_related("aluno", "importacao").order_by("-importado_em")[:12],
    }
    return render(request, "busca_ativa/painel.html", context)


@login_required
@user_passes_test(gerencial)
def relatorio_25mais(request):
    """Fila exclusiva do relatório oficial de 25%+, sem misturar com os demais alertas."""
    hoje = timezone.localdate()
    qs = SituacaoInfrequencia.objects.filter(
        ano_letivo=hoje.year, consta_relatorio_25=True
    ).select_related("aluno", "aluno__turma", "importacao")
    q = request.GET.get("q", "").strip()
    turno = request.GET.get("turno", "")
    turma = request.GET.get("turma", "")
    if q:
        qs = qs.filter(Q(aluno__nome__icontains=q) | Q(aluno__matricula__icontains=q))
    if turno:
        qs = qs.filter(aluno__turma__turno=turno)
    if turma:
        qs = qs.filter(aluno__turma_id=turma)

    # Quem já recebeu providência aberta/em andamento sai da fila de novas cobranças.
    acao_aberta = AcaoBuscaAtiva.objects.filter(
        aluno_id=OuterRef("aluno_id")
    ).exclude(status__in=["Concluída", "Cancelada"])
    ultima_importacao = HistoricoSituacaoInfrequencia.objects.filter(
        aluno_id=OuterRef("aluno_id"), ano_letivo=hoje.year
    ).order_by("-importado_em")
    ultima_conclusao = AcaoBuscaAtiva.objects.filter(
        aluno_id=OuterRef("aluno_id"), status="Concluída"
    ).order_by("-atualizado_em")
    qs = qs.annotate(
        tem_acao_aberta=Exists(acao_aberta),
        ultima_integracao=Subquery(ultima_importacao.values("importado_em")[:1]),
        concluida_em=Subquery(ultima_conclusao.values("atualizado_em")[:1]),
    ).annotate(
        concluido_apos_integracao=Q(concluida_em__isnull=False) &
        Q(ultima_integracao__isnull=False) & Q(concluida_em__gte=F("ultima_integracao"))
    )
    qs = qs.filter(tem_acao_aberta=False).exclude(concluido_apos_integracao=True)
    qs = qs.order_by("-percentual_relatorio_25", "-percentual_geral_final", "aluno__nome")
    from turmas.models import Turma
    pagina = Paginator(qs, 50).get_page(request.GET.get("page"))
    return render(request, "busca_ativa/relatorio_25mais.html", {
        "situacoes": pagina, "q": q, "turno": turno, "turma": turma,
        "turmas": Turma.objects.all().order_by("nome"),
        "turnos": Turma.TURNOS, "total": qs.count(),
    })


@login_required
@user_passes_test(gerencial)
def painel_alertas(request):
    """Central de alertas com prazos, prioridade e filtros operacionais."""
    from datetime import timedelta
    from turmas.models import Turma
    hoje = timezone.localdate()
    turno = request.GET.get("turno", "")
    turma = request.GET.get("turma", "")
    q = request.GET.get("q", "").strip()
    acoes = AcaoBuscaAtiva.objects.select_related("aluno", "aluno__turma", "responsavel").exclude(status__in=["Concluída", "Cancelada"])
    if turno: acoes = acoes.filter(aluno__turma__turno=turno)
    if turma: acoes = acoes.filter(aluno__turma_id=turma)
    if q: acoes = acoes.filter(Q(aluno__nome__icontains=q) | Q(aluno__matricula__icontains=q))
    vencidas = acoes.filter(prazo__lt=hoje).order_by("prazo", "aluno__nome")
    proximas = acoes.filter(prazo__gte=hoje, prazo__lte=hoje + timedelta(days=7)).order_by("prazo", "aluno__nome")
    sem_prazo = acoes.filter(prazo__isnull=True).order_by("-data", "aluno__nome")
    prioridade = SituacaoInfrequencia.objects.filter(ano_letivo=hoje.year, consta_relatorio_25=True).select_related("aluno", "aluno__turma")
    acao_aberta = AcaoBuscaAtiva.objects.filter(aluno_id=OuterRef("aluno_id")).exclude(status__in=["Concluída", "Cancelada"])
    ultima_integracao = HistoricoSituacaoInfrequencia.objects.filter(aluno_id=OuterRef("aluno_id"), ano_letivo=hoje.year).order_by("-importado_em")
    ultima_conclusao = AcaoBuscaAtiva.objects.filter(aluno_id=OuterRef("aluno_id"), status="Concluída").order_by("-atualizado_em")
    prioridade = prioridade.annotate(
        tem_acao_aberta=Exists(acao_aberta),
        ultima_integracao=Subquery(ultima_integracao.values("importado_em")[:1]),
        concluida_em=Subquery(ultima_conclusao.values("atualizado_em")[:1]),
    ).annotate(
        concluido_apos_integracao=Q(concluida_em__isnull=False) & Q(ultima_integracao__isnull=False) & Q(concluida_em__gte=F("ultima_integracao"))
    ).filter(tem_acao_aberta=False).exclude(concluido_apos_integracao=True).order_by("-percentual_relatorio_25", "aluno__nome")
    if turno: prioridade = prioridade.filter(aluno__turma__turno=turno)
    if turma: prioridade = prioridade.filter(aluno__turma_id=turma)
    if q: prioridade = prioridade.filter(Q(aluno__nome__icontains=q) | Q(aluno__matricula__icontains=q))
    return render(request, "busca_ativa/alertas_operacionais.html", {
        "vencidas": vencidas[:200], "proximas": proximas[:200], "sem_prazo": sem_prazo[:200],
        "prioridade": prioridade[:200], "total_vencidas": vencidas.count(),
        "total_proximas": proximas.count(), "total_sem_prazo": sem_prazo.count(),
        "total_prioridade": prioridade.count(), "q": q, "turno": turno, "turma": turma,
        "turnos": Turma.TURNOS, "turmas": Turma.objects.all().order_by("nome"),
    })


@login_required
@user_passes_test(gerencial)
def lancamentos_atuais(request):
    """Mostra a fotografia integral da importação mais recente, sem apagar snapshots anteriores."""
    importacao = ImportacaoInfrequencia.objects.order_by("-criado_em").first()
    historico = HistoricoSituacaoInfrequencia.objects.filter(
        importacao=importacao
    ).select_related("aluno", "aluno__turma") if importacao else HistoricoSituacaoInfrequencia.objects.none()
    q = request.GET.get("q", "").strip()
    turno = request.GET.get("turno", "")
    turma = request.GET.get("turma", "")
    faixa = request.GET.get("faixa", "")
    if q:
        historico = historico.filter(Q(aluno__nome__icontains=q) | Q(matricula__icontains=q))
    if turno:
        historico = historico.filter(aluno__turma__turno=turno)
    if turma:
        historico = historico.filter(aluno__turma_id=turma)
    if faixa in {"25mais", "10a249", "abaixo10"}:
        if faixa == "25mais":
            historico = historico.filter(percentual_considerado__gte=25)
        elif faixa == "10a249":
            historico = historico.filter(percentual_considerado__gte=10, percentual_considerado__lt=25)
        else:
            historico = historico.filter(percentual_considerado__lt=10)
    from turmas.models import Turma
    pagina = Paginator(historico.order_by("-percentual_considerado", "aluno__nome"), 50).get_page(request.GET.get("page"))
    return render(request, "busca_ativa/lancamentos_atuais.html", {
        "importacao": importacao, "registros": pagina, "total": historico.count(),
        "q": q, "turno": turno, "turma": turma, "faixa": faixa,
        "turmas": Turma.objects.all().order_by("nome"), "turnos": Turma.TURNOS,
    })


@login_required
@user_passes_test(gerencial)
def ficha_aluno(request, aluno_id):
    aluno = get_object_or_404(Aluno.objects.select_related("turma"), pk=aluno_id)
    situacao = SituacaoInfrequencia.objects.select_related("importacao").filter(aluno=aluno).order_by("-ano_letivo").first()
    acoes = aluno.acoes_busca_ativa.select_related("responsavel").all()
    historico_importacoes = HistoricoSituacaoInfrequencia.objects.filter(aluno=aluno).select_related("importacao").order_by("-importado_em")[:12]
    resumo_diario = FrequenciaAluno.objects.filter(aluno=aluno).aggregate(
        total=Count("id"), faltas=Count("id", filter=Q(presente=False)),
        presencas=Count("id", filter=Q(presente=True))
    )
    resumo_diario["percentual"] = round((resumo_diario["presencas"] / resumo_diario["total"] * 100), 1) if resumo_diario["total"] else 0
    acesso = getattr(aluno, "acesso_consulta_frequencia", None)
    link = request.build_absolute_uri(f"/consulta-frequencia/{acesso.token}/") if acesso and acesso.ativo else ""
    return render(request, "busca_ativa/ficha.html", {
        "aluno": aluno, "situacao": situacao, "acoes": acoes,
        "historico_importacoes": historico_importacoes, "resumo_diario": resumo_diario,
        "acesso": acesso, "link_consulta": link, "status_choices": AcaoBuscaAtiva.STATUS,
    })


@login_required
@user_passes_test(gerencial)
def registrar_acao(request, aluno_id):
    aluno = get_object_or_404(Aluno, pk=aluno_id)
    if request.method == "POST":
        data = request.POST.get("data") or timezone.localdate().isoformat()
        tipo = request.POST.get("tipo", "")
        descricao = request.POST.get("descricao", "").strip()
        prazo = request.POST.get("prazo") or None
        resultado = request.POST.get("resultado", "").strip()
        proxima = request.POST.get("proxima_acao", "").strip()
        situacao_atual = SituacaoInfrequencia.objects.filter(aluno=aluno).order_by("-ano_letivo").first()
        exige_prazo = True
        if not descricao:
            messages.error(request, "Descreva a providência realizada.")
        elif not tipo:
            messages.error(request, "Selecione o tipo de ação.")
        elif not prazo:
            messages.error(request, "Informe a data de retorno/reavaliação para manter o estudante em acompanhamento até o vencimento.")
        elif prazo and parse_date(prazo) and parse_date(prazo) < timezone.localdate():
            messages.error(request, "O prazo de acompanhamento não pode ser anterior à data de hoje.")
        else:
            # Impede repetição idêntica no mesmo dia, sem apagar ou sobrescrever histórico.
            duplicada = AcaoBuscaAtiva.objects.filter(
                aluno=aluno, data=data, tipo=tipo, descricao__iexact=descricao
            ).exists()
            if duplicada:
                messages.warning(request, "Essa mesma ação já está registrada para o estudante nesta data.")
            else:
                AcaoBuscaAtiva.objects.create(
                    aluno=aluno, data=data, tipo=tipo, descricao=descricao,
                    prazo=prazo, resultado=resultado, proxima_acao=proxima,
                    responsavel=request.user,
                )
                messages.success(request, "Providência registrada no histórico do estudante.")
                return redirect("busca_ativa:acompanhamentos")
    situacao_atual = SituacaoInfrequencia.objects.filter(aluno=aluno).order_by("-ano_letivo").first()
    exige_prazo = bool(situacao_atual and situacao_atual.percentual_considerado >= 10)
    return render(request, "busca_ativa/acao_form.html", {
        "aluno": aluno, "tipos": AcaoBuscaAtiva.TIPOS,
        "hoje": timezone.localdate().isoformat(), "exige_prazo": exige_prazo,
    })


@login_required
@user_passes_test(gerencial)
def gerenciar_acesso(request, aluno_id):
    aluno = get_object_or_404(Aluno, pk=aluno_id)
    acesso, _ = AcessoConsultaAluno.objects.get_or_create(aluno=aluno, defaults={"criado_por": request.user})
    if request.method == "POST":
        operacao = request.POST.get("operacao")
        if operacao == "revogar":
            acesso.ativo = False
            acesso.save(update_fields=["ativo"])
            messages.success(request, "Link público revogado.")
        elif operacao == "renovar":
            acesso.renovar(request.user)
            messages.success(request, "Novo link gerado. O link anterior deixou de funcionar.")
        elif operacao == "ativar":
            acesso.ativo = True
            acesso.save(update_fields=["ativo"])
            messages.success(request, "Acesso reativado.")
        return redirect("busca_ativa:ficha", aluno_id=aluno.id)
    return redirect("busca_ativa:ficha", aluno_id=aluno.id)


def consulta_por_codigo(request):
    """Consulta pública por matrícula + data de nascimento, sem expor se a matrícula existe."""
    erro = ""
    if request.method == "POST":
        matricula = (request.POST.get("matricula") or "").strip()
        nascimento = (request.POST.get("data_nascimento") or "").strip()
        # Limite simples por sessão para reduzir tentativas automatizadas.
        tentativas = int(request.session.get("tentativas_consulta_frequencia", 0))
        if tentativas >= 8:
            erro = "Muitas tentativas. Aguarde alguns minutos e tente novamente ou procure a secretaria."
        else:
            from datetime import date
            aluno = Aluno.objects.filter(matricula=matricula, data_nascimento=nascimento).first()
            if aluno:
                acesso, _ = AcessoConsultaAluno.objects.get_or_create(aluno=aluno, defaults={"ativo": True})
                if not acesso.ativo:
                    acesso.ativo = True
                    acesso.save(update_fields=["ativo"])
                request.session["tentativas_consulta_frequencia"] = 0
                return redirect("busca_ativa:consulta_publica", token=acesso.token)
            request.session["tentativas_consulta_frequencia"] = tentativas + 1
            erro = "Não foi possível confirmar os dados informados. Confira a matrícula e a data de nascimento."
    return render(request, "busca_ativa/consulta_codigo.html", {"erro": erro})


@login_required
def calendario_letivo(request):
    calendario = CalendarioEscolar.objects.filter(ativo=True).order_by("-data_fim_letivo").first()
    hoje = timezone.localdate()
    dias = 0
    feriados = []
    if calendario:
        feriados = list(calendario.dias_nao_letivos.all())
        datas = {item.data for item in feriados}
        # Inclui também os dois dias definidos como não letivos pela gestão.
        from types import SimpleNamespace
        for data_fixa in sorted(feriados_fixos_geredu(calendario.data_fim_letivo.year)):
            if not any(item.data == data_fixa for item in feriados):
                feriados.append(SimpleNamespace(data=data_fixa, descricao="Feriado não letivo definido pelo GerEdu"))
                datas.add(data_fixa)
        dia = hoje
        from datetime import timedelta
        while dia <= calendario.data_fim_letivo:
            if eh_dia_letivo(dia, datas):
                dias += 1
            dia += timedelta(days=1)
    return render(request, "busca_ativa/calendario_letivo.html", {
        "calendario": calendario, "dias_restantes": dias,
        "feriados": feriados, "hoje": hoje,
    })


@login_required
@user_passes_test(gerencial)
def estatisticas_consultas(request):
    por_aluno = Aluno.objects.annotate(total_consultas=Count("consultas_frequencia")).filter(total_consultas__gt=0).order_by("-total_consultas", "nome")
    return render(request, "busca_ativa/estatisticas_consultas.html", {
        "total_consultas": ConsultaFrequenciaLog.objects.count(),
        "estudantes_consultaram": por_aluno.count(),
        "consultas_hoje": ConsultaFrequenciaLog.objects.filter(consultado_em__date=timezone.localdate()).count(),
        "por_aluno": por_aluno,
        "ultimas": ConsultaFrequenciaLog.objects.select_related("aluno").all()[:30],
    })


@login_required
def comunicado_pendente_api(request):
    """API consultada globalmente para exibir atualizações sem trocar de página."""
    from django.views.decorators.http import require_http_methods
    if request.method == "POST":
        comunicado_id = request.POST.get("comunicado_id")
        if comunicado_id:
            comunicado = get_object_or_404(ComunicadoSistema, pk=comunicado_id, ativo=True)
            LeituraComunicado.objects.get_or_create(comunicado=comunicado, usuario=request.user)
    comunicado = (
        ComunicadoSistema.objects.filter(ativo=True)
        .exclude(leituras__usuario=request.user)
        .order_by("criado_em", "pk")
        .first()
    )
    total = (
        ComunicadoSistema.objects.filter(ativo=True)
        .exclude(leituras__usuario=request.user)
        .count()
    )
    if not comunicado:
        return JsonResponse({"pending": False, "total": 0})
    return JsonResponse({
        "pending": True,
        "id": comunicado.pk,
        "versao": comunicado.versao,
        "titulo": comunicado.titulo,
        "texto": comunicado.texto,
        "total": total,
    })


@login_required
@require_POST
def confirmar_comunicado(request, comunicado_id):
    comunicado = get_object_or_404(ComunicadoSistema, pk=comunicado_id, ativo=True)
    if request.POST.get("confirmacao") == "lido":
        LeituraComunicado.objects.get_or_create(
            comunicado=comunicado, usuario=request.user
        )
        messages.success(request, f"Leitura da atualização {comunicado.versao} confirmada.")
    destino = request.POST.get("next") or "home"
    # Evita redirecionamento para domínios externos.
    from django.utils.http import url_has_allowed_host_and_scheme
    if not url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        destino = "home"
    return redirect(destino)


def dispensar_assistente_natalino(request):
    if request.method == "POST":
        request.session["assistente_natalino_visto"] = timezone.localdate().isoformat()
    return redirect(request.POST.get("next") or "home")


def consulta_publica(request, token):
    acesso = AcessoConsultaAluno.objects.select_related("aluno", "aluno__turma").filter(
        token=token, ativo=True
    ).first()
    if not acesso:
        raise Http404("Link de consulta inválido ou desativado.")
    aluno = acesso.aluno
    ConsultaFrequenciaLog.objects.create(aluno=aluno, origem="link")
    acesso.ultimo_acesso = timezone.now()
    acesso.save(update_fields=["ultimo_acesso"])
    registros = FrequenciaAluno.objects.filter(aluno=aluno).select_related(
        "frequencia", "frequencia__turma"
    ).order_by("-frequencia__data")
    total = registros.count()
    faltas = registros.filter(presente=False).count()
    presencas = total - faltas
    percentual_faltas = round((faltas / total) * 100, 1) if total else 0
    situacao = SituacaoInfrequencia.objects.select_related("importacao").filter(aluno=aluno).order_by("-ano_letivo").first()
    percentual_oficial = situacao.percentual_considerado if situacao else None
    historico_mais_recente = (
        HistoricoSituacaoInfrequencia.objects.filter(
            aluno=aluno, ano_letivo=situacao.ano_letivo
        ).order_by("-importado_em").first() if situacao else None
    )
    data_atualizacao_relatorio = (
        historico_mais_recente.importado_em if historico_mais_recente else
        (situacao.importacao.criado_em if situacao and situacao.importacao_id else
         (situacao.atualizado_em if situacao else None))
    )
    faltas_oficiais = situacao.faltas_final if situacao else None
    percentual_presenca_oficial = max(0, round(100 - float(percentual_oficial), 2)) if percentual_oficial is not None else None
    limite_frequencia_legal = 75
    # Mostra separadamente os dados do diário e do relatório oficial, sem misturar denominadores.
    percentual_alerta = percentual_oficial if percentual_oficial is not None else percentual_faltas
    nivel = "critico" if percentual_alerta >= 25 else ("atencao" if percentual_alerta >= 10 else "regular")
    return render(request, "busca_ativa/consulta_publica.html", {
        "aluno": aluno, "registros": registros[:30], "total": total,
        "faltas": faltas, "presencas": presencas,
        "percentual_faltas": percentual_faltas,
        "situacao": situacao, "percentual_oficial": percentual_oficial,
        "percentual_alerta": percentual_alerta, "nivel": nivel,
        "data_atualizacao_relatorio": data_atualizacao_relatorio,
        "faltas_oficiais": faltas_oficiais,
        "percentual_presenca_oficial": percentual_presenca_oficial,
        "limite_frequencia_legal": limite_frequencia_legal,
    })


@login_required
@user_passes_test(gerencial)
def atualizar_status_acao(request, aluno_id, acao_id):
    acao = get_object_or_404(AcaoBuscaAtiva, pk=acao_id, aluno_id=aluno_id)
    if request.method == "POST":
        status = request.POST.get("status")
        if status in dict(AcaoBuscaAtiva.STATUS):
            acao.status = status
            acao.save(update_fields=["status", "atualizado_em"])
            messages.success(request, "Status da providência atualizado.")
        else:
            messages.error(request, "Status inválido.")
    return redirect("busca_ativa:ficha", aluno_id=aluno_id)



@login_required
@user_passes_test(gerencial)
def importar_backup_local(request):
    if request.method != "POST" or not request.FILES.get("arquivo"):
        messages.error(request, "Selecione o arquivo de banco SQLite.")
        return redirect("busca_ativa:painel")
    uploaded = request.FILES["arquivo"]
    nome_recebido = str(getattr(uploaded, "name", None) or "backup_busca_ativa.db").strip()
    nome_seguro = get_valid_filename(os.path.basename(nome_recebido)) or "backup_busca_ativa.db"
    if not nome_seguro.lower().endswith((".db", ".sqlite", ".sqlite3")):
        messages.error(request, "Envie um arquivo SQLite (.db, .sqlite ou .sqlite3).")
        return redirect("busca_ativa:painel")
    if uploaded.size > 200 * 1024 * 1024:
        messages.error(request, "O banco ultrapassa o limite de 200 MB. Gere um backup otimizado ou divida os dados antes de importar.")
        return redirect("busca_ativa:painel")
    temp_path = None
    conn = None
    registro_backup = None
    try:
        digest = hashlib.sha256()
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            for chunk in uploaded.chunks():
                digest.update(chunk)
                tmp.write(chunk)
            temp_path = tmp.name
        checksum_backup = digest.hexdigest()
        if ImportacaoInfrequencia.objects.filter(sha256=checksum_backup).exists():
            messages.warning(request, "Este backup já foi integrado anteriormente. Nenhum dado foi duplicado.")
            return redirect("busca_ativa:painel")
        # Verifica integridade antes de iniciar qualquer gravação no PostgreSQL/R2.
        conn = sqlite3.connect(f"file:{temp_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        integrity = conn.execute("PRAGMA quick_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise ValueError("O arquivo recebido não é um banco SQLite íntegro ou está incompleto.")
        tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"students", "actions"}.issubset(tables):
            raise ValueError("Banco incompatível: não encontrei as tabelas students e actions.")
        colunas_students = {c[1] for c in conn.execute("PRAGMA table_info(students)")}
        colunas_actions = {c[1] for c in conn.execute("PRAGMA table_info(actions)")}
        if "id" not in colunas_students or not ({"cod_aluno", "ged_mat_cod"} & colunas_students):
            raise ValueError("A tabela students não possui identificador e matrícula/código GED reconhecíveis.")
        if not {"student_id", "data", "tipo", "descricao"}.issubset(colunas_actions):
            raise ValueError("A tabela actions não possui as colunas mínimas para recuperar as providências.")
        vinculados = sem_vinculo = acoes_importadas = duplicadas = 0
        mapa = {}
        snapshots_backup = []
        historicos_anteriores = {}
        ano_backup = timezone.localdate().year
        for hist in HistoricoSituacaoInfrequencia.objects.filter(ano_letivo=ano_backup).values("aluno_id", "dados").order_by("aluno_id", "-importado_em"):
            historicos_anteriores.setdefault(hist["aluno_id"], hist["dados"])
        with transaction.atomic():
            registro_backup = ImportacaoInfrequencia.objects.create(
                arquivo=nome_seguro[:255], ano_letivo=timezone.localdate().year,
                importado_por=request.user, sha256=checksum_backup,
                observacao="Importação de banco SQLite local; dados e providências integrados sem apagar o histórico anterior."
            )
            # Reabre o arquivo temporário já validado. Evita depender do cursor/nome
            # do UploadedFile e impede que um nome nulo chegue ao backend de storage.
            with open(temp_path, "rb") as backup_stream:
                salvar_arquivo_geredu(registro_backup.arquivo_original, f'{uuid.uuid4().hex[:20]}.db', File(backup_stream, name='backup.db'), save=True)
            if registro_backup.arquivo_original.size != os.path.getsize(temp_path):
                raise IOError("O armazenamento não confirmou o tamanho integral do banco enviado. A integração foi cancelada.")
            # Resolve todas as matrículas de uma vez (em blocos) antes de percorrer
            # os estudantes. Evita duas consultas SQL por estudante e o WORKER TIMEOUT.
            students_rows = list(conn.execute("SELECT * FROM students"))
            codigos_arquivo = set()
            for student_row in students_rows:
                for campo in ("cod_aluno", "ged_mat_cod"):
                    if campo in student_row.keys():
                        codigo = str(student_row[campo] or "").strip()
                        if codigo:
                            codigos_arquivo.add(codigo)
            alunos_por_matricula = {}
            lista_codigos = list(codigos_arquivo)
            for inicio in range(0, len(lista_codigos), 1000):
                lote = lista_codigos[inicio:inicio + 1000]
                alunos_por_matricula.update({str(a.matricula).strip(): a for a in Aluno.objects.filter(matricula__in=lote).only("id", "matricula", "nome")})
            alunos_ids_lote = [a.id for a in alunos_por_matricula.values()]
            situacoes_existentes = {}
            for inicio in range(0, len(alunos_ids_lote), 1000):
                lote_ids = alunos_ids_lote[inicio:inicio + 1000]
                situacoes_existentes.update({s.aluno_id: s for s in SituacaoInfrequencia.objects.filter(ano_letivo=ano_backup, aluno_id__in=lote_ids)})
            situacoes_novas = []
            situacoes_atualizar = []
            for row in students_rows:
                codigos = [str(row[k] or "").strip() for k in ("cod_aluno", "ged_mat_cod") if k in row.keys()]
                aluno = next((alunos_por_matricula.get(c) for c in codigos if c and alunos_por_matricula.get(c)), None)
                if not aluno:
                    sem_vinculo += 1
                    continue
                mapa[row["id"]] = aluno
                ano = timezone.localdate().year
                sit = situacoes_existentes.get(aluno.pk)
                if sit is None:
                    sit = SituacaoInfrequencia(aluno=aluno, ano_letivo=ano, importacao=registro_backup)
                    situacoes_novas.append(sit)
                else:
                    sit.importacao = registro_backup
                    situacoes_atualizar.append(sit)
                campos = {
                    "codigo_fonte": str(_sqlite_value(row, "cod_aluno") or aluno.matricula)[:30],
                    "codigo_ged": str(_sqlite_value(row, "ged_mat_cod") or "")[:30],
                    "percentual_geral": _percent(_sqlite_value(row, "perc_original")), "percentual_geral_final": _percent(_sqlite_value(row, "perc_final")),
                    "percentual_1_bim": _percent(_sqlite_value(row, "perc_1b")), "percentual_2_bim": _percent(_sqlite_value(row, "perc_2b")),
                    "percentual_3_bim": _percent(_sqlite_value(row, "perc_3b")), "percentual_4_bim": _percent(_sqlite_value(row, "perc_4b")),
                    "percentual_relatorio_25": _percent(_sqlite_value(row, "perc_report25")), "consta_relatorio_25": bool(_sqlite_value(row, "report25")),
                    "faltas_geral": _sqlite_value(row, "faltas_geral") or 0, "faltas_final": _sqlite_value(row, "faltas_final") or 0,
                    "carga_horaria": _sqlite_value(row, "ch_anual") or 0, "paed_na_fonte": str(_sqlite_value(row, "paed") or "")[:10]}
                for k,val in campos.items(): setattr(sit,k,val)
                sit.atualizado_em = timezone.now()
                dados_snapshot = _snapshot_situacao(sit)
                dados_anteriores = historicos_anteriores.get(aluno.pk)
                percentual_atual = max(sit.percentual_geral_final or 0, sit.percentual_geral or 0, sit.percentual_relatorio_25 or 0)
                snapshots_backup.append(HistoricoSituacaoInfrequencia(
                    importacao=registro_backup, aluno=aluno, matricula=str(aluno.matricula), ano_letivo=ano,
                    dados=dados_snapshot, percentual_considerado=percentual_atual,
                    faixa_alerta="critico" if percentual_atual >= 25 else "atencao" if percentual_atual >= 10 else "regular",
                    apareceu_novamente=dados_anteriores is not None,
                    mudou_desde_anterior=bool(dados_anteriores is not None and dados_anteriores != dados_snapshot),
                ))
                vinculados += 1
            if situacoes_novas:
                SituacaoInfrequencia.objects.bulk_create(situacoes_novas, batch_size=500)
            if situacoes_atualizar:
                campos_atualizacao = ["codigo_fonte", "codigo_ged", "importacao", "percentual_geral", "percentual_geral_final", "percentual_1_bim", "percentual_2_bim", "percentual_3_bim", "percentual_4_bim", "percentual_relatorio_25", "consta_relatorio_25", "faltas_geral", "faltas_final", "carga_horaria", "paed_na_fonte", "atualizado_em"]
                SituacaoInfrequencia.objects.bulk_update(situacoes_atualizar, campos_atualizacao, batch_size=500)
            if snapshots_backup:
                HistoricoSituacaoInfrequencia.objects.bulk_create(snapshots_backup, batch_size=250)
            registro_backup.estudantes_repetidos = sum(1 for h in snapshots_backup if h.apareceu_novamente)
            registro_backup.vinculados = vinculados
            registro_backup.nao_vinculados = sem_vinculo
            registro_backup.total_registros = vinculados + sem_vinculo
            registro_backup.save(update_fields=["estudantes_repetidos", "vinculados", "nao_vinculados", "total_registros"])
            # Ações também são comparadas em memória: nenhuma consulta exists() por linha.
            alunos_ids = [a.id for a in mapa.values()]
            chaves_acoes_existentes = set()
            for inicio in range(0, len(alunos_ids), 1000):
                lote_ids = alunos_ids[inicio:inicio + 1000]
                chaves_acoes_existentes.update(
                    (aluno_id, str(data), tipo, descricao)
                    for aluno_id, data, tipo, descricao in AcaoBuscaAtiva.objects.filter(aluno_id__in=lote_ids).values_list("aluno_id", "data", "tipo", "descricao")
                )
            acoes_novas = []
            alunos_para_marcar = {}
            for row in conn.execute("SELECT * FROM actions ORDER BY id"):
                aluno = mapa.get(row["student_id"])
                if not aluno: continue
                data_texto = str(row["data"] or "")[:10]
                try:
                    from datetime import date as _date
                    data = _date.fromisoformat(data_texto)
                except (TypeError, ValueError):
                    continue
                tipo = str(row["tipo"] or "Outra providência")[:60]
                descricao = str(row["descricao"] or "").strip()
                if not descricao: continue
                chave = (aluno.id, str(data), tipo, descricao)
                if chave in chaves_acoes_existentes:
                    duplicadas += 1
                    continue
                chaves_acoes_existentes.add(chave)
                acoes_novas.append(AcaoBuscaAtiva(
                    aluno=aluno, data=data, tipo=tipo, descricao=descricao,
                    resultado=str(_sqlite_value(row, "resultado", '') or ""),
                    proxima_acao=str(_sqlite_value(row, "proxima_acao", '') or ""),
                    prazo=_sqlite_value(row, "prazo", None) or None,
                    status=_sqlite_value(row, "status", 'Em andamento') or "Em andamento",
                    responsavel=request.user, responsavel_origem=str(_sqlite_value(row, "responsavel", '') or "")[:150]
                ))
                if not aluno.aluno_busca_ativa:
                    aluno.aluno_busca_ativa = True
                    alunos_para_marcar[aluno.id] = aluno
            if acoes_novas:
                AcaoBuscaAtiva.objects.bulk_create(acoes_novas, batch_size=500)
            if alunos_para_marcar:
                Aluno.objects.bulk_update(list(alunos_para_marcar.values()), ["aluno_busca_ativa"], batch_size=500)
            acoes_importadas = len(acoes_novas)
            # Restaura também os históricos antigos incluídos nos backups GerEdu mais recentes.
            if "imports" in tables and "history" in tables:
                mapa_importacoes = {}
                colunas_imports = {c[1] for c in conn.execute("PRAGMA table_info(imports)")}
                for imp_row in conn.execute("SELECT * FROM imports"):
                    nome_arquivo = str(imp_row["arquivo"] or "Importação recuperada")[:255]
                    ano_imp = int(imp_row["ano_letivo"] or timezone.localdate().year) if "ano_letivo" in colunas_imports else timezone.localdate().year
                    imp_novo = ImportacaoInfrequencia.objects.create(
                        arquivo=nome_arquivo, ano_letivo=ano_imp, importado_por=request.user,
                        total_registros=(imp_row["total_registros"] or 0) if "total_registros" in colunas_imports else 0,
                        vinculados=(imp_row["vinculados"] or 0) if "vinculados" in colunas_imports else 0,
                        nao_vinculados=(imp_row["nao_vinculados"] or 0) if "nao_vinculados" in colunas_imports else 0,
                        estudantes_repetidos=(imp_row["estudantes_repetidos"] or 0) if "estudantes_repetidos" in colunas_imports else 0,
                        observacao="Histórico de importação recuperado de backup anterior."
                    )
                    mapa_importacoes[imp_row["id"]] = imp_novo.id
                matriculas_arquivo = {str(r["matricula"] or "") for r in conn.execute("SELECT DISTINCT matricula FROM history")}
                matriculas_historicas = {str(a.matricula): a.id for a in Aluno.objects.filter(matricula__in=matriculas_arquivo)}
                snapshots_recuperados = []
                for hrow in conn.execute("SELECT * FROM history"):
                    aluno_id = matriculas_historicas.get(str(hrow["matricula"] or ""))
                    importacao_id = mapa_importacoes.get(hrow["importacao_id"])
                    if not importacao_id:
                        continue
                    try:
                        dados_hist = json.loads(hrow["dados"] or "{}")
                    except (TypeError, ValueError):
                        dados_hist = {}
                    snapshots_recuperados.append(HistoricoSituacaoInfrequencia(
                        importacao_id=importacao_id, aluno_id=aluno_id,
                        matricula=str(hrow["matricula"]), ano_letivo=int(hrow["ano_letivo"] or timezone.localdate().year),
                        dados=dados_hist, percentual_considerado=_decimal_import(hrow["percentual_considerado"]),
                        faixa_alerta=str(hrow["faixa_alerta"] or ""),
                        apareceu_novamente=bool(hrow["apareceu_novamente"]),
                        mudou_desde_anterior=bool(hrow["mudou_desde_anterior"]),
                    ))
                    if len(snapshots_recuperados) >= 500:
                        HistoricoSituacaoInfrequencia.objects.bulk_create(snapshots_recuperados, batch_size=500)
                        snapshots_recuperados = []
                if snapshots_recuperados:
                    HistoricoSituacaoInfrequencia.objects.bulk_create(snapshots_recuperados, batch_size=500)
            elif "imports" in tables:
                # Compatibilidade com bancos SQLite antigos que não possuíam a tabela de snapshots.
                for imp_row in conn.execute("SELECT * FROM imports"):
                    nome_arquivo = str(imp_row["arquivo"] or "Backup da Busca Ativa")[:255]
                    if not ImportacaoInfrequencia.objects.filter(arquivo=nome_arquivo, observacao__contains="backup local").exists():
                        ImportacaoInfrequencia.objects.create(arquivo=nome_arquivo, ano_letivo=timezone.localdate().year,
                            importado_por=request.user, total_registros=imp_row["quantidade"] or 0,
                            observacao="Registro histórico recuperado de backup SQLite antigo.")
            registro_backup.observacao = f"Backup integrado: {acoes_importadas} ações recuperadas; {duplicadas} duplicadas ignoradas. Arquivo original mantido para auditoria."
            registro_backup.save(update_fields=["observacao"])
        conn.close()
        messages.success(request, f"Backup importado: {vinculados} estudantes vinculados, {acoes_importadas} providências recuperadas, {duplicadas} duplicadas ignoradas e {sem_vinculo} estudantes sem correspondência.")
    except Exception as exc:
        logger.exception("Falha ao importar backup SQLite da Busca Ativa (arquivo=%r)", nome_recebido)
        if registro_backup and registro_backup.arquivo_original:
            try:
                registro_backup.arquivo_original.storage.delete(registro_backup.arquivo_original.name)
            except Exception:
                pass
        messages.error(request, f"Falha ao importar backup ({type(exc).__name__}). Consulte os logs do servidor para o diagnóstico completo. Nenhum histórico anterior foi removido.")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        if temp_path and os.path.exists(temp_path): os.remove(temp_path)
    return redirect("busca_ativa:painel")


@login_required
@user_passes_test(gerencial)
def baixar_backup_busca_ativa(request):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        conn = sqlite3.connect(path)
        conn.executescript("""
        CREATE TABLE students (id INTEGER PRIMARY KEY,cod_aluno TEXT,ged_mat_cod TEXT,nome TEXT,turma TEXT,paed TEXT,ch_anual REAL,faltas_geral REAL,faltas_final REAL,perc_original REAL,perc_final REAL,perc_1b REAL,perc_2b REAL,perc_3b REAL,perc_4b REAL,report25 INTEGER,perc_report25 REAL);
        CREATE TABLE actions (id INTEGER PRIMARY KEY,student_id INTEGER,data TEXT,tipo TEXT,descricao TEXT,resultado TEXT,proxima_acao TEXT,prazo TEXT,responsavel TEXT,criado_em TEXT,status TEXT);
        CREATE TABLE imports (id INTEGER PRIMARY KEY,arquivo TEXT,ano_letivo INTEGER,total_registros INTEGER,vinculados INTEGER,nao_vinculados INTEGER,estudantes_repetidos INTEGER,observacao TEXT);
        CREATE TABLE history (id INTEGER PRIMARY KEY,importacao_id INTEGER,matricula TEXT,ano_letivo INTEGER,dados TEXT,percentual_considerado REAL,faixa_alerta TEXT,apareceu_novamente INTEGER,mudou_desde_anterior INTEGER);
        """)
        for s in SituacaoInfrequencia.objects.select_related("aluno").all():
            a=s.aluno
            conn.execute("INSERT INTO students VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (a.id,str(s.codigo_fonte or a.matricula),s.codigo_ged,a.nome,str(a.turma or ""),s.paed_na_fonte,
                 float(s.carga_horaria),float(s.faltas_geral),float(s.faltas_final),float(s.percentual_geral),
                 float(s.percentual_geral_final),float(s.percentual_1_bim),float(s.percentual_2_bim),
                 float(s.percentual_3_bim),float(s.percentual_4_bim),int(s.consta_relatorio_25),float(s.percentual_relatorio_25)))
        for a in AcaoBuscaAtiva.objects.select_related("aluno","responsavel").all():
            conn.execute("INSERT INTO actions VALUES (?,?,?,?,?,?,?,?,?,?,?)",(a.id,a.aluno_id,a.data.isoformat(),a.tipo,a.descricao,a.resultado,a.proxima_acao,a.prazo.isoformat() if a.prazo else None,(a.responsavel_origem or a.responsavel.get_username()),a.criado_em.isoformat(),a.status))
        for imp in ImportacaoInfrequencia.objects.all():
            conn.execute("INSERT INTO imports VALUES (?,?,?,?,?,?,?,?)", (imp.id, imp.arquivo, imp.ano_letivo, imp.total_registros, imp.vinculados, imp.nao_vinculados, imp.estudantes_repetidos, imp.observacao))
        for h in HistoricoSituacaoInfrequencia.objects.all():
            conn.execute("INSERT INTO history VALUES (?,?,?,?,?,?,?,?,?)", (h.id, h.importacao_id, h.matricula, h.ano_letivo, json.dumps(h.dados, ensure_ascii=False), float(h.percentual_considerado), h.faixa_alerta, int(h.apareceu_novamente), int(h.mudou_desde_anterior)))
        conn.commit(); conn.close()
        with open(path,"rb") as f: payload=f.read()
        resp=HttpResponse(payload,content_type="application/vnd.sqlite3")
        resp["Content-Disposition"]='attachment; filename="geredu_busca_ativa_backup.db"'
        return resp
    finally:
        if os.path.exists(path): os.remove(path)


@login_required
@user_passes_test(gerencial)
def importar_planilha(request):
    """Recebe e valida o arquivo; o processamento acontece em lotes via requisições curtas."""
    if request.method != "POST":
        return render(request, "busca_ativa/importar.html")

    arquivo = request.FILES.get("arquivo")
    tipo = request.POST.get("tipo", "geral")
    if not arquivo:
        messages.error(request, "Selecione o arquivo que deseja importar.")
        return redirect("busca_ativa:importar")
    if arquivo.size > 15 * 1024 * 1024:
        messages.error(request, "O arquivo ultrapassa o limite de 15 MB. Divida a planilha em arquivos menores.")
        return redirect("busca_ativa:importar")

    registro = None
    try:
        arquivo.seek(0)
        conteudo_arquivo = arquivo.read()
        checksum = hashlib.sha256(conteudo_arquivo).hexdigest()
        if ImportacaoInfrequencia.objects.filter(sha256=checksum).exists():
            messages.warning(request, "Este arquivo já foi importado anteriormente. O histórico foi preservado e nenhuma duplicação foi criada.")
            return redirect("busca_ativa:importar")
        arquivo.seek(0)
        dados = []
        ano = timezone.localdate().year
        if tipo == "25mais":
            if not arquivo.name.lower().endswith(".csv"):
                raise ValueError("O relatório complementar 25%+ deve ser enviado em CSV.")
            raw = arquivo.read()
            conteudo = None
            for enc in ("utf-8-sig", "cp1252", "latin1"):
                try:
                    conteudo = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            sample = conteudo[:4096]
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
            except csv.Error:
                dialect = csv.excel
                dialect.delimiter = ";"
            reader = csv.DictReader(io.StringIO(conteudo), dialect=dialect)
            obrigatorias = {"CodAluno", "PercFaltas_GeralFinal"}
            if not reader.fieldnames or not obrigatorias.issubset({x.strip() for x in reader.fieldnames}):
                raise ValueError("O CSV precisa conter CodAluno e PercFaltas_GeralFinal.")
            reader.fieldnames = [x.strip() for x in reader.fieldnames]
            for row in reader:
                codigo = str(row.get("CodAluno") or "").strip().replace(".0", "")
                if codigo:
                    dados.append({"codigo": codigo, "percentual": str(row.get("PercFaltas_GeralFinal") or "0")})
                if len(dados) > 20000:
                    raise ValueError("A planilha possui mais de 20.000 registros. Divida o arquivo para importar.")
        else:
            if tipo != "geral" or not arquivo.name.lower().endswith((".xlsx", ".xlsm")):
                raise ValueError("A base geral deve ser enviada em Excel (.xlsx ou .xlsm).")
            wb = load_workbook(arquivo, read_only=True, data_only=True)
            try:
                ws = wb.active
                rows = ws.iter_rows(values_only=True)
                headers = [str(v).strip() if v is not None else "" for v in next(rows, ())]
                ix = {name: i for i, name in enumerate(headers)}
                obrigatorias = {"CodAluno", "NomeAluno", "PercFaltas_GeralFinal"}
                if not obrigatorias.issubset(ix):
                    raise ValueError("A planilha não contém as colunas essenciais CodAluno, NomeAluno e PercFaltas_GeralFinal.")
                for row in rows:
                    if not row or ix["CodAluno"] >= len(row) or row[ix["CodAluno"]] is None:
                        continue
                    def cell(col):
                        value = row[ix[col]] if col in ix and ix[col] < len(row) else None
                        return str(value).strip() if value is not None else ""
                    codigo = cell("CodAluno").replace(".0", "")
                    ged = cell("GedMatCod").replace(".0", "")
                    if not codigo and not ged:
                        continue
                    dados.append({
                        "codigo": codigo, "ged": ged,
                        "percentual_geral": cell("PercFaltas_Geral"),
                        "percentual_final": cell("PercFaltas_GeralFinal"),
                        "bim1": cell("PercFaltasFinal_1Bim"), "bim2": cell("PercFaltasFinal_2Bim"),
                        "bim3": cell("PercFaltasFinal_3Bim"), "bim4": cell("PercFaltasFinal_4Bim"),
                        "faltas_geral": cell("TF_Geral") or "0", "faltas_final": cell("TF_Geral_Final") or "0",
                        "carga_horaria": cell("CHAnual") or "0", "paed": cell("PAED"),
                    })
                    if len(dados) > 20000:
                        raise ValueError("A planilha possui mais de 20.000 registros. Divida o arquivo para importar.")
                first = dados[0] if dados else None
                if "AnoLetivo" in ix:
                    first_row = next(ws.iter_rows(min_row=2, max_row=2, values_only=True), None)
                    if first_row and ix["AnoLetivo"] < len(first_row) and first_row[ix["AnoLetivo"]]:
                        ano = int(first_row[ix["AnoLetivo"]])
            finally:
                wb.close()

        if not dados:
            raise ValueError("O arquivo não contém registros válidos para importar.")

        with transaction.atomic():
            registro = ImportacaoInfrequencia.objects.create(
                arquivo=arquivo.name, ano_letivo=ano, importado_por=request.user, sha256=checksum
            )
            salvar_arquivo_geredu(registro.arquivo_original, get_valid_filename(os.path.basename(str(getattr(arquivo, "name", None) or "importacao.xlsx"))), ContentFile(conteudo_arquivo), save=True)
            if registro.arquivo_original.size != len(conteudo_arquivo):
                raise IOError("O armazenamento não confirmou o tamanho integral do arquivo enviado. A importação foi cancelada.")
            job = ImportacaoLote.objects.create(
                arquivo=arquivo.name, tipo=tipo, ano_letivo=ano, usuario=request.user,
                importacao=registro, dados=dados, total=len(dados), status="pendente"
            )
        return redirect("busca_ativa:processar_importacao", job_id=job.pk)
    except Exception as exc:
        if registro and registro.arquivo_original:
            try:
                registro.arquivo_original.storage.delete(registro.arquivo_original.name)
            except Exception:
                pass
        messages.error(request, f"Não foi possível preparar o arquivo: {exc}")
        return redirect("busca_ativa:importar")


@login_required
@user_passes_test(gerencial)
def processar_importacao(request, job_id):
    job = get_object_or_404(ImportacaoLote, pk=job_id, usuario=request.user)
    if request.method == "GET":
        return render(request, "busca_ativa/processando_importacao.html", {"job": job})
    if request.method != "POST":
        return JsonResponse({"erro": "Método não permitido."}, status=405)

    CHUNK_SIZE = 250
    try:
        with transaction.atomic():
            job = ImportacaoLote.objects.select_for_update().get(pk=job_id, usuario=request.user)
            if job.status in ("concluida", "erro"):
                return JsonResponse({"status": job.status, "percentual": job.percentual,
                                     "processados": job.processados, "total": job.total,
                                     "vinculados": job.vinculados, "nao_vinculados": job.nao_vinculados,
                                     "repetidos": job.importacao.estudantes_repetidos if job.importacao_id else 0,
                                     "erro": job.erro})
            job.status = "processando"
            inicio = job.processados
            lote = job.dados[inicio:inicio + CHUNK_SIZE]
            if not lote:
                job.status = "concluida"
            else:
                codigos = {r.get("codigo", "") for r in lote if r.get("codigo")}
                ged_codes = {r.get("ged", "") for r in lote if r.get("ged")}
                alunos = Aluno.objects.filter(Q(matricula__in=codigos) | Q(matricula__in=ged_codes)).only("id", "matricula")
                por_codigo = {str(a.matricula): a for a in alunos}
                alunos_lote = {}
                registros = {}
                for row in lote:
                    codigo, ged = row.get("codigo", ""), row.get("ged", "")
                    a1, a2 = por_codigo.get(codigo), por_codigo.get(ged) if ged else None
                    if job.tipo == "geral" and a1 and a2 and a1.pk != a2.pk:
                        job.nao_vinculados += 1
                        job.pendentes.append(f"{codigo}/{ged} divergentes")
                        continue
                    aluno = a1 or a2
                    if not aluno:
                        job.nao_vinculados += 1
                        job.pendentes.append(f"{codigo}/{ged}" if ged else codigo)
                        continue
                    alunos_lote[aluno.pk] = aluno
                    registros[aluno.pk] = row  # Em duplicidade, prevalece a última linha do arquivo.

                existentes = {s.aluno_id: s for s in SituacaoInfrequencia.objects.filter(
                    aluno_id__in=alunos_lote.keys(), ano_letivo=job.ano_letivo
                )}
                criar, atualizar = [], []
                agora = timezone.now()
                anteriores = {}
                for hist in HistoricoSituacaoInfrequencia.objects.filter(
                    aluno_id__in=alunos_lote.keys(), ano_letivo=job.ano_letivo
                ).exclude(importacao_id=job.importacao_id).order_by("aluno_id", "-importado_em"):
                    anteriores.setdefault(hist.aluno_id, hist)
                snapshots = []
                repetidos_lote = 0
                for aluno_id, row in registros.items():
                    situacao = existentes.get(aluno_id)
                    dados_atuais_anteriores = _snapshot_situacao(situacao) if situacao is not None else None
                    if situacao is None:
                        situacao = SituacaoInfrequencia(
                            aluno_id=aluno_id, ano_letivo=job.ano_letivo,
                            codigo_fonte=row.get("codigo") or row.get("codigo_ged") or str(alunos_lote[aluno_id].matricula)
                        )
                        criar.append(situacao)
                    if job.tipo == "25mais":
                        situacao.percentual_relatorio_25 = _percent(row.get("percentual"))
                        situacao.consta_relatorio_25 = True
                    else:
                        situacao.codigo_fonte = row.get("codigo") or str(alunos_lote[aluno_id].matricula)
                        situacao.codigo_ged = row.get("ged", "")
                        situacao.importacao_id = job.importacao_id
                        situacao.percentual_geral = _percent(row.get("percentual_geral"))
                        situacao.percentual_geral_final = _percent(row.get("percentual_final"))
                        situacao.percentual_1_bim = _percent(row.get("bim1"))
                        situacao.percentual_2_bim = _percent(row.get("bim2"))
                        situacao.percentual_3_bim = _percent(row.get("bim3"))
                        situacao.percentual_4_bim = _percent(row.get("bim4"))
                        situacao.faltas_geral = _decimal_import(row.get("faltas_geral"))
                        situacao.faltas_final = _decimal_import(row.get("faltas_final"))
                        situacao.carga_horaria = _decimal_import(row.get("carga_horaria"))
                        situacao.paed_na_fonte = (row.get("paed") or "")[:10]
                    situacao.atualizado_em = agora
                    anterior = anteriores.get(aluno_id)
                    dados_snapshot = _snapshot_situacao(situacao)
                    dados_anteriores = anterior.dados if anterior is not None else dados_atuais_anteriores
                    repetido = anterior is not None or dados_atuais_anteriores is not None
                    mudou = bool(dados_anteriores is not None and dados_anteriores != dados_snapshot)
                    snapshots.append(HistoricoSituacaoInfrequencia(
                        importacao_id=job.importacao_id, aluno_id=aluno_id,
                        matricula=str(alunos_lote[aluno_id].matricula), ano_letivo=job.ano_letivo,
                        dados=dados_snapshot, percentual_considerado=Decimal(str(max(
                            situacao.percentual_geral_final or 0, situacao.percentual_geral or 0,
                            situacao.percentual_relatorio_25 or 0))),
                        faixa_alerta=("critico" if max(situacao.percentual_geral_final or 0, situacao.percentual_geral or 0, situacao.percentual_relatorio_25 or 0) >= 25 else
                                      "atencao" if max(situacao.percentual_geral_final or 0, situacao.percentual_geral or 0, situacao.percentual_relatorio_25 or 0) >= 10 else "regular"),
                        apareceu_novamente=repetido, mudou_desde_anterior=mudou
                    ))
                    if repetido:
                        repetidos_lote += 1
                    if aluno_id in existentes:
                        atualizar.append(situacao)
                if snapshots:
                    HistoricoSituacaoInfrequencia.objects.bulk_create(snapshots, batch_size=200)
                if criar:
                    SituacaoInfrequencia.objects.bulk_create(criar, batch_size=200)
                if atualizar:
                    campos = ["percentual_relatorio_25", "consta_relatorio_25", "codigo_fonte", "codigo_ged",
                              "importacao", "percentual_geral", "percentual_geral_final", "percentual_1_bim",
                              "percentual_2_bim", "percentual_3_bim", "percentual_4_bim", "faltas_geral",
                              "faltas_final", "carga_horaria", "paed_na_fonte", "atualizado_em"]
                    SituacaoInfrequencia.objects.bulk_update(atualizar, campos, batch_size=200)
                job.vinculados += len(registros)
                job.importacao.estudantes_repetidos = (job.importacao.estudantes_repetidos or 0) + repetidos_lote
                job.importacao.save(update_fields=["estudantes_repetidos"])
                job.processados = min(job.total, inicio + len(lote))
                if job.processados >= job.total:
                    if job.tipo == "25mais":
                        # O relatório 25%+ é uma fotografia: quem não veio nesta nova planilha
                        # deixa de aparecer na fila atual, mas seus snapshots anteriores permanecem.
                        ids_no_relatorio = HistoricoSituacaoInfrequencia.objects.filter(
                            importacao_id=job.importacao_id, aluno_id__isnull=False
                        ).values_list("aluno_id", flat=True)
                        SituacaoInfrequencia.objects.filter(
                            ano_letivo=job.ano_letivo, consta_relatorio_25=True
                        ).exclude(aluno_id__in=ids_no_relatorio).update(
                            consta_relatorio_25=False, percentual_relatorio_25=0
                        )
                    job.status = "concluida"
                    job.importacao.total_registros = job.total
                    job.importacao.vinculados = job.vinculados
                    job.importacao.nao_vinculados = job.nao_vinculados
                    resumo = "Códigos sem vínculo ou ambíguos: " + "; ".join(job.pendentes[:300])
                    job.importacao.observacao = resumo
                    job.importacao.save(update_fields=["total_registros", "vinculados", "nao_vinculados", "observacao"])
                    job.dados = []  # libera espaço após conclusão
                job.save()
        return JsonResponse({"status": job.status, "percentual": job.percentual,
                             "processados": job.processados, "total": job.total,
                             "vinculados": job.vinculados, "nao_vinculados": job.nao_vinculados,
                             "repetidos": job.importacao.estudantes_repetidos if job.importacao_id else 0,
                             "erro": job.erro})
    except Exception as exc:
        ImportacaoLote.objects.filter(pk=job_id, usuario=request.user).update(status="erro", erro=str(exc)[:2000])
        return JsonResponse({"status": "erro", "erro": str(exc)[:2000]}, status=500)


@login_required
@user_passes_test(gerencial)
def historico_importacao(request, importacao_id):
    importacao = get_object_or_404(ImportacaoInfrequencia, pk=importacao_id)
    historico = HistoricoSituacaoInfrequencia.objects.filter(importacao=importacao).select_related("aluno", "aluno__turma")
    repetidos = historico.filter(apareceu_novamente=True).order_by("-percentual_considerado", "aluno__nome")
    return render(request, "busca_ativa/historico_importacao.html", {
        "importacao": importacao, "historico": historico.order_by("aluno__nome"),
        "repetidos": repetidos, "total_repetidos": repetidos.count(),
        "total_historico": historico.count(),
    })


@login_required
@user_passes_test(gerencial)
def relatorio_acoes(request):
    acoes = AcaoBuscaAtiva.objects.select_related("aluno", "aluno__turma", "responsavel")
    status = request.GET.get("status", "")
    tipo = request.GET.get("tipo", "")
    q = request.GET.get("q", "").strip()
    turno = request.GET.get("turno", "")
    inicio, fim = request.GET.get("inicio"), request.GET.get("fim")
    if status: acoes = acoes.filter(status=status)
    if tipo: acoes = acoes.filter(tipo=tipo)
    if turno: acoes = acoes.filter(aluno__turma__turno=turno)
    if q: acoes = acoes.filter(Q(aluno__nome__icontains=q) | Q(aluno__matricula__icontains=q) | Q(descricao__icontains=q) | Q(responsavel_origem__icontains=q))
    if inicio: acoes = acoes.filter(data__gte=inicio)
    if fim: acoes = acoes.filter(data__lte=fim)
    if request.GET.get("csv") == "1":
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = 'attachment; filename="relatorio_busca_ativa.csv"'
        writer = csv.writer(response, delimiter=";")
        writer.writerow(["Estudante", "Matrícula", "Turma", "Turno", "Data", "Tipo", "Descrição", "Resultado", "Próxima ação", "Prazo", "Status", "Responsável"])
        for a in acoes:
            responsavel = a.responsavel_origem or a.responsavel.get_full_name() or a.responsavel.username
            writer.writerow([a.aluno.nome, a.aluno.matricula, str(a.aluno.turma or ""), a.aluno.turma.get_turno_display() if a.aluno.turma else "", a.data, a.get_tipo_display(), a.descricao, a.resultado, a.proxima_acao, a.prazo or "", a.status, responsavel])
        return response
    return render(request, "busca_ativa/relatorio.html", {
        "acoes": acoes[:1500], "status": status, "tipo": tipo, "q": q, "turno": turno,
        "inicio": inicio, "fim": fim, "tipos": AcaoBuscaAtiva.TIPOS,
        "status_choices": AcaoBuscaAtiva.STATUS,
        "turnos": [(v, l) for v, l in __import__("turmas.models", fromlist=["Turma"]).Turma.TURNOS],
    })


@login_required
@user_passes_test(gerencial)
def compensacao_ausencias(request):
    """Uma linha por estudante no período, sempre com o lançamento mais recente."""
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    inicio, fim = request.GET.get("inicio", ""), request.GET.get("fim", "")
    base = AcaoBuscaAtiva.objects.filter(tipo__in=["Compensação de Ausências", "Compensação de ausências"])
    if inicio: base = base.filter(data__gte=inicio)
    if fim: base = base.filter(data__lte=fim)
    if status: base = base.filter(status=status)
    if q: base = base.filter(Q(aluno__nome__icontains=q) | Q(aluno__matricula__icontains=q) | Q(descricao__icontains=q))
    alunos = Aluno.objects.filter(acoes_busca_ativa__in=base).select_related("turma").distinct()
    latest = base.filter(aluno_id=OuterRef("pk")).order_by("-data", "-criado_em")
    alunos = alunos.annotate(
        compensacao_data=Subquery(latest.values("data")[:1]),
        compensacao_status=Subquery(latest.values("status")[:1]),
        compensacao_descricao=Subquery(latest.values("descricao")[:1]),
        compensacao_prazo=Subquery(latest.values("prazo")[:1]),
        compensacao_responsavel=Subquery(latest.values("responsavel_origem")[:1]),
    ).order_by("nome")
    if request.GET.get("csv") == "1":
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = 'attachment; filename="compensacao_ausencias_geredu.csv"'
        writer = csv.writer(response, delimiter=";")
        writer.writerow(["Estudante", "Matrícula", "Turma", "Data", "Descrição", "Prazo", "Status", "Responsável"])
        for a in alunos:
            writer.writerow([a.nome, a.matricula, str(a.turma or ""), a.compensacao_data or "", a.compensacao_descricao or "", a.compensacao_prazo or "", a.compensacao_status or "", a.compensacao_responsavel or ""])
        return response
    return render(request, "busca_ativa/compensacao.html", {"alunos": alunos, "q": q, "status": status, "inicio": inicio, "fim": fim, "status_choices": AcaoBuscaAtiva.STATUS})


@login_required
@user_passes_test(gerencial)
def relatorios_personalizados(request):
    """Relatórios configuráveis, com seleção de campos e saída para impressão/CSV."""
    hoje = timezone.localdate()
    tipo = request.GET.get("tipo", "estudantes")
    if tipo not in ["estudantes", "acoes", "compensacao", "alertas"]: tipo = "estudantes"
    q = request.GET.get("q", "").strip()
    inicio, fim = request.GET.get("inicio", ""), request.GET.get("fim", "")
    turno, faixa = request.GET.get("turno", ""), request.GET.get("faixa", "")
    paed = request.GET.get("paed", "")
    tipo_acao, status = request.GET.get("tipo_acao", ""), request.GET.get("status", "")
    field_sets = {
        "estudantes": [("nome", "Estudante"), ("matricula", "Matrícula"), ("turma", "Turma"), ("turno", "Turno"), ("nascimento", "Nascimento"), ("paed", "PAED"), ("percentual", "Infrequência"), ("faltas", "Faltas"), ("situacao", "Situação escolar")],
        "acoes": [("estudante", "Estudante"), ("matricula", "Matrícula"), ("turma", "Turma"), ("tipo", "Tipo de ação"), ("data", "Data"), ("descricao", "Descrição"), ("resultado", "Resultado"), ("proxima", "Próxima ação"), ("prazo", "Prazo"), ("responsavel", "Responsável"), ("status", "Status")],
        "compensacao": [("estudante", "Estudante"), ("matricula", "Matrícula"), ("turma", "Turma"), ("turno", "Turno"), ("data", "Data do lançamento"), ("descricao", "Descrição"), ("prazo", "Prazo"), ("status", "Status")],
        "alertas": [("estudante", "Estudante"), ("matricula", "Matrícula"), ("turma", "Turma"), ("turno", "Turno"), ("percentual", "Infrequência"), ("paed", "PAED"), ("ultima_acao", "Última ação"), ("prazo", "Prazo")],
    }
    options = field_sets[tipo]
    selected = request.GET.getlist("campos")
    valid_keys = [k for k, _ in options]
    if not selected: selected = valid_keys[:]
    selected = [k for k in selected if k in valid_keys]
    if not selected: selected = valid_keys[:]
    rows = []

    def faixa_ok(pct):
        if not faixa: return True
        if faixa == "abaixo10": return pct < 10
        if faixa == "10a149": return 10 <= pct < 15
        if faixa == "15a249": return 15 <= pct < 25
        if faixa == "25mais": return pct >= 25
        return True

    def aluno_ok(aluno):
        if q and q.lower() not in (aluno.nome or "").lower() and q not in (aluno.matricula or ""): return False
        if turno and (not aluno.turma or aluno.turma.turno != turno): return False
        return True

    if tipo == "estudantes":
        qs = Aluno.objects.select_related("turma").all().order_by("nome")
        situacoes = {s.aluno_id: s for s in SituacaoInfrequencia.objects.filter(ano_letivo=hoje.year)}
        for a in qs:
            if not aluno_ok(a): continue
            sit = situacoes.get(a.id)
            pct = sit.percentual_considerado if sit else 0
            if not faixa_ok(pct): continue
            paed_flag = a.aluno_paed or bool(sit and str(sit.paed_na_fonte).strip().upper() in ["SIM", "S", "1", "TRUE"])
            if paed == "sim" and not paed_flag: continue
            if paed == "nao" and paed_flag: continue
            data = {"nome": a.nome, "matricula": a.matricula, "turma": str(a.turma or "—"), "turno": a.turma.get_turno_display() if a.turma else "—", "nascimento": a.data_nascimento.strftime("%d/%m/%Y") if a.data_nascimento else "—", "paed": "Sim" if paed_flag else "Não", "percentual": f"{pct:.1f}%", "faltas": str(sit.faltas_final if sit else "—"), "situacao": a.situacao or "—"}
            rows.append({"values": [data[k] for k in selected], "aluno_id": a.id})
    elif tipo in ["acoes", "compensacao"]:
        qs = AcaoBuscaAtiva.objects.select_related("aluno", "aluno__turma", "responsavel").all()
        ids_alunos = qs.values_list("aluno_id", flat=True).distinct()
        situacoes = {s.aluno_id: s for s in SituacaoInfrequencia.objects.filter(ano_letivo=hoje.year, aluno_id__in=ids_alunos)}
        if tipo == "compensacao": qs = qs.filter(tipo__in=["Compensação de Ausências", "Compensação de ausências"])
        if inicio: qs = qs.filter(data__gte=inicio)
        if fim: qs = qs.filter(data__lte=fim)
        if tipo_acao and tipo == "acoes": qs = qs.filter(tipo=tipo_acao)
        if status: qs = qs.filter(status=status)
        if q: qs = qs.filter(Q(aluno__nome__icontains=q) | Q(aluno__matricula__icontains=q) | Q(descricao__icontains=q) | Q(responsavel_origem__icontains=q))
        if turno: qs = qs.filter(aluno__turma__turno=turno)
        for a in qs.order_by("-data", "aluno__nome"):
            sit = situacoes.get(a.aluno_id)
            pct = sit.percentual_considerado if sit else 0
            paed_flag = a.aluno.aluno_paed or bool(sit and str(sit.paed_na_fonte).strip().upper() in ["SIM", "S", "1", "TRUE"])
            if paed == "sim" and not paed_flag: continue
            if paed == "nao" and paed_flag: continue
            if not faixa_ok(pct): continue
            if tipo == "compensacao":
                # Um único lançamento por estudante no período, sempre o mais recente.
                if any(r.get("aluno_id") == a.aluno_id for r in rows): continue
                data = {"estudante": a.aluno.nome, "matricula": a.aluno.matricula, "turma": str(a.aluno.turma or "—"), "turno": a.aluno.turma.get_turno_display() if a.aluno.turma else "—", "data": a.data.strftime("%d/%m/%Y"), "descricao": a.descricao, "prazo": a.prazo.strftime("%d/%m/%Y") if a.prazo else "—", "status": a.get_status_display()}
            else:
                data = {"estudante": a.aluno.nome, "matricula": a.aluno.matricula, "turma": str(a.aluno.turma or "—"), "tipo": a.get_tipo_display(), "data": a.data.strftime("%d/%m/%Y"), "descricao": a.descricao, "resultado": a.resultado or "—", "proxima": a.proxima_acao or "—", "prazo": a.prazo.strftime("%d/%m/%Y") if a.prazo else "—", "responsavel": a.responsavel_origem or a.responsavel.get_full_name() or a.responsavel.username, "status": a.get_status_display()}
            rows.append({"values": [data.get(k, "—") for k in selected], "aluno_id": a.aluno_id})
    else:
        qs = SituacaoInfrequencia.objects.select_related("aluno", "aluno__turma").filter(ano_letivo=hoje.year)
        qs = qs.annotate(tem_prazo_ativo=Exists(AcaoBuscaAtiva.objects.filter(aluno_id=OuterRef("aluno_id"), prazo__gte=hoje).exclude(status__in=["Concluída", "Cancelada"]))).filter(tem_prazo_ativo=False)
        from django.db.models import Prefetch
        acoes_recentes = AcaoBuscaAtiva.objects.order_by("-data", "-criado_em")
        qs = qs.prefetch_related(Prefetch("aluno__acoes_busca_ativa", queryset=acoes_recentes, to_attr="_acoes_busca_ativa_cache"))
        for sit in qs.order_by("-percentual_geral_final", "aluno__nome"):
            a = sit.aluno
            if not aluno_ok(a): continue
            pct = sit.percentual_considerado
            if pct < 10 or not faixa_ok(pct): continue
            paed_flag = a.aluno_paed or str(sit.paed_na_fonte).strip().upper() in ["SIM", "S", "1", "TRUE"]
            if paed == "sim" and not paed_flag: continue
            if paed == "nao" and paed_flag: continue
            ultima = a._acoes_busca_ativa_cache[0] if a._acoes_busca_ativa_cache else None
            paed_flag = a.aluno_paed or str(sit.paed_na_fonte).strip().upper() in ["SIM", "S", "1", "TRUE"]
            data = {"estudante": a.nome, "matricula": a.matricula, "turma": str(a.turma or "—"), "turno": a.turma.get_turno_display() if a.turma else "—", "percentual": f"{pct:.1f}%", "paed": "Sim" if paed_flag else "Não", "ultima_acao": ultima.get_tipo_display() if ultima else "—", "prazo": ultima.prazo.strftime("%d/%m/%Y") if ultima and ultima.prazo else "—"}
            rows.append({"values": [data[k] for k in selected], "aluno_id": a.id})

    headers = [label for key, label in options if key in selected]
    if request.GET.get("csv") == "1":
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = f'attachment; filename="relatorio_busca_ativa_{tipo}.csv"'
        writer = csv.writer(response, delimiter=";")
        writer.writerow(headers)
        for row in rows: writer.writerow(row["values"])
        return response
    return render(request, "busca_ativa/relatorios_personalizados.html", {
        "tipo": tipo, "tipos_relatorio": [("estudantes", "Relação de estudantes"), ("acoes", "Providências e tratativas"), ("compensacao", "Compensação de ausências"), ("alertas", "Alertas ativos")],
        "q": q, "inicio": inicio, "fim": fim, "turno": turno, "faixa": faixa, "paed": paed, "tipo_acao": tipo_acao, "status": status,
        "field_options": options, "selected": selected, "headers": headers, "rows": rows,
        "tipos_acao": AcaoBuscaAtiva.TIPOS, "status_choices": AcaoBuscaAtiva.STATUS,
        "turnos": [(v, l) for v, l in __import__("turmas.models", fromlist=["Turma"]).Turma.TURNOS],
    })


@login_required
@user_passes_test(gerencial)
def acompanhamentos(request):
    """Visão consolidada: um estudante por linha, com filtros sobre suas providências."""
    hoje = timezone.localdate()
    acoes = AcaoBuscaAtiva.objects.select_related("aluno", "aluno__turma", "responsavel")
    q = request.GET.get("q", "").strip()
    tipo = request.GET.get("tipo", "")
    status = request.GET.get("status", "")
    turno = request.GET.get("turno", "")
    turma = request.GET.get("turma", "")
    prazo_filtro = request.GET.get("prazo", "")
    faixa = request.GET.get("faixa", "")
    paed = request.GET.get("paed", "")
    inicio, fim = request.GET.get("inicio", ""), request.GET.get("fim", "")
    if q:
        acoes = acoes.filter(Q(aluno__nome__icontains=q) | Q(aluno__matricula__icontains=q) | Q(descricao__icontains=q) | Q(responsavel_origem__icontains=q) | Q(responsavel__username__icontains=q))
    if tipo: acoes = acoes.filter(tipo=tipo)
    if status: acoes = acoes.filter(status=status)
    if turno: acoes = acoes.filter(aluno__turma__turno=turno)
    if turma: acoes = acoes.filter(aluno__turma_id=turma)
    if prazo_filtro == "vencido": acoes = acoes.filter(prazo__lt=hoje).exclude(status__in=["Concluída", "Cancelada"])
    elif prazo_filtro == "no_prazo": acoes = acoes.filter(prazo__gte=hoje).exclude(status__in=["Concluída", "Cancelada"])
    elif prazo_filtro == "sem_prazo": acoes = acoes.filter(prazo__isnull=True).exclude(status__in=["Concluída", "Cancelada"])
    if inicio: acoes = acoes.filter(data__gte=inicio)
    if fim: acoes = acoes.filter(data__lte=fim)
    if paed == "sim": acoes = acoes.filter(Q(aluno__aluno_paed=True) | Q(aluno__situacoes_infrequencia__paed_na_fonte__in=["SIM", "S", "1"]))
    elif paed == "nao": acoes = acoes.filter(aluno__aluno_paed=False).exclude(aluno__situacoes_infrequencia__paed_na_fonte__in=["SIM", "S", "1"])
    if faixa:
        situacoes = SituacaoInfrequencia.objects.filter(ano_letivo=hoje.year).select_related(None)
        faixas_ids = []
        for situacao in situacoes:
            percentual = situacao.percentual_considerado
            if ((faixa == "abaixo10" and percentual < 10) or
                (faixa == "10a149" and 10 <= percentual < 15) or
                (faixa == "15a249" and 15 <= percentual < 25) or
                (faixa == "25mais" and percentual >= 25)):
                faixas_ids.append(situacao.aluno_id)
        acoes = acoes.filter(aluno_id__in=faixas_ids)
    alunos = Aluno.objects.filter(acoes_busca_ativa__in=acoes).select_related("turma").distinct().annotate(total_acoes=Count("acoes_busca_ativa", distinct=True))
    latest = acoes.filter(aluno_id=OuterRef("pk")).order_by("-data", "-criado_em")
    situacao_atual = SituacaoInfrequencia.objects.filter(aluno_id=OuterRef("pk"), ano_letivo=hoje.year)
    zero = Value(0, output_field=DecimalField(max_digits=6, decimal_places=2))
    alunos = alunos.annotate(
        ultima_data=Subquery(latest.values("data")[:1]),
        ultima_acao=Subquery(latest.values("tipo")[:1]),
        ultimo_prazo=Subquery(latest.values("prazo")[:1]),
        ultimo_status=Subquery(latest.values("status")[:1]),
        ultimo_responsavel=Subquery(latest.values("responsavel_origem")[:1]),
        ultimo_usuario=Subquery(latest.values("responsavel__username")[:1]),
        paed_fonte=Subquery(situacao_atual.values("paed_na_fonte")[:1]),
        p_final=Subquery(situacao_atual.values("percentual_geral_final")[:1]),
        p_geral=Subquery(situacao_atual.values("percentual_geral")[:1]),
        p_25=Subquery(situacao_atual.values("percentual_relatorio_25")[:1]),
    ).annotate(maior_percentual=Greatest(Coalesce("p_final", zero), Coalesce("p_geral", zero), Coalesce("p_25", zero))).order_by("-ultima_data", "nome")
    total_estudantes = Aluno.objects.filter(acoes_busca_ativa__isnull=False).distinct().count()
    total_acoes = AcaoBuscaAtiva.objects.count()
    if request.GET.get("csv") == "1":
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = 'attachment; filename="geredu_acompanhamentos_busca_ativa.csv"'
        writer = csv.writer(response, delimiter=";")
        writer.writerow(["Estudante", "Matrícula", "Turma", "Turno", "PAED", "Ações", "Última ação", "Data", "Prazo", "Status", "Responsável de origem"])
        for a in alunos:
            paed_flag = a.aluno_paed or str(a.paed_fonte or "").strip().upper() in ["SIM", "S", "1", "TRUE"]
            writer.writerow([a.nome, a.matricula, str(a.turma or ""), a.turma.get_turno_display() if a.turma else "", "Sim" if paed_flag else "Não", a.total_acoes, a.ultima_acao or "", a.ultima_data or "", a.ultimo_prazo or "", a.ultimo_status or "", a.ultimo_responsavel or a.ultimo_usuario or ""])
        return response
    return render(request, "busca_ativa/acompanhamentos.html", {
        "alunos": alunos, "total_estudantes": total_estudantes, "total_acoes": total_acoes,
        "acoes_filtradas": acoes.count(), "q": q, "tipo": tipo, "status": status,
        "turno": turno, "turma": turma, "prazo": prazo_filtro, "faixa": faixa, "paed": paed, "inicio": inicio, "fim": fim,
        "turmas": __import__("turmas.models", fromlist=["Turma"]).Turma.objects.all().order_by("nome"),
        "tipos": AcaoBuscaAtiva.TIPOS, "status_choices": AcaoBuscaAtiva.STATUS,
        "turnos": [(v, l) for v, l in __import__("turmas.models", fromlist=["Turma"]).Turma.TURNOS],
    })


@login_required
def importar_comunicado_txt(request):
    """Publica a atualização do sistema a partir de um arquivo TXT versionado."""
    if not gerencial(request.user):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    if request.method == 'POST':
        arquivo = request.FILES.get('arquivo_txt')
        if not arquivo:
            messages.error(request, 'Selecione o arquivo TXT da atualização.')
            return redirect('busca_ativa:atualizacao_txt')
        if not arquivo.name.lower().endswith('.txt') or arquivo.size > 512 * 1024:
            messages.error(request, 'Envie somente arquivo .txt de até 512 KB.')
            return redirect('busca_ativa:atualizacao_txt')
        try:
            conteudo = arquivo.read().decode('utf-8-sig')
            campos = {}
            corpo = []
            lendo_texto = False
            for linha in conteudo.splitlines():
                if not lendo_texto and ':' in linha:
                    chave, valor = linha.split(':', 1)
                    chave = chave.strip().upper()
                    if chave in {'VERSAO', 'TITULO'}:
                        campos[chave] = valor.strip()
                        continue
                    if chave == 'TEXTO':
                        if valor.strip(): corpo.append(valor.strip())
                        lendo_texto = True
                        continue
                if lendo_texto:
                    corpo.append(linha)
            versao, titulo, texto = campos.get('VERSAO', ''), campos.get('TITULO', ''), '\n'.join(corpo).strip()
            if not versao or not titulo or not texto:
                raise ValueError('O TXT precisa conter VERSAO:, TITULO: e TEXTO:, seguido da descrição da atualização.')
            # Uma versão nova gera um comunicado novo. Se a mesma versão for
            # republicada com conteúdo diferente, as confirmações anteriores
            # deixam de valer e todos os usuários precisam ler novamente.
            comunicado = ComunicadoSistema.objects.filter(versao=versao).first()
            criado = comunicado is None
            if comunicado is None:
                comunicado = ComunicadoSistema.objects.create(
                    versao=versao, titulo=titulo[:180], texto=texto, ativo=True
                )
            else:
                mudou_conteudo = (
                    comunicado.titulo != titulo[:180]
                    or comunicado.texto != texto
                    or not comunicado.ativo
                )
                if mudou_conteudo:
                    LeituraComunicado.objects.filter(comunicado=comunicado).delete()
                    comunicado.titulo = titulo[:180]
                    comunicado.texto = texto
                    comunicado.ativo = True
                    comunicado.save(update_fields=["titulo", "texto", "ativo"])
            # Arquiva o TXT original em uma pasta única de notas de versão.
            pasta_notas = Path(settings.BASE_DIR) / 'busca_ativa' / 'atualizacoes'
            pasta_notas.mkdir(parents=True, exist_ok=True)
            nome_arquivo = get_valid_filename(f'NOTAS_VERSAO_{versao}.txt')
            (pasta_notas / nome_arquivo).write_text(conteudo, encoding='utf-8')
            messages.success(request, f'Atualização {comunicado.versao} publicada e arquivada. O aviso será exibido aos usuários até confirmarem a leitura.')
            return redirect('busca_ativa:atualizacao_txt')
        except UnicodeDecodeError:
            messages.error(request, 'Não foi possível ler o TXT. Salve o arquivo em UTF-8 e tente novamente.')
        except Exception as exc:
            messages.error(request, str(exc))
    historico = ComunicadoSistema.objects.order_by('-criado_em')[:20]
    pasta_notas = Path(settings.BASE_DIR) / 'busca_ativa' / 'atualizacoes'
    pasta_notas.mkdir(parents=True, exist_ok=True)
    arquivos_notas = sorted(pasta_notas.glob('NOTAS_VERSAO_*.txt'), key=lambda p: p.stat().st_mtime, reverse=True)
    notas_versao = [{'name': p.name, 'size': p.stat().st_size} for p in arquivos_notas]
    return render(request, 'busca_ativa/atualizacao_txt.html', {
        'historico': historico,
        'notas_versao': notas_versao,
    })


@login_required
def baixar_nota_versao(request, nome):
    """Disponibiliza somente arquivos NOTAS_VERSAO_*.txt da pasta oficial."""
    if not gerencial(request.user):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    nome_seguro = get_valid_filename(nome)
    if nome_seguro != nome or not nome.startswith('NOTAS_VERSAO_') or not nome.endswith('.txt'):
        raise Http404
    pasta = Path(settings.BASE_DIR) / 'busca_ativa' / 'atualizacoes'
    arquivo = (pasta / nome).resolve()
    if arquivo.parent != pasta.resolve() or not arquivo.is_file():
        raise Http404
    resposta = HttpResponse(arquivo.read_bytes(), content_type='text/plain; charset=utf-8')
    resposta['Content-Disposition'] = f'attachment; filename="{nome}"'
    return resposta
