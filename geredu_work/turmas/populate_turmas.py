from turmas.models import AnoLetivo, Turma

# Criar anos letivos
anos = [2024, 2025, 2026]
for ano in anos:
    AnoLetivo.objects.get_or_create(ano=ano)

# Criar turmas
turmas = [
    {"nome": "1º A", "etapa": "Fundamental", "ano_letivo": 2024, "turno": "Manhã"},
    {"nome": "1º B", "etapa": "Fundamental", "ano_letivo": 2024, "turno": "Tarde"},
    {"nome": "2º A", "etapa": "Fundamental", "ano_letivo": 2025, "turno": "Manhã"},
]

for t in turmas:
    ano = AnoLetivo.objects.get(ano=t["ano_letivo"])
    Turma.objects.get_or_create(nome=t["nome"], etapa=t["etapa"], ano_letivo=ano, turno=t["turno"])
