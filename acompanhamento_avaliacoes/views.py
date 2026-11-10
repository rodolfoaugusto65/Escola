import csv
import io
import json
import hashlib
import logging
import re
import unicodedata
from datetime import datetime

from django.contrib import messages
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import get_valid_filename
from openpyxl import load_workbook

from alunos.models import Aluno
from core.utils import render_smart
from core.file_storage import salvar_arquivo_geredu
from .models import Avaliacao, ImportacaoAvaliacao, RegistroParticipacao, ArquivoImportacaoAvaliacao

logger = logging.getLogger(__name__)


def _render(request, template, context=None):
    template, context = render_smart(request, template, context or {})
    return render(request, template, context)


def _somente_gestao(user):
    if not (user.is_superuser or getattr(user, 'pode_gerenciar_usuarios', False)):
        raise PermissionDenied


def _norm(valor):
    texto = unicodedata.normalize('NFKD', str(valor or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '', texto)


def _valor(row, headers, *nomes):
    desejados = {_norm(n) for n in nomes}
    for i, h in enumerate(headers):
        if _norm(h) in desejados and i < len(row):
            return row[i]
    return ''


def _string(v):
    """Converte células vazias/None e valores Excel para texto seguro."""
    if v is None:
        return ''
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v).strip()


def _regex_text(value):
    """Nunca permite que None chegue às funções do módulo re."""
    return _string(value)


def _nome_arquivo_seguro(upload):
    nome = _string(getattr(upload, 'name', None))
    if not nome:
        nome = 'planilha_importada.xlsx'
    return get_valid_filename(nome) or 'planilha_importada.xlsx'


def _ler_planilha(upload):
    nome = _string(getattr(upload, 'name', None)).lower()
    if not nome:
        raise ValueError('O arquivo enviado não possui nome válido.')
    upload.seek(0)
    if nome.endswith('.csv'):
        raw = upload.read()
        try:
            conteudo = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            conteudo = raw.decode('latin-1')
        amostra = conteudo[:4096]
        try:
            dialect = csv.Sniffer().sniff(amostra, delimiters=';,\t')
        except csv.Error:
            dialect = csv.excel
        linhas = list(csv.reader(io.StringIO(conteudo), dialect))
    elif nome.endswith(('.xlsx', '.xlsm')):
        wb = load_workbook(upload, read_only=True, data_only=True)
        try:
            ws = wb.active
            linhas = list(ws.iter_rows(values_only=True))
        finally:
            wb.close()
    else:
        raise ValueError('Formato não suportado. Envie XLSX ou CSV.')
    linhas = [list(r) for r in linhas if r and any(v not in (None, '') for v in r)]
    if len(linhas) < 2:
        raise ValueError('A planilha não possui cabeçalho e registros suficientes.')
    headers = [_string(v) for v in linhas[0]]
    obrigatorios = {'matricula': ('matricula', 'registroacademico', 'ra'), 'aluno': ('aluno', 'nome', 'nomedoaluno'), 'participacao': ('participacao', 'situacao', 'status')}
    ausentes = [campo for campo, aliases in obrigatorios.items() if not any(_norm(h) in {_norm(a) for a in aliases} for h in headers)]
    if ausentes:
        raise ValueError('Não foi possível reconhecer as colunas obrigatórias: ' + ', '.join(ausentes) + '. A planilha precisa conter matrícula, aluno e participação/situação.')
    return headers, linhas[1:]


def _classificar(status):
    s = _norm(status)
    if any(x in s for x in ('aguardando', 'pendente', 'naorealizou', 'naoentregue', 'naoparticipou', 'naoconcluido')):
        return 'pendente'
    if any(x in s for x in ('presente', 'realizado', 'concluido', 'entregue', 'participou', 'finalizado')):
        return 'realizado'
    if any(x in s for x in ('ausente', 'falta', 'faltou')):
        return 'ausente'
    return 'outro'


@login_required
def painel(request):
    _somente_gestao(request.user)
    avaliacao_id = request.GET.get('avaliacao', '')
    base_importacoes = ImportacaoAvaliacao.objects.select_related('avaliacao').all()
    if not avaliacao_id:
        mais_recente = base_importacoes.first()
        if mais_recente:
            avaliacao_id = str(mais_recente.avaliacao_id)
    importacoes = base_importacoes.filter(avaliacao_id=avaliacao_id) if avaliacao_id.isdigit() else base_importacoes.none()
    ultima = importacoes.first()
    registros = RegistroParticipacao.objects.filter(importacao=ultima) if ultima else RegistroParticipacao.objects.none()
    ano = request.GET.get('ano', '')
    turma = request.GET.get('turma', '')
    busca = request.GET.get('q', '').strip()
    if ano:
        registros = registros.filter(ano_serie__icontains=ano)
    if turma:
        registros = registros.filter(turma__icontains=turma)
    if busca:
        registros = registros.filter(Q(nome_aluno__icontains=busca) | Q(matricula__icontains=busca))
    resumo = registros.aggregate(total=Count('id'), realizados=Count('id', filter=Q(situacao='realizado')), pendentes=Count('id', filter=Q(situacao='pendente')), ausentes=Count('id', filter=Q(situacao='ausente')))
    total = resumo['total'] or 0
    percentual = round((resumo['realizados'] or 0) * 100 / total, 1) if total else 0
    # Resumo por turma: os percentuais são calculados no servidor para evitar
    # divergências de arredondamento e permitir comparação visual consistente.
    por_turma = list(registros.values('ano_serie', 'turma').annotate(
        total=Count('id'),
        realizados=Count('id', filter=Q(situacao='realizado')),
        pendentes=Count('id', filter=Q(situacao='pendente')),
        ausentes=Count('id', filter=Q(situacao='ausente')),
    ).order_by('ano_serie', 'turma'))
    for item in por_turma:
        item['percentual'] = round(item['realizados'] * 100 / item['total'], 1) if item['total'] else 0
        item['nao_realizados'] = item['total'] - item['realizados']
    turmas_disponiveis = list(RegistroParticipacao.objects.filter(importacao=ultima)
        .exclude(turma='').values_list('turma', flat=True).distinct().order_by('turma')) if ultima else []
    anos_disponiveis = list(RegistroParticipacao.objects.filter(importacao=ultima)
        .exclude(ano_serie='').values_list('ano_serie', flat=True).distinct().order_by('ano_serie')) if ultima else []
    pendentes_lista = registros.filter(situacao__in=['pendente', 'ausente', 'outro']).order_by('ano_serie', 'turma', 'nome_aluno')[:250]

    historico = list(importacoes.order_by('-criado_em')[:30])
    historico.reverse()
    grafico_labels = [i.criado_em.strftime('%d/%m %H:%M') for i in historico]
    grafico_percentuais = [i.percentual for i in historico]
    contexto = {
        'avaliacoes': Avaliacao.objects.order_by('-ano_letivo', 'nome'), 'importacoes': importacoes[:12],
        'ultima': ultima, 'resumo': resumo, 'total': total, 'percentual': percentual,
        'por_turma': por_turma, 'turmas_disponiveis': turmas_disponiveis,
        'anos_disponiveis': anos_disponiveis, 'pendentes_lista': pendentes_lista,
        'grafico_labels': json.dumps(grafico_labels), 'grafico_percentuais': json.dumps(grafico_percentuais),
        'filtro_avaliacao': avaliacao_id, 'filtro_ano': ano, 'filtro_turma': turma, 'busca': busca,
    }
    return _render(request, 'acompanhamento_avaliacoes/painel.html', contexto)


@login_required
def importar(request):
    _somente_gestao(request.user)
    if request.method == 'POST':
        arquivos = request.FILES.getlist('arquivos') or ([request.FILES['arquivo']] if request.FILES.get('arquivo') else [])
        if not arquivos:
            messages.error(request, 'Selecione ao menos uma planilha.')
            return redirect('acompanhamento_avaliacoes:importar')

        grupos = {}
        erros = []
        for upload in arquivos:
            try:
                if upload.size > 25 * 1024 * 1024:
                    raise ValueError('O arquivo ultrapassa o limite de 25 MB.')
                headers, linhas = _ler_planilha(upload)
                primeira = linhas[0]
                nome_upload = _string(getattr(upload, 'name', None)) or 'planilha_importada.xlsx'
                nome_original = _string(_valor(primeira, headers, 'Avaliação', 'Avaliacao', 'Nome da avaliação'))
                if not nome_original:
                    nome_original = nome_upload.rsplit('.', 1)[0]
                # Os relatórios de cada série costumam repetir o mesmo nome-base.
                # Normalizamos explicitamente para string antes de chamar regex.
                nome_original = _regex_text(nome_original)
                nome_avaliacao = re.sub(
                    r'\s*-\s*\d+\s*[ºª°]?\s*(?:ano|série|serie)(?:\s+\w+)?\s*$',
                    '', _regex_text(nome_original), flags=re.I
                ).strip()
                nome_avaliacao = _regex_text(nome_avaliacao) or nome_original
                ano_match = re.search(r'20\d{2}', _regex_text(nome_avaliacao))
                ano_letivo = int(ano_match.group()) if ano_match else timezone.localdate().year
                chave = (nome_avaliacao, ano_letivo)
                grupos.setdefault(chave, []).append((upload, headers, linhas, nome_original))
            except Exception as exc:
                logger.exception('Falha ao validar planilha de avaliações %r', getattr(upload, 'name', None))
                erros.append(f'{_string(getattr(upload, "name", None)) or "Arquivo sem nome"}: {exc}')

        sucesso = 0
        for (nome_avaliacao, ano_letivo), planilhas in grupos.items():
            arquivos_salvos = []
            try:
                with transaction.atomic():
                    exemplo_headers, exemplo_linhas = planilhas[0][1], planilhas[0][2]
                    primeira = exemplo_linhas[0]
                    prova_padrao = _string(_valor(primeira, exemplo_headers, 'Prova', 'Nome da prova'))
                    serie_padrao = _string(_valor(primeira, exemplo_headers, 'Ano/Série', 'Ano Serie', 'Série', 'Etapa'))
                    etapa = 'Ensino Médio' if 'medio' in _norm(serie_padrao) or 'medio' in _norm(nome_avaliacao) else ('Ensino Fundamental' if 'fundamental' in _norm(serie_padrao) or 'ano' in _norm(serie_padrao) else '')
                    bimestre_match = re.search(r'([1-4])\s*[º°]?\s*bimestre', _regex_text(nome_avaliacao), re.I)
                    bimestre = f'{bimestre_match.group(1)}º Bimestre' if bimestre_match else ''
                    avaliacao, _ = Avaliacao.objects.get_or_create(nome=nome_avaliacao, ano_letivo=ano_letivo, defaults={'etapa': etapa, 'bimestre': bimestre, 'prova': prova_padrao})
                    nomes_arquivos = [_nome_arquivo_seguro(item[0]) for item in planilhas]
                    importacao = ImportacaoAvaliacao.objects.create(avaliacao=avaliacao, arquivo='; '.join(nomes_arquivos)[:255], usuario=request.user)
                    for upload, _headers, _linhas, _nome_original in planilhas:
                        upload.seek(0)
                        conteudo_original = upload.read()
                        arquivo_guardado = ArquivoImportacaoAvaliacao(
                            importacao=importacao, nome_original=(_string(getattr(upload, 'name', None)) or 'planilha_importada.xlsx')[:255],
                            sha256=hashlib.sha256(conteudo_original).hexdigest(),
                            tamanho_bytes=len(conteudo_original),
                        )
                        nome_guardado = _nome_arquivo_seguro(upload)
                        if not conteudo_original:
                            raise ValueError(f'O arquivo {nome_guardado} está vazio.')
                        salvar_arquivo_geredu(arquivo_guardado.arquivo_original, nome_guardado, ContentFile(conteudo_original), save=True)
                        if arquivo_guardado.arquivo_original.size != len(conteudo_original):
                            raise IOError(f'O armazenamento não confirmou o arquivo {upload.name}. A importação foi cancelada.')
                        arquivos_salvos.append((arquivo_guardado.arquivo_original.storage, arquivo_guardado.arquivo_original.name))
                    objetos = []
                    realizados = pendentes = nao_vinculados = 0
                    for upload, headers, linhas, nome_original in planilhas:
                        for row in linhas:
                            matricula = _string(_valor(row, headers, 'Matrícula', 'Matricula', 'RA', 'Registro Acadêmico'))
                            nome = _string(_valor(row, headers, 'Aluno', 'Nome', 'Nome do aluno'))
                            if not matricula and not nome:
                                continue
                            status = _string(_valor(row, headers, 'Participação', 'Participacao', 'Situação', 'Situacao', 'Status'))
                            situacao = _classificar(status)
                            aluno = Aluno.objects.filter(matricula=matricula).first() if matricula else None
                            if not aluno:
                                nao_vinculados += 1
                            if situacao == 'realizado':
                                realizados += 1
                            elif situacao in ('pendente', 'ausente'):
                                pendentes += 1
                            originais = {str(h): _string(row[i]) if i < len(row) else '' for i, h in enumerate(headers)}
                            objetos.append(RegistroParticipacao(
                                importacao=importacao, aluno=aluno, matricula=matricula or 'SEM-MATRICULA',
                                nome_aluno=nome or (aluno.nome if aluno else 'Aluno não identificado'),
                                turma=_string(_valor(row, headers, 'Turma', 'Classe')),
                                ano_serie=_string(_valor(row, headers, 'Ano/Série', 'Ano Serie', 'Série', 'Etapa')) or serie_padrao,
                                prova=_string(_valor(row, headers, 'Prova', 'Nome da prova')) or prova_padrao,
                                participacao=status, situacao=situacao,
                                entregue_em=_string(_valor(row, headers, 'Entregue Em', 'Data de entrega', 'Data')),
                                tempo_prova=_string(_valor(row, headers, 'Tempo de Prova', 'Tempo')),
                                dados_originais=originais,
                            ))
                    RegistroParticipacao.objects.bulk_create(objetos, batch_size=500)
                    importacao.total_registros = len(objetos)
                    importacao.realizados = realizados
                    importacao.pendentes = pendentes
                    importacao.nao_vinculados = nao_vinculados
                    importacao.status = 'parcial' if nao_vinculados else 'concluida'
                    importacao.save(update_fields=['total_registros', 'realizados', 'pendentes', 'nao_vinculados', 'status'])
                sucesso += 1
            except Exception as exc:
                logger.exception('Falha ao concluir importação da avaliação %r', nome_avaliacao)
                for storage, nome_arquivo_salvo in arquivos_salvos:
                    try:
                        storage.delete(nome_arquivo_salvo)
                    except Exception:
                        pass
                erros.append(f'{nome_avaliacao}: {type(exc).__name__}. Consulte os logs do servidor para o diagnóstico completo; a importação foi revertida e o histórico anterior foi preservado.')
        if sucesso:
            messages.success(request, f'{sucesso} conjunto(s) de avaliação importado(s). As planilhas do mesmo conjunto foram agrupadas e o histórico anterior foi preservado.')
        for erro in erros:
            messages.error(request, erro)
        return redirect('acompanhamento_avaliacoes:painel')
    return _render(request, 'acompanhamento_avaliacoes/importar.html')

@login_required
def historico(request):
    _somente_gestao(request.user)
    registros = ImportacaoAvaliacao.objects.select_related('avaliacao', 'usuario').all()
    return _render(request, 'acompanhamento_avaliacoes/historico.html', {'importacoes': registros})


@login_required
def detalhe_importacao(request, pk):
    _somente_gestao(request.user)
    importacao = get_object_or_404(ImportacaoAvaliacao.objects.select_related('avaliacao'), pk=pk)
    registros = importacao.registros.all()
    situacao = request.GET.get('situacao', '')
    turma = request.GET.get('turma', '')
    q = request.GET.get('q', '').strip()
    if situacao:
        registros = registros.filter(situacao=situacao)
    if turma:
        registros = registros.filter(turma__icontains=turma)
    if q:
        registros = registros.filter(Q(nome_aluno__icontains=q) | Q(matricula__icontains=q))
    return _render(request, 'acompanhamento_avaliacoes/detalhe.html', {'importacao': importacao, 'registros': registros, 'arquivos_originais': importacao.arquivos_originais.all(), 'situacao_filtro': situacao, 'turma_filtro': turma, 'busca': q})
