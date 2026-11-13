import sqlite3
from django.test import SimpleTestCase
from .views import _decimal_import, _percent, _sqlite_value


class ImportacaoBackupSQLiteTests(SimpleTestCase):
    def test_coluna_opcional_ausente_retorna_padrao(self):
        row = sqlite3.Row
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        conn.execute('CREATE TABLE exemplo (id INTEGER, nome TEXT)')
        conn.execute('INSERT INTO exemplo VALUES (1, NULL)')
        registro = conn.execute('SELECT * FROM exemplo').fetchone()
        self.assertEqual(_sqlite_value(registro, 'nome', ''), None)
        self.assertEqual(_sqlite_value(registro, 'coluna_antiga', 'padrão'), 'padrão')
        conn.close()

    def test_percentuais_e_valores_nulos(self):
        self.assertEqual(_percent(None), 0)
        self.assertEqual(_percent('0,35'), 35)
        self.assertEqual(_decimal_import(None), 0)
