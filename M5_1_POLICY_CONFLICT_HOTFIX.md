# M5.1 — Correção de segurança para conflitos no manual

## Objetivo

Evitar que o modelo escolha arbitrariamente uma interpretação quando a consulta ao manual encontra uma política marcada para revisão humana.

## O que mudou

- Consultas amplas sobre **trocas e devoluções** agora sinalizam revisão humana, porque podem envolver a divergência entre a seção 4.2 (troca por defeito após 30 dias) e a seção 8.1 (garantia legal de 90 dias).
- Uma troca explicitamente descrita como **troca por preferência** continua sem escalonamento automático por esse conflito específico.
- O runtime do agente agora aplica um bloqueio determinístico: se `search_store_policies` retornar `requires_human_review=true`, a resposta final não é redigida novamente pelo LLM. O próprio runtime apresenta as referências divergentes e informa que a equipe da loja precisa confirmar.
- O registro de chamada e resultado da ferramenta é mantido no histórico, sem quebrar a continuidade da sessão.

## Comportamento esperado

Para a pergunta:

> Como funciona a política de troca e devolução da Empório da Música?

O agente não deve afirmar que a garantia termina após 30 dias. Deve informar que o manual apresenta orientações que precisam ser conciliadas: seção 4.2, página 4, e seção 8.1, página 7. A equipe da loja precisa confirmar a aplicação ao caso específico.

## Arquivos incluídos

- `app/agent/runtime.py`
- `app/knowledge/conflict_registry.py`
- `tests/unit/test_agent_runtime_m5.py`
- `tests/unit/test_knowledge_conflicts.py`
- `tests/integration/test_knowledge_real_policy.py`

## Aplicação

Extraia o ZIP na raiz do repositório com `Expand-Archive -DestinationPath . -Force`.

Depois execute:

```powershell
python -m pytest -q
```

Resultado validado nesta cópia: **102 passed** (Python 3.13.5). A suíte deve ser repetida no ambiente do projeto antes do commit.

## Escopo

Este hotfix não altera o catálogo, os serviços de pagamento, o provedor Groq, os dados privados, nem as chaves de API. Não inclui o manual original ou arquivos com dados de clientes.
