"""Armazenamento consistente dos arquivos originais do GerEdu."""
from django.conf import settings
from django.core.files.storage import FileSystemStorage, default_storage


def storage_geredu():
    """Usa disco local em DEBUG sem R2; em produção exige o storage configurado."""
    bucket = (getattr(settings, "AWS_STORAGE_BUCKET_NAME", "") or "").strip()
    endpoint = (getattr(settings, "AWS_S3_ENDPOINT_URL", "") or "").strip()
    access = (getattr(settings, "AWS_ACCESS_KEY_ID", "") or "").strip()
    secret = (getattr(settings, "AWS_SECRET_ACCESS_KEY", "") or "").strip()
    r2_ok = all((bucket, endpoint, access, secret))
    if getattr(settings, "DEBUG", False) and not r2_ok:
        return FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)
    if not r2_ok:
        raise RuntimeError(
            "Cloudflare R2 não está configurado corretamente. Confira "
            "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME "
            "e AWS_S3_ENDPOINT_URL antes de importar arquivos em produção."
        )
    return default_storage


def salvar_arquivo_geredu(field_file, nome, conteudo, *, save=True):
    """Salva FileField usando backend compatível com o ambiente atual.

    O storage é associado ao campo antes do save, evitando que uma instância
    antiga do backend S3 tente enviar Bucket=None durante testes locais.
    """
    storage = storage_geredu()
    field_file.field.storage = storage
    field_file.save(nome, conteudo, save=save)
    return field_file.name
