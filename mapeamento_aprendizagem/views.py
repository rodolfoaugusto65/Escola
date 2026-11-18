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
from openpyxl.worksheet.datavalidation import DataValidation

from alunos.models import Aluno
from turmas.models import Turma
from .models import RegistroMapeamento, ResultadoDiagnostico


NIVEIS = ["", "Nível 01", "Nível 02", "Nível 03", "Nível 04", "Nível 05"]

# Equivalência adotada exclusivamente para o diagnóstico inicial importado.
GRUPO_PARA_NIVEL_DIAGNOSTICO = {
    f"Grupo {i}": f"Nível {i:02d}" for i in range(1, 5)
}


def _nivel_diagnostico(grupo):
    """Converte somente o resultado do diagnóstico inicial; não afeta bimestres."""
    return GRUPO_PARA_NIVEL_DIAGNOSTICO.get(str(grupo or "").strip(), "")
CAMPOS_TEXTO = ["professor_lp", "professor_mt", "observacoes"]
CAMPOS_NIVEL = [
    "diagnostico_lp", "lp_b1", "lp_b2", "lp_b3", "lp_b4",
    "diagnostico_mt", "mt_b1", "mt_b2", "mt_b3", "mt_b4",
]


def _ano_planilha(valor):
    """Converte a descrição da turma para a notação usada na planilha-base."""
    texto = str(valor or "").strip()
    texto = texto.replace(" Ano", "").replace(" ano", "").strip()
    if texto.startswith("8º"):
        return "8°"  # a validação original do arquivo usa o símbolo ° para o 8º ano
    return texto


def _nome_arquivo(valor):
    import re
    texto = re.sub(r"[^A-Za-z0-9_-]+", "_", str(valor or "").strip())
    return texto.strip("_")[:60] or "Turma"


@login_required
@require_http_methods(["GET", "POST"])
def painel(request):
    ano_atual = timezone.localdate().year
    anos = list(Turma.objects.order_by().values_list("ano_letivo", flat=True).distinct())
    raw_ano = request.POST.get("ano") if request.method == "POST" else request.GET.get("ano")
    try:
        ano = int(raw_ano or (ano_atual if ano_atual in anos else (max(anos) if anos else ano_atual)))
    except (TypeError, ValueError):
        ano = ano_atual

    turmas = Turma.objects.filter(ano_letivo=ano).order_by("etapa", "ano_escolar", "nome", "turno")
    turma_id = request.POST.get("turma") if request.method == "POST" else request.GET.get("turma")
    turma = turmas.filter(pk=turma_id).first() if turma_id else None
    busca = request.POST.get("q", "") if request.method == "POST" else request.GET.get("q", "")

    alunos = Aluno.objects.none()
    registros = {}
    if turma:
        alunos = Aluno.objects.filter(turma=turma).order_by("nome")
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
        alunos_validos = Aluno.objects.filter(turma=turma, pk__in=ids)
        salvos = 0
        with transaction.atomic():
            for aluno in alunos_validos:
                registro, criado = RegistroMapeamento.objects.get_or_create(
                    aluno=aluno, ano_letivo=ano,
                    defaults={
                        "turma": turma,
                        "criado_por": request.user,
                        "paede": "SIM" if aluno.aluno_paed else "NÃO",
                        "situacao": "Transferido" if aluno.transferido else "Matriculado",
                    },
                )
                registro.turma = turma
                paede = request.POST.get(f"paede_{aluno.pk}", "SIM" if aluno.aluno_paed else "NÃO").strip().upper()
                situacao = request.POST.get(f"situacao_{aluno.pk}", "Transferido" if aluno.transferido else "Matriculado").strip()
                registro.paede = paede if paede in {"SIM", "NÃO"} else ("SIM" if aluno.aluno_paed else "NÃO")
                registro.situacao = situacao if situacao in {"Matriculado", "Transferido"} else ("Transferido" if aluno.transferido else "Matriculado")
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

    resultados_diag = ResultadoDiagnostico.objects.filter(ano_letivo=ano)
    if turma:
        resultados_diag = resultados_diag.filter(aluno__turma=turma)
    diagnosticos_lp_por_aluno = {r.aluno_id: _nivel_diagnostico(r.grupo) for r in resultados_diag.filter(disciplina="LP")}
    diagnosticos_mt_por_aluno = {r.aluno_id: _nivel_diagnostico(r.grupo) for r in resultados_diag.filter(disciplina="MT")}
    return render(request, "mapeamento_aprendizagem/painel.html", {
        "anos": anos, "ano": ano, "turmas": turmas, "turma": turma,
        "alunos": alunos, "registros": registros, "q": busca,
        "niveis": NIVEIS,
        "lp_campos": [("diagnostico_lp", "Diagnóstico"), ("lp_b1", "1º Bimestre"), ("lp_b2", "2º Bimestre"), ("lp_b3", "3º Bimestre"), ("lp_b4", "4º Bimestre")],
        "mt_campos": [("diagnostico_mt", "Diagnóstico"), ("mt_b1", "1º Bimestre"), ("mt_b2", "2º Bimestre"), ("mt_b3", "3º Bimestre"), ("mt_b4", "4º Bimestre")],
        "total_alunos": alunos.count() if turma else 0,
        "total_preenchidos": len(registros),
        "total_diagnosticos": resultados_diag.count(),
        "diagnosticos_lp": resultados_diag.filter(disciplina="LP").count(),
        "diagnosticos_mt": resultados_diag.filter(disciplina="MT").count(),
        "diagnosticos_lp_por_aluno": diagnosticos_lp_por_aluno,
        "diagnosticos_mt_por_aluno": diagnosticos_mt_por_aluno,
    })



def _codigo_limpo(valor):
    if valor is None:
        return ""
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return "".join(ch for ch in texto if ch.isdigit())


def _normalizar_cabecalho(valor):
    import unicodedata, re
    texto = unicodedata.normalize("NFKD", str(valor or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", texto)


def _localizar_cabecalho(ws):
    obrigatorios = {
        "escola": {"nmescola", "nomeescola"},
        "disciplina": {"cddisciplina", "codigodisciplina"},
        "etapa": {"cdetapa", "codigoetapa"},
        "matricula": {"cdalunoinstitucional", "codigoalunoinstitucional"},
        "nome": {"nmaluno", "nomealuno"},
        "grupo": {"grupo", "classificacao", "classificacaogrupo"},
    }
    for numero, row in enumerate(ws.iter_rows(min_row=1, max_row=20, values_only=True), start=1):
        mapa = {}
        for indice, valor in enumerate(row or []):
            chave = _normalizar_cabecalho(valor)
            for campo, aliases in obrigatorios.items():
                if chave in aliases:
                    mapa[campo] = indice
        if len(mapa) == len(obrigatorios):
            return numero, mapa
    return None, None


@login_required
@require_http_methods(["GET", "POST"])
def importar_diagnostico(request):
    """Importação validada em duas fases, com limites para planilhas extensas."""
    LIMITE_ARQUIVO = 30 * 1024 * 1024
    LIMITE_LINHAS = 100_000
    LIMITE_RESULTADOS = 20_000
    escola_alvo = "EE RODOLFO AUGUSTO TRECHAUD CURVO"

    recentes = ResultadoDiagnostico.objects.values(
        "ano_letivo", "disciplina", "arquivo_origem", "importado_em"
    ).distinct().order_by("-importado_em")[:12]
    if request.method == "GET":
        return render(request, "mapeamento_aprendizagem/importar_diagnostico.html", {"recentes": recentes})

    arquivos = request.FILES.getlist("arquivos") or (
        [request.FILES.get("arquivo")] if request.FILES.get("arquivo") else []
    )
    try:
        ano = int(request.POST.get("ano_letivo") or timezone.localdate().year)
        if not 2000 <= ano <= 2100:
            raise ValueError
    except (TypeError, ValueError):
        messages.error(request, "Informe um ano letivo válido entre 2000 e 2100.")
        return redirect("mapeamento_aprendizagem:importar_diagnostico")
    if not arquivos:
        messages.error(request, "Selecione ao menos uma planilha Excel.")
        return redirect("mapeamento_aprendizagem:importar_diagnostico")
    for arquivo in arquivos:
        if not Path(arquivo.name).name.lower().endswith((".xlsx", ".xlsm")):
            messages.error(request, f"Formato não aceito: {arquivo.name}. Use .xlsx ou .xlsm.")
            return redirect("mapeamento_aprendizagem:importar_diagnostico")
        if arquivo.size > LIMITE_ARQUIVO:
            messages.error(request, f"{arquivo.name}: excede o limite de 30 MB por arquivo.")
            return redirect("mapeamento_aprendizagem:importar_diagnostico")

    mapa_alunos = {
        _codigo_limpo(a.matricula): a for a in Aluno.objects.select_related("turma")
        if _codigo_limpo(a.matricula)
    }
    # Chave única evita acumular repetidos em planilhas longas.
    pendentes = {}
    erros = []
    ignorados = nao_encontrados = 0

    for arquivo in arquivos:
        wb = None
        try:
            arquivo.seek(0)
            wb = load_workbook(arquivo, read_only=True, data_only=True)
            encontrou = False
            for ws in wb.worksheets:
                cabecalho, indices = _localizar_cabecalho(ws)
                if not indices:
                    continue
                encontrou = True
                ultima = min(ws.max_row or LIMITE_LINHAS, LIMITE_LINHAS)
                for row in ws.iter_rows(min_row=cabecalho + 1, max_row=ultima, values_only=True):
                    if not row or not any(v not in (None, "") for v in row):
                        continue
                    def valor(campo):
                        i = indices[campo]
                        return row[i] if i < len(row) else None
                    if str(valor("escola") or "").strip().upper() != escola_alvo:
                        continue
                    disc_raw = _normalizar_cabecalho(valor("disciplina"))
                    disciplina = "LP" if disc_raw in {"lp", "linguaportuguesa", "portugues"} else (
                        "MT" if disc_raw in {"mt", "matematica"} else ""
                    )
                    grupo_num = "".join(ch for ch in str(valor("grupo") or "") if ch.isdigit())
                    grupo = f"Grupo {grupo_num}" if grupo_num in {"1", "2", "3", "4"} else ""
                    codigo = _codigo_limpo(valor("matricula"))
                    if not disciplina or not grupo or not codigo:
                        ignorados += 1
                        continue
                    aluno = mapa_alunos.get(codigo)
                    if not aluno:
                        nao_encontrados += 1
                        continue
                    pendentes[(aluno.pk, disciplina)] = {
                        "aluno": aluno, "disciplina": disciplina,
                        "etapa": str(valor("etapa") or "").strip()[:20],
                        "grupo": grupo, "codigo_aluno": "",
                        "codigo_institucional": codigo, "escola": escola_alvo,
                        "arquivo_origem": Path(arquivo.name).name[:255], "modalidade": "",
                    }
                    if len(pendentes) > LIMITE_RESULTADOS:
                        raise ValueError(f"lote excede {LIMITE_RESULTADOS:,} resultados válidos")
            if not encontrou:
                erros.append(f"{arquivo.name}: cabeçalho obrigatório não localizado nas primeiras 20 linhas")
        except Exception as exc:
            erros.append(f"{arquivo.name}: {exc}")
        finally:
            if wb is not None:
                wb.close()

    if erros:
        messages.error(request, "Nenhum registro foi gravado. Corrija os arquivos: " + " | ".join(erros))
        return redirect("mapeamento_aprendizagem:importar_diagnostico")
    if not pendentes:
        messages.warning(request, f"Nenhum resultado válido. Matrículas não localizadas: {nao_encontrados}; linhas ignoradas: {ignorados}.")
        return redirect("mapeamento_aprendizagem:importar_diagnostico")

    ids = [item["aluno"].pk for item in pendentes.values()]
    existentes = set(ResultadoDiagnostico.objects.filter(
        ano_letivo=ano, aluno_id__in=ids
    ).values_list("aluno_id", "disciplina"))
    criados = atualizados = 0
    exibicao = []
    try:
        with transaction.atomic():
            for item in pendentes.values():
                aluno = item["aluno"]
                disciplina = item["disciplina"]
                defaults = {k: val for k, val in item.items() if k != "aluno"}
                resultado, _ = ResultadoDiagnostico.objects.update_or_create(
                    aluno=aluno, ano_letivo=ano, disciplina=disciplina,
                    defaults={"turma": aluno.turma, **defaults},
                )
                if (aluno.pk, disciplina) in existentes:
                    atualizados += 1
                else:
                    criados += 1
                nivel = _nivel_diagnostico(resultado.grupo)
                if nivel and aluno.turma_id:
                    registro, _ = RegistroMapeamento.objects.get_or_create(
                        aluno=aluno, ano_letivo=ano,
                        defaults={
                            "turma": aluno.turma, "criado_por": request.user,
                            "paede": "SIM" if aluno.aluno_paed else "NÃO",
                            "situacao": "Transferido" if aluno.transferido else "Matriculado",
                        },
                    )
                    campo = "diagnostico_lp" if disciplina == "LP" else "diagnostico_mt"
                    setattr(registro, campo, nivel)
                    registro.turma = aluno.turma
                    registro.atualizado_por = request.user
                    registro.save(update_fields=["turma", campo, "atualizado_por", "atualizado_em"])
                exibicao.append({
                    "aluno": aluno, "disciplina": resultado.get_disciplina_display(),
                    "grupo": resultado.grupo, "nivel": nivel, "turma": aluno.turma,
                })
    except Exception as exc:
        messages.error(request, f"Importação cancelada integralmente; nenhum lote parcial foi confirmado: {exc}")
        return redirect("mapeamento_aprendizagem:importar_diagnostico")

    messages.success(request, f"Importação concluída: {criados} novos, {atualizados} atualizados, {nao_encontrados} matrículas não localizadas e {ignorados} linhas ignoradas.")
    return render(request, "mapeamento_aprendizagem/importar_diagnostico.html", {
        "recentes": recentes, "resultado_importacao": exibicao, "ano_importado": ano,
        "criados": criados, "atualizados": atualizados,
        "nao_encontrados": nao_encontrados, "ignorados": ignorados,
    })


@login_required
def exportar(request):
    try:
        ano = int(request.GET.get("ano"))
    except (TypeError, ValueError):
        ano = timezone.localdate().year
    registros = RegistroMapeamento.objects.select_related("aluno", "turma").filter(ano_letivo=ano)
    turma = None
    if request.GET.get("turma"):
        turma = get_object_or_404(Turma, pk=request.GET["turma"], ano_letivo=ano)
        registros = registros.filter(turma=turma)
    registros = registros.order_by("turma__etapa", "turma__ano_escolar", "turma__nome", "aluno__nome")

    modelo = Path(__file__).resolve().parent / "modelos" / "planilha_monitoramento_modelo.xlsx"
    wb = load_workbook(modelo)
    ws = wb["Mapeamento"]
    # A planilha original tem dados demonstrativos nas linhas 9+, então limpamos somente valores,
    # sem alterar estilos, validações, larguras, mesclagens ou as outras duas abas.
    for row in ws.iter_rows(min_row=9, max_row=1500, min_col=1, max_col=19):
        for cell in row:
            cell.value = None

    # O GerEdu possui turno noturno; ampliamos a validação original sem remover as opções existentes.
    turno_dv = next((dv for dv in ws.data_validations.dataValidation if "C9:C1500" in str(dv.sqref)), None)
    if turno_dv:
        turno_dv.formula1 = '"Matutino,Vespertino,Integral,Noturno"'

    for idx, registro in enumerate(registros, start=9):
        if idx > 1500:
            break
        t = registro.turma
        aluno = registro.aluno
        valores = [
            _ano_planilha(t.ano_escolar), t.nome, t.get_turno_display(),
            aluno.nome, registro.paede, registro.situacao,
            registro.professor_lp, registro.diagnostico_lp,
            registro.lp_b1, registro.lp_b2, registro.lp_b3, registro.lp_b4,
            registro.professor_mt, registro.diagnostico_mt,
            registro.mt_b1, registro.mt_b2, registro.mt_b3, registro.mt_b4,
            registro.observacoes,
        ]
        for col, valor in enumerate(valores, start=1):
            ws.cell(idx, col).value = valor

    # Cabeçalho da unidade: mantém os rótulos e células mescladas do modelo.
    ws["D2"] = "EE RODOLFO AUGUSTO TRECHAUD CURVO"
    try:
        wb.calculation.fullCalcOnLoad = True
        wb.calculation.forceFullCalc = True
        wb.calculation.calcMode = "auto"
    except AttributeError:
        pass

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    nome = f"Mapeamento_Monitoramento_{ano}"
    if turma:
        nome += f"_{_nome_arquivo(turma.ano_escolar)}_{_nome_arquivo(turma.nome)}_{_nome_arquivo(turma.turno)}"
    response = HttpResponse(output.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{nome}.xlsx"'
    return response
