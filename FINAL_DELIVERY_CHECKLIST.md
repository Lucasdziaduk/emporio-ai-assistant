# Checklist final de entrega — Artefact AI Engineer

O desafio exige três entregáveis: repositório Git público com histórico real, README completo e entre 3 e 5 exemplos de conversa. Também exige responder ao e-mail original do processo seletivo com o link do repositório.

## Conteúdo técnico

- [x] Agente em Python.
- [x] Persona em português brasileiro.
- [x] Respostas baseadas em dados e contexto fornecidos.
- [x] Ferramentas para catálogo, detalhes, pedidos, políticas, loja e pagamento.
- [x] RAG do manual com referências de seção/página.
- [x] Tratamento determinístico de conflitos do manual.
- [x] Tratamento de perguntas fora do escopo no prompt.
- [x] Proteção local do telefone na verificação de pedidos.
- [x] CLI funcional com Groq; Gemini mantido como adaptador alternativo.
- [x] Teste automatizado de fidelidade de campos técnicos.

## Entregáveis do desafio

- [x] README com instruções, decisões técnicas, limitações e uso de assistente de código.
- [x] Quatro exemplos de interação em `examples/M5_CONVERSATIONS.md`.
- [ ] Repositório GitHub público atualizado com os commits M5, M5.1 e M5.2.
- [ ] Link do repositório enviado em resposta ao e-mail original.

## Antes de publicar

1. Execute `python -m pytest -q` no ambiente local e confira o resultado.
2. Execute `git status --short` e `git diff --check`.
3. Confirme que `.env`, `data/private/`, arquivos CSV de origem, banco SQLite e PDF restrito não aparecem no staging.
4. Revise com `git diff --cached --name-only` antes de cada commit.
5. Faça commits separados, sem force-push. Após o prazo de entrega, não altere o repositório.

## Comandos de revisão (PowerShell)

```powershell
git status --short
git diff --check
git check-ignore .env data/private/emporio.sqlite3 data/private/source/customers.csv data/private/store_policies.pdf
```

O desafio recomenda manter histórico de progresso real e proíbe alterações no repositório depois do horário de entrega.
