"""Regras nacionais fixas de dias não letivos usadas pelo GerEdu."""
from datetime import date


def feriados_fixos_geredu(ano):
    # Datas solicitadas pela gestão escolar: Consciência Negra e 08 de dezembro.
    return {date(int(ano), 11, 20), date(int(ano), 12, 8)}


def eh_dia_letivo(data, datas_adicionais=None):
    datas = set(datas_adicionais or ()) | feriados_fixos_geredu(data.year)
    return data.weekday() < 5 and data not in datas
