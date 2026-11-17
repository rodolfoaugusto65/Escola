from pathlib import Path
from django.db import migrations


def publicar_comunicado_r15(apps, schema_editor):
    ComunicadoSistema = apps.get_model("busca_ativa", "ComunicadoSistema")
    LeituraComunicado = apps.get_model("busca_ativa", "LeituraComunicado")
    arquivo_txt = Path(__file__).resolve().parents[1] / "atualizacoes" / "2026.11.13.15.txt"
    try:
        linhas = arquivo_txt.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"Não foi possível ler o TXT da atualização r15: {exc}") from exc
    campos, corpo, lendo_texto = {}, [], False
    for linha in linhas:
        if not lendo_texto and ":" in linha:
            chave, valor = linha.split(":", 1)
            chave = chave.strip().upper()
            if chave in {"VERSAO", "TITULO"}:
                campos[chave] = valor.strip()
                continue
            if chave == "TEXTO":
                if valor.strip():
                    corpo.append(valor.strip())
                lendo_texto = True
                continue
        if lendo_texto:
            corpo.append(linha)
    versao = campos.get("VERSAO", "")
    titulo = campos.get("TITULO", "")
    texto = "\n".join(corpo).strip()
    if not versao or not titulo or not texto:
        raise RuntimeError("TXT da atualização r15 inválido.")
    comunicado, criado = ComunicadoSistema.objects.get_or_create(
        versao=versao,
        defaults={"titulo": titulo[:180], "texto": texto, "ativo": True},
    )
    if not criado and (
        comunicado.titulo != titulo[:180] or comunicado.texto != texto or not comunicado.ativo
    ):
        LeituraComunicado.objects.filter(comunicado_id=comunicado.pk).delete()
        comunicado.titulo, comunicado.texto, comunicado.ativo = titulo[:180], texto, True
        comunicado.save(update_fields=["titulo", "texto", "ativo"])


class Migration(migrations.Migration):
    dependencies = [("busca_ativa", "0012_comunicado_assistente_r14")]
    operations = [migrations.RunPython(publicar_comunicado_r15, migrations.RunPython.noop)]
