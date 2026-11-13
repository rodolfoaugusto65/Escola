from pathlib import Path
from django.db import migrations


def publicar_comunicado_r11(apps, schema_editor):
    ComunicadoSistema = apps.get_model('busca_ativa', 'ComunicadoSistema')
    arquivo_txt = Path(__file__).resolve().parents[1] / 'atualizacoes' / '2026.11.13.11.txt'
    try:
        linhas = arquivo_txt.read_text(encoding='utf-8-sig').splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise RuntimeError(f'Não foi possível ler o TXT da atualização {arquivo_txt.name}: {exc}') from exc
    campos, corpo, lendo_texto = {}, [], False
    for linha in linhas:
        if not lendo_texto and ':' in linha:
            chave, valor = linha.split(':', 1)
            chave = chave.strip().upper()
            if chave in {'VERSAO', 'TITULO'}:
                campos[chave] = valor.strip()
                continue
            if chave == 'TEXTO':
                if valor.strip():
                    corpo.append(valor.strip())
                lendo_texto = True
                continue
        if lendo_texto:
            corpo.append(linha)
    versao, titulo, texto = campos.get('VERSAO', ''), campos.get('TITULO', ''), '\n'.join(corpo).strip()
    if not versao or not titulo or not texto:
        raise RuntimeError('TXT da atualização inválido: informe VERSAO:, TITULO: e TEXTO:.')
    ComunicadoSistema.objects.update_or_create(
        versao=versao,
        defaults={'titulo': titulo[:180], 'texto': texto, 'ativo': True},
    )


class Migration(migrations.Migration):
    dependencies = [('busca_ativa', '0010_comunicado_relatorios_impressao_r10')]
    operations = [migrations.RunPython(publicar_comunicado_r11, migrations.RunPython.noop)]
