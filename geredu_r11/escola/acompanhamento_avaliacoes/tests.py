from django.test import SimpleTestCase
from .views import _classificar, _norm

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
