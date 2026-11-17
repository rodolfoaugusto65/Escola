from django.test import SimpleTestCase
from .views import _classificar, _norm, _parse_data_realizacao

class ClassificacaoParticipacaoTests(SimpleTestCase):
    def test_statuses_da_planilha_plurall(self):
        self.assertEqual(_classificar('Presente'), 'realizado')
        self.assertEqual(_classificar('Aguardando Participação'), 'pendente')

    def test_status_negativo_nao_e_realizado(self):
        self.assertEqual(_classificar('Não realizado'), 'pendente')
        self.assertEqual(_classificar('Ausente'), 'ausente')

    def test_normalizacao_de_colunas(self):
        self.assertEqual(_norm('Ano/Série'), 'anoserie')
        self.assertEqual(_norm('Participação'), 'participacao')


class DataRealizacaoTests(SimpleTestCase):
    def test_iso_utc_com_z(self):
        dt = _parse_data_realizacao('2026-11-05T15:06:45Z')
        self.assertIsNotNone(dt)
        self.assertEqual(dt.utcoffset().total_seconds(), 0)

    def test_iso_plurall_minusculo(self):
        dt = _parse_data_realizacao('2026-11-05t18:21:05z')
        self.assertIsNotNone(dt)
        self.assertEqual(dt.utcoffset().total_seconds(), 0)

    def test_data_hora_brasileira(self):
        dt = _parse_data_realizacao('05/11/2026 12:06:45')
        self.assertIsNotNone(dt)

    def test_vazio(self):
        self.assertIsNone(_parse_data_realizacao(''))
