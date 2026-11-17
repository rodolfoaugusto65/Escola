# GerEdu — correções visuais e acompanhamento por turma

## O que foi ajustado

1. Removido o script global que transformava automaticamente o primeiro título da página em um banner. Esse script movia visualmente títulos e botões para o mesmo contêiner e causava sobreposição, títulos com contraste inadequado e cabeçalhos de largura excessiva.
2. Mantidos os estilos globais de cartões, formulários, tabelas e topbar, com regras adicionais de estabilidade responsiva.
3. O painel de Avaliações agora apresenta resumo visual por turma, com ano/série, total de alunos, realizados, pendentes, percentual e barra de progresso.
4. Os filtros de ano/série e turma passaram a ser listas selecionáveis, preenchidas com os valores da importação selecionada.
5. Cada cartão de turma possui atalho para abrir o painel filtrado naquela turma e visualizar os alunos pendentes.
6. Os percentuais por turma são calculados no servidor. Não foram criadas migrações nem alterados modelos/banco de dados.

## Arquivos alterados

- `core/templates/core/base.html`
- `core/static/core/css/style.css`
- `acompanhamento_avaliacoes/views.py`
- `acompanhamento_avaliacoes/templates/acompanhamento_avaliacoes/painel.html`

## Aplicação

Faça backup do projeto. Extraia o pacote mantendo os caminhos relativos e substitua os arquivos correspondentes. Não substitua `.env`, banco de dados, `media/` ou credenciais.

Depois execute localmente:

```powershell
python manage.py check
python manage.py runserver
```

Teste as páginas Alunos, Turmas, Relatórios, Ocorrências, Frequência, Busca Ativa e Avaliações. Em Avaliações, selecione uma avaliação e confira os cartões por turma e o atalho de detalhamento.

Não há migrações novas. A publicação no Railway deve ocorrer somente depois da validação local e backup do PostgreSQL.
