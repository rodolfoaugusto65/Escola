import csv
import io
import json
import hashlib
import logging
import re
import unicodedata
import uuid
from datetime import datetime, date, time

from django.contrib import messages
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.core.paginator import Paginator
from django.utils.dateparse import parse_datetime, parse_date
from django.utils.timezone import make_aware, is_naive
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse
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



def _parse_data_realizacao(valor):
    """Normaliza datas Excel, ISO-8601 (inclusive sufixo Z) e datas brasileiras."""
    if valor in (None, ''):
        return None
    if isinstance(valor, datetime):
        dt = valor
    elif isinstance(valor, date):
        dt = datetime.combine(valor, time.min)
    else:
        texto = _string(valor)
        if not texto:
            return None
        # Exportações Plurall podem gerar ISO-8601 em minúsculas (t/z).
        iso_normalizado = texto.replace('t', 'T').replace('z', 'Z')
        try:
            dt = parse_datetime(iso_normalizado)
        except ValueError:
            dt = None
        if dt is None:
            for fmt in ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S'):
                try:
                    dt = datetime.strptime(texto, fmt)
                    break
                except ValueError:
                    continue
        if dt is None:
            try:
                somente_data = parse_date(texto[:10])
            except ValueError:
                somente_data = None
            if somente_data:
                dt = datetime.combine(somente_data, time.min)
    if dt is None:
        return None
    if is_naive(dt):
        dt = make_aware(dt, timezone.get_current_timezone())
    return dt


def _mapear_alunos_em_lote(matriculas, tamanho_lote=1000):
    """Resolve matrículas com poucas consultas, sem N+1 por estudante."""
    unicas = {str(m).strip() for m in matriculas if str(m or '').strip()}
    mapa = {}
    lista = list(unicas)
    for inicio in range(0, len(lista), tamanho_lote):
        lote = lista[inicio:inicio + tamanho_lote]
        for aluno in Aluno.objects.filter(matricula__in=lote).only('id', 'matricula', 'nome'):
            mapa[str(aluno.matricula).strip()] = aluno
    return mapa


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
    avaliacao_id = request.GET.get('avaliacao', '').strip()
    base_importacoes = ImportacaoAvaliacao.objects.select_related('avaliacao').all()
    if not avaliacao_id:
        mais_recente = base_importacoes.first()
        if mais_recente:
            avaliacao_id = str(mais_recente.avaliacao_id)

    importacoes = base_importacoes.filter(avaliacao_id=avaliacao_id) if avaliacao_id.isdigit() else base_importacoes.none()
    ultima = importacoes.first()
    registros_base = RegistroParticipacao.objects.filter(importacao=ultima) if ultima else RegistroParticipacao.objects.none()

    ano = request.GET.get('ano', '').strip()
    turma = request.GET.get('turma', '').strip()
    situacao = request.GET.get('situacao', '').strip()
    busca = request.GET.get('q', '').strip()
    data_inicio_txt = request.GET.get('data_inicio', '').strip()
    data_fim_txt = request.GET.get('data_fim', '').strip()
    data_inicio = parse_date(data_inicio_txt) if data_inicio_txt else None
    data_fim = parse_date(data_fim_txt) if data_fim_txt else None

    registros = registros_base
    if ano:
        registros = registros.filter(ano_serie__icontains=ano)
    if turma:
        registros = registros.filter(turma__icontains=turma)
    if situacao in {'realizado', 'pendente', 'ausente', 'outro'}:
        registros = registros.filter(situacao=situacao)
    if busca:
        registros = registros.filter(Q(nome_aluno__icontains=busca) | Q(matricula__icontains=busca))
    if data_inicio:
        registros = registros.filter(realizado_em__date__gte=data_inicio)
    if data_fim:
        registros = registros.filter(realizado_em__date__lte=data_fim)

    resumo = registros.aggregate(
        total=Count('id'),
        realizados=Count('id', filter=Q(situacao='realizado')),
        pendentes=Count('id', filter=Q(situacao='pendente')),
        ausentes=Count('id', filter=Q(situacao='ausente')),
        outros=Count('id', filter=Q(situacao='outro')),
    )
    total = resumo['total'] or 0
    percentual = round((resumo['realizados'] or 0) * 100 / total, 1) if total else 0

    por_turma = list(registros.values('ano_serie', 'turma').annotate(
        total=Count('id'),
        realizados=Count('id', filter=Q(situacao='realizado')),
        pendentes=Count('id', filter=Q(situacao='pendente')),
        ausentes=Count('id', filter=Q(situacao='ausente')),
        outros=Count('id', filter=Q(situacao='outro')),
    ).order_by('ano_serie', 'turma'))
    for item in por_turma:
        item['percentual'] = round(item['realizados'] * 100 / item['total'], 1) if item['total'] else 0
        item['nao_realizados'] = item['total'] - item['realizados']

    turmas_disponiveis = list(registros_base.exclude(turma='').values_list('turma', flat=True).distinct().order_by('turma'))
    anos_disponiveis = list(registros_base.exclude(ano_serie='').values_list('ano_serie', flat=True).distinct().order_by('ano_serie'))

    pendentes_qs = registros.filter(situacao__in=['pendente', 'ausente', 'outro']).order_by('ano_serie', 'turma', 'nome_aluno')
    pendentes_total = pendentes_qs.count()
    pendentes_pagina = Paginator(pendentes_qs, 50).get_page(request.GET.get('pagina'))

    realizados_base = registros.filter(situacao='realizado', realizado_em__isnull=False)
    realizacoes_sem_data = registros.filter(situacao='realizado', realizado_em__isnull=True).count()
    realizacoes_por_dia = list(realizados_base.annotate(dia=TruncDate('realizado_em')).values('dia').annotate(total=Count('id')).order_by('dia'))
    realizacoes_por_turma_dia = list(realizados_base.annotate(dia=TruncDate('realizado_em')).values('ano_serie', 'turma', 'dia').annotate(total=Count('id')).order_by('ano_serie', 'turma', 'dia'))
    datas_labels = [item['dia'].strftime('%d/%m/%Y') for item in realizacoes_por_dia if item['dia']]
    datas_valores = [item['total'] for item in realizacoes_por_dia if item['dia']]

    historico = list(importacoes.order_by('-criado_em')[:30])
    historico.reverse()
    grafico_labels = [i.criado_em.strftime('%d/%m %H:%M') for i in historico]
    grafico_percentuais = [i.percentual for i in historico]

    contexto = {
        'avaliacoes': Avaliacao.objects.order_by('-ano_letivo', 'nome'),
        'importacoes': importacoes[:12], 'historico': historico, 'ultima': ultima, 'resumo': resumo,
        'total': total, 'percentual': percentual, 'por_turma': por_turma,
        'turmas_disponiveis': turmas_disponiveis, 'anos_disponiveis': anos_disponiveis,
        'pendentes_lista': pendentes_pagina, 'pendentes_total': pendentes_total,
        'grafico_labels': json.dumps(grafico_labels), 'grafico_percentuais': json.dumps(grafico_percentuais),
        'realizacoes_por_dia': realizacoes_por_dia, 'realizacoes_por_turma_dia': realizacoes_por_turma_dia,
        'realizacoes_sem_data': realizacoes_sem_data,
        'datas_labels': json.dumps(datas_labels), 'datas_valores': json.dumps(datas_valores),
        'filtro_avaliacao': avaliacao_id, 'filtro_ano': ano, 'filtro_turma': turma,
        'filtro_situacao': situacao, 'data_inicio': data_inicio_txt, 'data_fim': data_fim_txt,
        'busca': busca,
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
                        extensao = '.csv' if _nome_arquivo_seguro(upload).lower().endswith('.csv') else '.xlsx'
                        nome_guardado = f'{uuid.uuid4().hex[:20]}{extensao}'
                        if not conteudo_original:
                            raise ValueError(f'O arquivo {nome_guardado} está vazio.')
                        salvar_arquivo_geredu(arquivo_guardado.arquivo_original, nome_guardado, ContentFile(conteudo_original), save=True)
                        if arquivo_guardado.arquivo_original.size != len(conteudo_original):
                            raise IOError(f'O armazenamento não confirmou o arquivo {upload.name}. A importação foi cancelada.')
                        arquivos_salvos.append((arquivo_guardado.arquivo_original.storage, arquivo_guardado.arquivo_original.name))
                    objetos = []
                    realizados = pendentes = nao_vinculados = 0
                    matriculas_arquivo = []
                    for _upload, headers, linhas, _nome in planilhas:
                        matriculas_arquivo.extend(_string(_valor(row, headers, 'Matrícula', 'Matricula', 'RA', 'Registro Acadêmico')) for row in linhas)
                    alunos_por_matricula = _mapear_alunos_em_lote(matriculas_arquivo)
                    for upload, headers, linhas, nome_original in planilhas:
                        for row in linhas:
                            matricula = _string(_valor(row, headers, 'Matrícula', 'Matricula', 'RA', 'Registro Acadêmico'))
                            nome = _string(_valor(row, headers, 'Aluno', 'Nome', 'Nome do aluno'))
                            if not matricula and not nome:
                                continue
                            status = _string(_valor(row, headers, 'Participação', 'Participacao', 'Situação', 'Situacao', 'Status'))
                            situacao = _classificar(status)
                            aluno = alunos_por_matricula.get(matricula) if matricula else None
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
                                realizado_em=(_parse_data_realizacao(_valor(row, headers, 'Data de realização', 'Data da realização', 'Realizado em', 'Data realização', 'Data de conclusão', 'Data de conclusão da avaliação', 'Data de entrega', 'Entregue em', 'Data')) if situacao == 'realizado' else None),
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
    registros = ImportacaoAvaliacao.objects.select_related('avaliacao', 'usuario').prefetch_related('arquivos_originais')
    avaliacao_id = request.GET.get('avaliacao', '').strip()
    status = request.GET.get('status', '').strip()
    inicio_txt = request.GET.get('data_inicio', '').strip()
    fim_txt = request.GET.get('data_fim', '').strip()
    inicio = parse_date(inicio_txt) if inicio_txt else None
    fim = parse_date(fim_txt) if fim_txt else None
    if avaliacao_id.isdigit():
        registros = registros.filter(avaliacao_id=avaliacao_id)
    if status in {'concluida', 'parcial'}:
        registros = registros.filter(status=status)
    if inicio:
        registros = registros.filter(criado_em__date__gte=inicio)
    if fim:
        registros = registros.filter(criado_em__date__lte=fim)
    return _render(request, 'acompanhamento_avaliacoes/historico.html', {
        'importacoes': registros, 'avaliacoes': Avaliacao.objects.order_by('-ano_letivo', 'nome'),
        'filtro_avaliacao': avaliacao_id, 'filtro_status': status,
        'data_inicio': inicio_txt, 'data_fim': fim_txt,
    })


@login_required
def detalhe_importacao(request, pk):
    _somente_gestao(request.user)
    importacao = get_object_or_404(
        ImportacaoAvaliacao.objects.select_related('avaliacao').prefetch_related('arquivos_originais'), pk=pk
    )
    registros_base = importacao.registros.select_related('aluno', 'aluno__turma').all()
    registros = registros_base
    situacao = request.GET.get('situacao', '').strip()
    turma = request.GET.get('turma', '').strip()
    turno = request.GET.get('turno', '').strip()
    ano = request.GET.get('ano', '').strip()
    q = request.GET.get('q', '').strip()
    data_inicio_txt = request.GET.get('data_inicio', '').strip()
    data_fim_txt = request.GET.get('data_fim', '').strip()
    data_inicio = parse_date(data_inicio_txt) if data_inicio_txt else None
    data_fim = parse_date(data_fim_txt) if data_fim_txt else None

    if situacao in {'realizado', 'pendente', 'ausente', 'outro'}:
        registros = registros.filter(situacao=situacao)
    if turma:
        registros = registros.filter(turma=turma)
    if turno:
        registros = registros.filter(aluno__turma__turno=turno)
    if request.GET.get('nao_realizados') == '1':
        registros = registros.filter(situacao__in=['pendente', 'ausente', 'outro'])
    if ano:
        registros = registros.filter(ano_serie=ano)
    if q:
        registros = registros.filter(Q(nome_aluno__icontains=q) | Q(matricula__icontains=q))
    # O filtro por período deve considerar a data de realização sem apagar
    # pendentes/ausentes, que normalmente não possuem realizado_em.
    situacoes_sem_data = Q(situacao__in=['pendente', 'ausente', 'outro'])
    if data_inicio and data_fim:
        registros = registros.filter(
            Q(realizado_em__date__range=(data_inicio, data_fim)) | situacoes_sem_data
        )
    elif data_inicio:
        registros = registros.filter(Q(realizado_em__date__gte=data_inicio) | situacoes_sem_data)
    elif data_fim:
        registros = registros.filter(Q(realizado_em__date__lte=data_fim) | situacoes_sem_data)

    total_filtrado = registros.count()
    if request.GET.get('imprimir') == '1':
        # Impressão dedicada: todos os registros filtrados, sem paginação,
        # indicadores, tabelas gerenciais ou dados acessórios.
        return _render(request, 'acompanhamento_avaliacoes/imprimir_lista.html', {
            'importacao': importacao,
            'estudantes': registros.order_by('nome_aluno', 'matricula'),
            'total_filtrado': total_filtrado,
        })
    if request.GET.get('csv') == '1':
        resposta = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        resposta['Content-Disposition'] = f'attachment; filename="nao_realizados_avaliacao_{importacao.pk}.csv"'
        escritor = csv.writer(resposta, delimiter=';')
        escritor.writerow(['Avaliação', 'Ano/série', 'Turma', 'Turno', 'Estudante', 'Matrícula', 'Situação', 'Participação'])
        for item in registros.order_by('ano_serie', 'turma', 'nome_aluno'):
            turno_aluno = item.aluno.turma.get_turno_display() if item.aluno_id and item.aluno.turma_id else ''
            escritor.writerow([importacao.avaliacao.nome, item.ano_serie, item.turma, turno_aluno, item.nome_aluno, item.matricula, item.get_situacao_display(), item.participacao])
        return resposta
    pagina = Paginator(registros.order_by('ano_serie', 'turma', 'nome_aluno'), 50).get_page(request.GET.get('pagina'))

    base_realizados = registros_base.filter(situacao='realizado', realizado_em__isnull=False)
    datas_realizacao = list(base_realizados.annotate(dia=TruncDate('realizado_em')).values('dia').annotate(total=Count('id')).order_by('dia'))
    turmas_datas = list(base_realizados.annotate(dia=TruncDate('realizado_em')).values('ano_serie', 'turma', 'dia').annotate(total=Count('id')).order_by('ano_serie', 'turma', 'dia'))
    resumo_turmas = list(registros_base.values('ano_serie', 'turma').annotate(
        total=Count('id'), realizados=Count('id', filter=Q(situacao='realizado')),
        pendentes=Count('id', filter=Q(situacao='pendente')),
        ausentes=Count('id', filter=Q(situacao='ausente')),
    ).order_by('ano_serie', 'turma'))
    for item in resumo_turmas:
        item['percentual'] = round(item['realizados'] * 100 / item['total'], 1) if item['total'] else 0

    return _render(request, 'acompanhamento_avaliacoes/detalhe.html', {
        'importacao': importacao, 'registros': pagina,
        'arquivos_originais': importacao.arquivos_originais.all(),
        'situacao_filtro': situacao, 'turma_filtro': turma, 'turno_filtro': turno, 'ano_filtro': ano,
        'turnos_disponiveis': __import__('turmas.models', fromlist=['Turma']).Turma.TURNOS,
        'busca': q, 'data_inicio': data_inicio_txt, 'data_fim': data_fim_txt,
        'turmas_disponiveis': list(registros_base.exclude(turma='').values_list('turma', flat=True).distinct().order_by('turma')),
        'anos_disponiveis': list(registros_base.exclude(ano_serie='').values_list('ano_serie', flat=True).distinct().order_by('ano_serie')),
        'total_filtrado': total_filtrado, 'datas_realizacao': datas_realizacao,
        'turmas_datas': turmas_datas, 'resumo_turmas': resumo_turmas,
    })



@login_required
def relatorios(request):
    """Painel de aplicações, comparação por período e listas operacionais."""
    _somente_gestao(request.user)
    aplicacoes_base = ImportacaoAvaliacao.objects.select_related('avaliacao').all()
    avaliacao_id = request.GET.get('avaliacao', '').strip()
    ano_letivo = request.GET.get('ano_letivo', '').strip()
    inicio_txt = request.GET.get('data_inicio', '').strip()
    fim_txt = request.GET.get('data_fim', '').strip()
    aplicacao_id = request.GET.get('aplicacao', '').strip()
    inicio = parse_date(inicio_txt) if inicio_txt else None
    fim = parse_date(fim_txt) if fim_txt else None
    if avaliacao_id.isdigit():
        aplicacoes_base = aplicacoes_base.filter(avaliacao_id=avaliacao_id)
    if ano_letivo.isdigit():
        aplicacoes_base = aplicacoes_base.filter(avaliacao__ano_letivo=int(ano_letivo))
    if inicio:
        aplicacoes_base = aplicacoes_base.filter(criado_em__date__gte=inicio)
    if fim:
        aplicacoes_base = aplicacoes_base.filter(criado_em__date__lte=fim)
    aplicacoes = aplicacoes_base.order_by('-criado_em')
    comparativo = list(aplicacoes.annotate(
        qtd_realizados=Count('registros', filter=Q(registros__situacao='realizado')),
        qtd_pendentes=Count('registros', filter=Q(registros__situacao='pendente')),
        qtd_ausentes=Count('registros', filter=Q(registros__situacao='ausente')),
        qtd_outros=Count('registros', filter=Q(registros__situacao='outro')),
    ).order_by('-criado_em')[:500])
    selecionada = aplicacoes.filter(pk=aplicacao_id).first() if aplicacao_id.isdigit() else aplicacoes.first()
    registros_base = selecionada.registros.select_related('aluno', 'aluno__turma').all() if selecionada else RegistroParticipacao.objects.none()

    turma = request.GET.get('turma', '').strip()
    turno = request.GET.get('turno', '').strip()
    ano = request.GET.get('ano', '').strip()
    situacao = request.GET.get('situacao', '').strip()
    q = request.GET.get('q', '').strip()
    realizacao_inicio_txt = request.GET.get('realizacao_inicio', '').strip()
    realizacao_fim_txt = request.GET.get('realizacao_fim', '').strip()
    realizacao_inicio = parse_date(realizacao_inicio_txt) if realizacao_inicio_txt else None
    realizacao_fim = parse_date(realizacao_fim_txt) if realizacao_fim_txt else None
    registros = registros_base
    if turma: registros = registros.filter(turma=turma)
    if turno: registros = registros.filter(aluno__turma__turno=turno)
    if ano: registros = registros.filter(ano_serie=ano)
    if situacao in {'realizado', 'pendente', 'ausente', 'outro'}: registros = registros.filter(situacao=situacao)
    if q: registros = registros.filter(Q(nome_aluno__icontains=q) | Q(matricula__icontains=q))
    # Datas de realização só se aplicam a registros que possuem data; não devem
    # ocultar pendentes/ausentes sem data quando o usuário solicita a lista de sala.
    if realizacao_inicio: registros = registros.filter(Q(realizado_em__date__gte=realizacao_inicio) | Q(realizado_em__isnull=True, situacao__in=['pendente', 'ausente', 'outro']))
    if realizacao_fim: registros = registros.filter(Q(realizado_em__date__lte=realizacao_fim) | Q(realizado_em__isnull=True, situacao__in=['pendente', 'ausente', 'outro']))

    resumo = registros.aggregate(
        total=Count('id'), realizados=Count('id', filter=Q(situacao='realizado')),
        pendentes=Count('id', filter=Q(situacao='pendente')),
        ausentes=Count('id', filter=Q(situacao='ausente')),
        outros=Count('id', filter=Q(situacao='outro')),
    )
    lista_tipo = request.GET.get('lista', 'pendencias').strip()
    if lista_tipo not in {'pendencias', 'todos'}:
        lista_tipo = 'pendencias'
    pendencias = registros.filter(situacao__in=['pendente', 'ausente', 'outro']).order_by('ano_serie', 'turma', 'nome_aluno')
    lista_exportacao = registros.order_by('ano_serie', 'turma', 'nome_aluno') if lista_tipo == 'todos' else pendencias
    if request.GET.get('csv') == '1':
        resposta = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        sufixo = 'todos' if lista_tipo == 'todos' else 'pendentes_ausentes'
        resposta['Content-Disposition'] = f'attachment; filename="avaliacao_{selecionada.pk if selecionada else "sem_aplicacao"}_{sufixo}.csv"'
        escritor = csv.writer(resposta, delimiter=';')
        escritor.writerow(['Avaliação', 'Aplicação em', 'Ano letivo', 'Ano/série', 'Turma', 'Turno', 'Estudante', 'Matrícula', 'Situação', 'Participação', 'Data de realização'])
        for item in lista_exportacao:
            turno_aluno = item.aluno.turma.get_turno_display() if item.aluno_id and item.aluno.turma_id else ''
            escritor.writerow([selecionada.avaliacao.nome, timezone.localtime(selecionada.criado_em).strftime('%d/%m/%Y %H:%M'), selecionada.avaliacao.ano_letivo, item.ano_serie, item.turma, turno_aluno, item.nome_aluno, item.matricula, item.get_situacao_display(), item.participacao, timezone.localtime(item.realizado_em).strftime('%d/%m/%Y %H:%M') if item.realizado_em else ''])
        return resposta
    from turmas.models import Turma
    turmas = list(registros_base.exclude(turma='').values_list('turma', flat=True).distinct().order_by('turma'))
    anos = list(registros_base.exclude(ano_serie='').values_list('ano_serie', flat=True).distinct().order_by('ano_serie'))
    agrupado = list(pendencias.values('ano_serie', 'turma').annotate(total=Count('id')).order_by('ano_serie', 'turma'))
    # Resumo adicional por turno: considera apenas vínculos de turma existentes.
    agrupado_turno = list(pendencias.values('aluno__turma__turno').annotate(total=Count('id')).order_by('aluno__turma__turno'))
    for item in agrupado_turno:
        codigo_turno = item.get('aluno__turma__turno')
        item['turno_label'] = dict(Turma.TURNOS).get(codigo_turno, 'Não identificado') if codigo_turno else 'Não identificado'
    imprimir = request.GET.get('imprimir') == '1'
    lista_exibicao = lista_exportacao
    pagina = lista_exibicao if imprimir else Paginator(lista_exibicao, 100).get_page(request.GET.get('pagina'))
    anos_letivos = list(Avaliacao.objects.values_list('ano_letivo', flat=True).distinct().order_by('-ano_letivo'))
    total_pendencias = pendencias.count()
    total_filtrado = registros.count()
    percentual_realizacao = round((resumo['realizados'] or 0) * 100 / total_filtrado, 1) if total_filtrado else 0
    return _render(request, 'acompanhamento_avaliacoes/relatorios.html', {
        'avaliacoes': Avaliacao.objects.order_by('-ano_letivo', 'nome'), 'aplicacoes': aplicacoes[:500],
        'comparativo': comparativo, 'selecionada': selecionada, 'registros': pagina,
        'resumo': resumo, 'total_pendencias': total_pendencias, 'total_filtrado': total_filtrado,
        'percentual_realizacao': percentual_realizacao, 'agrupado': agrupado, 'agrupado_turno': agrupado_turno,
        'imprimir': imprimir, 'lista_exibicao_total': lista_exportacao.count(),
        'turmas_disponiveis': turmas, 'anos_disponiveis': anos, 'anos_letivos': anos_letivos,
        'turnos_disponiveis': Turma.TURNOS, 'filtro_avaliacao': avaliacao_id,
        'filtro_ano_letivo': ano_letivo, 'filtro_aplicacao': str(selecionada.pk) if selecionada else aplicacao_id,
        'data_inicio': inicio_txt, 'data_fim': fim_txt, 'realizacao_inicio': realizacao_inicio_txt,
        'realizacao_fim': realizacao_fim_txt, 'turma_filtro': turma, 'turno_filtro': turno,
        'ano_filtro': ano, 'situacao_filtro': situacao, 'busca': q, 'lista_tipo': lista_tipo,
    })

