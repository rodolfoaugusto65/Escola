import csv
import sqlite3
import tempfile
import os
import io
from decimal import Decimal, InvalidOperation
from io import BytesIO
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Count, Q, Exists, OuterRef, Subquery, DecimalField, Value
from django.db.models.functions import Coalesce, Greatest
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from openpyxl import load_workbook

from alunos.models import Aluno
from frequencia.models import FrequenciaAluno
from .models import (
    AcaoBuscaAtiva, AcessoConsultaAluno, ImportacaoInfrequencia,
    SituacaoInfrequencia, ConsultaFrequenciaLog, ComunicadoSistema,
    LeituraComunicado, CalendarioEscolar, DiaNaoLetivo,
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


def _active_action_subquery():
    today = timezone.localdate()
    return AcaoBuscaAtiva.objects.filter(
        aluno_id=OuterRef("aluno_id"), prazo__gte=today
    ).exclude(status__in=["Concluída", "Cancelada"])


@login_required
@user_passes_test(gerencial)
def painel(request):
    today = timezone.localdate()
    situacoes = SituacaoInfrequencia.objects.select_related("aluno", "aluno__turma").filter(ano_letivo=today.year)
    ativos = AcaoBuscaAtiva.objects.filter(prazo__gte=today).exclude(status__in=["Concluída", "Cancelada"])
    base = situacoes.annotate(tem_prazo_ativo=Exists(
        AcaoBuscaAtiva.objects.filter(aluno_id=OuterRef("aluno_id"), prazo__gte=today).exclude(status__in=["Concluída", "Cancelada"])
    ))
    pendentes = base.filter(tem_prazo_ativo=False)
    q = request.GET.get("q", "").strip()
    faixa = request.GET.get("faixa", "")
    if q:
        base = base.filter(Q(aluno__nome__icontains=q) | Q(aluno__matricula__icontains=q))
    if faixa == "critico":
        base = base.filter(Q(percentual_geral_final__gte=25) | Q(percentual_geral__gte=25) | Q(percentual_relatorio_25__gte=25))
    elif faixa == "atencao":
        base = base.filter(Q(percentual_geral_final__gte=10) | Q(percentual_geral__gte=10) | Q(percentual_relatorio_25__gte=10)).exclude(
            Q(percentual_geral_final__gte=25) | Q(percentual_geral__gte=25) | Q(percentual_relatorio_25__gte=25))
    base = base.filter(tem_prazo_ativo=False).order_by("-percentual_geral_final", "aluno__nome")
    context = {
        "situacoes": base,
        "total_criticos": pendentes.filter(Q(percentual_geral_final__gte=25) | Q(percentual_geral__gte=25) | Q(percentual_relatorio_25__gte=25)).count(),
        "total_atencao": pendentes.filter(Q(percentual_geral_final__gte=10) | Q(percentual_geral__gte=10) | Q(percentual_relatorio_25__gte=10)).exclude(Q(percentual_geral_final__gte=25) | Q(percentual_geral__gte=25) | Q(percentual_relatorio_25__gte=25)).count(),
        "acoes_pendentes": ativos.count(),
        "q": q, "faixa": faixa,
        "importacoes": ImportacaoInfrequencia.objects.all()[:5],
    }
    return render(request, "busca_ativa/painel.html", context)


@login_required
@user_passes_test(gerencial)
def ficha_aluno(request, aluno_id):
    aluno = get_object_or_404(Aluno.objects.select_related("turma"), pk=aluno_id)
    situacao = SituacaoInfrequencia.objects.filter(aluno=aluno).order_by("-ano_letivo").first()
    acoes = aluno.acoes_busca_ativa.select_related("responsavel").all()
    acesso = getattr(aluno, "acesso_consulta_frequencia", None)
    link = request.build_absolute_uri(f"/consulta-frequencia/{acesso.token}/") if acesso and acesso.ativo else ""
    return render(request, "busca_ativa/ficha.html", {
        "aluno": aluno, "situacao": situacao, "acoes": acoes,
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
        exige_prazo = bool(situacao_atual and situacao_atual.percentual_considerado >= 10)
        if not descricao:
            messages.error(request, "Descreva a providência realizada.")
        elif not tipo:
            messages.error(request, "Selecione o tipo de ação.")
        elif exige_prazo and not prazo:
            messages.error(request, "Para estudantes em faixa de atenção ou crítica, informe o prazo da próxima ação.")
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
                return redirect("busca_ativa:ficha", aluno_id=aluno.id)
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
        dia = hoje
        from datetime import timedelta
        while dia <= calendario.data_fim_letivo:
            if dia.weekday() < 5 and dia not in datas:
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
def confirmar_comunicado(request, comunicado_id):
    comunicado = get_object_or_404(ComunicadoSistema, pk=comunicado_id, ativo=True)
    if request.method == "POST" and request.POST.get("confirmacao") == "lido":
        LeituraComunicado.objects.get_or_create(comunicado=comunicado, usuario=request.user)
    return redirect(request.POST.get("next") or "home")


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
    situacao = SituacaoInfrequencia.objects.filter(aluno=aluno).order_by("-ano_letivo").first()
    percentual_oficial = situacao.percentual_considerado if situacao else None
    # Mostra separadamente os dados do diário e do relatório oficial, sem misturar denominadores.
    percentual_alerta = percentual_oficial if percentual_oficial is not None else percentual_faltas
    nivel = "critico" if percentual_alerta >= 25 else ("atencao" if percentual_alerta >= 10 else "regular")
    return render(request, "busca_ativa/consulta_publica.html", {
        "aluno": aluno, "registros": registros[:30], "total": total,
        "faltas": faltas, "presencas": presencas,
        "percentual_faltas": percentual_faltas,
        "situacao": situacao, "percentual_oficial": percentual_oficial,
        "percentual_alerta": percentual_alerta, "nivel": nivel,
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
    if not uploaded.name.lower().endswith((".db", ".sqlite", ".sqlite3")):
        messages.error(request, "Envie um arquivo SQLite (.db, .sqlite ou .sqlite3).")
        return redirect("busca_ativa:painel")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            for chunk in uploaded.chunks(): tmp.write(chunk)
            temp_path = tmp.name
        conn = sqlite3.connect(f"file:{temp_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"students", "actions"}.issubset(tables):
            raise ValueError("Banco incompatível: não encontrei students e actions.")
        vinculados = sem_vinculo = acoes_importadas = duplicadas = 0
        mapa = {}
        with transaction.atomic():
            for row in conn.execute("SELECT * FROM students"):
                codigos = [str(row[k] or "").strip() for k in ("cod_aluno", "ged_mat_cod") if k in row.keys()]
                aluno = next((Aluno.objects.filter(matricula=c).first() for c in codigos if c and Aluno.objects.filter(matricula=c).exists()), None)
                if not aluno:
                    sem_vinculo += 1
                    continue
                mapa[row["id"]] = aluno
                ano = timezone.localdate().year
                sit, _ = SituacaoInfrequencia.objects.get_or_create(aluno=aluno, ano_letivo=ano, defaults={"codigo_fonte": str(row["cod_aluno"] or aluno.matricula)[:30]})
                campos = {
                    "codigo_fonte": str(row["cod_aluno"] or aluno.matricula)[:30],
                    "codigo_ged": str(row["ged_mat_cod"] or "")[:30],
                    "percentual_geral": _percent(row["perc_original"]), "percentual_geral_final": _percent(row["perc_final"]),
                    "percentual_1_bim": _percent(row["perc_1b"]), "percentual_2_bim": _percent(row["perc_2b"]),
                    "percentual_3_bim": _percent(row["perc_3b"]), "percentual_4_bim": _percent(row["perc_4b"]),
                    "percentual_relatorio_25": _percent(row["perc_report25"]), "consta_relatorio_25": bool(row["report25"]),
                    "faltas_geral": row["faltas_geral"] or 0, "faltas_final": row["faltas_final"] or 0,
                    "carga_horaria": row["ch_anual"] or 0, "paed_na_fonte": str(row["paed"] or "")[:10]}
                for k,val in campos.items(): setattr(sit,k,val)
                sit.save()
                vinculados += 1
            for row in conn.execute("SELECT * FROM actions ORDER BY id"):
                aluno = mapa.get(row["student_id"])
                if not aluno: continue
                data = str(row["data"] or "")[:10]
                tipo = str(row["tipo"] or "Outra providência")[:60]
                descricao = str(row["descricao"] or "").strip()
                if not data or not descricao: continue
                if not aluno.aluno_busca_ativa:
                    aluno.aluno_busca_ativa = True
                    aluno.save(update_fields=["aluno_busca_ativa"])
                if AcaoBuscaAtiva.objects.filter(aluno=aluno,data=data,tipo=tipo,descricao=descricao).exists():
                    duplicadas += 1
                    continue
                AcaoBuscaAtiva.objects.create(aluno=aluno,data=data,tipo=tipo,descricao=descricao,
                    resultado=str(row["resultado"] or ""),proxima_acao=str(row["proxima_acao"] or ""),
                    prazo=row["prazo"] or None,status=row["status"] or "Em andamento",responsavel=request.user,
                    responsavel_origem=str(row["responsavel"] or "")[:150])
                acoes_importadas += 1
            if "imports" in tables:
                for imp_row in conn.execute("SELECT * FROM imports"):
                    nome_arquivo = str(imp_row["arquivo"] or "Backup da Busca Ativa")[:255]
                    data_import = str(imp_row["data"] or "")
                    # Mantém o registro histórico sem substituir os lançamentos atuais.
                    if not ImportacaoInfrequencia.objects.filter(arquivo=nome_arquivo, observacao__contains="backup local").exists():
                        ImportacaoInfrequencia.objects.create(
                            arquivo=nome_arquivo, ano_letivo=timezone.localdate().year,
                            importado_por=request.user, total_registros=imp_row["quantidade"] or 0,
                            observacao=f"Registro histórico recuperado do backup local ({data_import})."
                        )
            ImportacaoInfrequencia.objects.create(
                arquivo=uploaded.name[:255], ano_letivo=timezone.localdate().year,
                importado_por=request.user, total_registros=vinculados + sem_vinculo,
                vinculados=vinculados, nao_vinculados=sem_vinculo,
                observacao=f"Integração do banco local: {acoes_importadas} ações recuperadas; {duplicadas} duplicadas ignoradas."
            )
        conn.close()
        messages.success(request, f"Backup importado: {vinculados} estudantes vinculados, {acoes_importadas} providências recuperadas, {duplicadas} duplicadas ignoradas e {sem_vinculo} estudantes sem correspondência.")
    except Exception as exc:
        messages.error(request, f"Falha ao importar backup: {exc}")
    finally:
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
    if request.method == "POST":
        arquivo = request.FILES.get("arquivo")
        tipo = request.POST.get("tipo", "geral")
        if not arquivo:
            messages.error(request, "Selecione o arquivo que deseja importar.")
            return redirect("busca_ativa:importar")
        try:
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
                if not reader.fieldnames or not obrigatorias.issubset(set(x.strip() for x in reader.fieldnames)):
                    raise ValueError("O CSV precisa conter CodAluno e PercFaltas_GeralFinal.")
                reader.fieldnames = [x.strip() for x in reader.fieldnames]
                vinculados = nao_vinculados = total = 0
                with transaction.atomic():
                    imp = ImportacaoInfrequencia.objects.create(arquivo=arquivo.name, ano_letivo=timezone.localdate().year, importado_por=request.user)
                    pendentes = []
                    for row in reader:
                        total += 1
                        codigo = str(row.get("CodAluno") or "").strip().replace(".0", "")
                        aluno = Aluno.objects.filter(matricula=codigo).first()
                        if not aluno:
                            nao_vinculados += 1
                            pendentes.append(codigo)
                            continue
                        situacao, _ = SituacaoInfrequencia.objects.get_or_create(aluno=aluno, ano_letivo=timezone.localdate().year, defaults={"codigo_fonte": codigo})
                        situacao.percentual_relatorio_25 = _percent(row.get("PercFaltas_GeralFinal"))
                        situacao.consta_relatorio_25 = True
                        situacao.importacao = imp
                        situacao.save(update_fields=["percentual_relatorio_25", "consta_relatorio_25", "importacao", "atualizado_em"])
                        vinculados += 1
                    imp.total_registros, imp.vinculados, imp.nao_vinculados = total, vinculados, nao_vinculados
                    imp.observacao = "Importação complementar 25%+. Códigos não localizados: " + "; ".join(pendentes[:300])
                    imp.save(update_fields=["total_registros", "vinculados", "nao_vinculados", "observacao"])
                messages.success(request, f"Relatório 25%+ importado: {vinculados} vinculados; {nao_vinculados} códigos não localizados.")
            else:
                if not arquivo.name.lower().endswith((".xlsx", ".xlsm")):
                    raise ValueError("A base geral deve ser enviada em Excel (.xlsx ou .xlsm).")
                wb = load_workbook(arquivo, read_only=True, data_only=True)
                ws = wb.active
                rows = ws.iter_rows(values_only=True)
                headers = [str(v).strip() if v is not None else "" for v in next(rows)]
                ix = {name: i for i, name in enumerate(headers)}
                obrigatorias = {"CodAluno", "NomeAluno", "PercFaltas_GeralFinal"}
                if not obrigatorias.issubset(ix):
                    raise ValueError("A planilha não contém as colunas essenciais CodAluno, NomeAluno e PercFaltas_GeralFinal.")
                primeira_linha = next(ws.iter_rows(min_row=2, max_row=2, values_only=True), None)
                ano_valor = primeira_linha[ix["AnoLetivo"]] if primeira_linha and "AnoLetivo" in ix else timezone.localdate().year
                ano = int(ano_valor or timezone.localdate().year)
                with transaction.atomic():
                    imp = ImportacaoInfrequencia.objects.create(arquivo=arquivo.name, ano_letivo=ano, importado_por=request.user)
                    total = vinculados = nao_vinculados = 0
                    pendentes = []
                    for row in rows:
                        if not row or row[ix["CodAluno"]] is None:
                            continue
                        total += 1
                        codigo = str(row[ix["CodAluno"]]).strip().replace(".0", "")
                        ged = str(row[ix["GedMatCod"]]).strip().replace(".0", "") if "GedMatCod" in ix and row[ix["GedMatCod"]] is not None else ""
                        a1 = Aluno.objects.filter(matricula=codigo).first()
                        a2 = Aluno.objects.filter(matricula=ged).first() if ged else None
                        if a1 and a2 and a1.pk != a2.pk:
                            nao_vinculados += 1; pendentes.append(f"{codigo}/{ged} divergentes"); continue
                        aluno = a1 or a2
                        if not aluno:
                            nao_vinculados += 1; pendentes.append(f"{codigo}/{ged}"); continue
                        def val(col): return row[ix[col]] if col in ix and ix[col] < len(row) else None
                        SituacaoInfrequencia.objects.update_or_create(aluno=aluno, ano_letivo=ano, defaults={
                            "codigo_fonte": codigo, "codigo_ged": ged, "importacao": imp,
                            "percentual_geral": _percent(val("PercFaltas_Geral")),
                            "percentual_geral_final": _percent(val("PercFaltas_GeralFinal")),
                            "percentual_1_bim": _percent(val("PercFaltasFinal_1Bim")),
                            "percentual_2_bim": _percent(val("PercFaltasFinal_2Bim")),
                            "percentual_3_bim": _percent(val("PercFaltasFinal_3Bim")),
                            "percentual_4_bim": _percent(val("PercFaltasFinal_4Bim")),
                            "faltas_geral": val("TF_Geral") or 0, "faltas_final": val("TF_Geral_Final") or 0,
                            "carga_horaria": val("CHAnual") or 0, "paed_na_fonte": str(val("PAED") or ""),
                        })
                        vinculados += 1
                    imp.total_registros, imp.vinculados, imp.nao_vinculados = total, vinculados, nao_vinculados
                    imp.observacao = "Códigos sem vínculo ou ambíguos: " + "; ".join(pendentes[:300])
                    imp.save(update_fields=["total_registros", "vinculados", "nao_vinculados", "observacao"])
                wb.close()
                messages.success(request, f"Base geral importada: {vinculados} vinculados; {nao_vinculados} sem correspondência. Histórico preservado.")
        except Exception as exc:
            messages.error(request, f"Não foi possível importar o arquivo: {exc}")
        return redirect("busca_ativa:painel")
    return render(request, "busca_ativa/importar.html")


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
        for a in qs:
            if not aluno_ok(a): continue
            sit = SituacaoInfrequencia.objects.filter(aluno=a, ano_letivo=hoje.year).first()
            pct = sit.percentual_considerado if sit else 0
            if not faixa_ok(pct): continue
            paed_flag = a.aluno_paed or bool(sit and str(sit.paed_na_fonte).strip().upper() in ["SIM", "S", "1", "TRUE"])
            if paed == "sim" and not paed_flag: continue
            if paed == "nao" and paed_flag: continue
            data = {"nome": a.nome, "matricula": a.matricula, "turma": str(a.turma or "—"), "turno": a.turma.get_turno_display() if a.turma else "—", "nascimento": a.data_nascimento.strftime("%d/%m/%Y") if a.data_nascimento else "—", "paed": "Sim" if paed_flag else "Não", "percentual": f"{pct:.1f}%", "faltas": str(sit.faltas_final if sit else "—"), "situacao": a.situacao or "—"}
            rows.append({"values": [data[k] for k in selected], "aluno_id": a.id})
    elif tipo in ["acoes", "compensacao"]:
        qs = AcaoBuscaAtiva.objects.select_related("aluno", "aluno__turma", "responsavel").all()
        if tipo == "compensacao": qs = qs.filter(tipo__in=["Compensação de Ausências", "Compensação de ausências"])
        if inicio: qs = qs.filter(data__gte=inicio)
        if fim: qs = qs.filter(data__lte=fim)
        if tipo_acao and tipo == "acoes": qs = qs.filter(tipo=tipo_acao)
        if status: qs = qs.filter(status=status)
        if q: qs = qs.filter(Q(aluno__nome__icontains=q) | Q(aluno__matricula__icontains=q) | Q(descricao__icontains=q) | Q(responsavel_origem__icontains=q))
        if turno: qs = qs.filter(aluno__turma__turno=turno)
        for a in qs.order_by("-data", "aluno__nome"):
            sit = SituacaoInfrequencia.objects.filter(aluno=a.aluno, ano_letivo=hoje.year).first()
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
        for sit in qs.order_by("-percentual_geral_final", "aluno__nome"):
            a = sit.aluno
            if not aluno_ok(a): continue
            pct = sit.percentual_considerado
            if pct < 10 or not faixa_ok(pct): continue
            paed_flag = a.aluno_paed or str(sit.paed_na_fonte).strip().upper() in ["SIM", "S", "1", "TRUE"]
            if paed == "sim" and not paed_flag: continue
            if paed == "nao" and paed_flag: continue
            ultima = AcaoBuscaAtiva.objects.filter(aluno=a).order_by("-data", "-criado_em").first()
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
    faixa = request.GET.get("faixa", "")
    paed = request.GET.get("paed", "")
    inicio, fim = request.GET.get("inicio", ""), request.GET.get("fim", "")
    if q:
        acoes = acoes.filter(Q(aluno__nome__icontains=q) | Q(aluno__matricula__icontains=q) | Q(descricao__icontains=q) | Q(responsavel_origem__icontains=q) | Q(responsavel__username__icontains=q))
    if tipo: acoes = acoes.filter(tipo=tipo)
    if status: acoes = acoes.filter(status=status)
    if turno: acoes = acoes.filter(aluno__turma__turno=turno)
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
        "turno": turno, "faixa": faixa, "paed": paed, "inicio": inicio, "fim": fim,
        "tipos": AcaoBuscaAtiva.TIPOS, "status_choices": AcaoBuscaAtiva.STATUS,
        "turnos": [(v, l) for v, l in __import__("turmas.models", fromlist=["Turma"]).Turma.TURNOS],
    })
