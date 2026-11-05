# M5 — Relatório final de testes

## Escopo

A suíte cobre o contrato dos adaptadores de modelo, allow-list e validação das ferramentas, orquestração modelo/ferramenta, fluxo de verificação local de telefone, sanitização do histórico, integração com o dataset real, recuperação do manual, conflitos de política e formatação técnica determinística de detalhes de produto.

## Resultados de validação

- Testes do projeto antes do hotfix de fidelidade M5.2: 102 aprovados.
- Testes completos após M5.2: **103 aprovados**.
- Comando: `python -m pytest -q`.
- Ambiente da validação do pacote: Python 3.13.5.

Os testes de adaptador usam clientes simulados e não fazem chamadas externas. A validação manual com Groq foi realizada na CLI para saudação e busca de catálogo; consultas de detalhes do produto e política foram exercitadas, e o runtime recebeu testes de regressão para impedir a reinterpretação incorreta de `neck` como madeira da escala.

## Controles de segurança e qualidade

- Apenas seis funções conhecidas são declaradas e despachadas.
- Os argumentos são validados por schemas Pydantic ou limites explícitos.
- Funções desconhecidas falham de forma segura.
- Telefone de pedido é tratado fora do histórico do modelo, enquanto a verificação está pendente.
- A consulta de status depende de autorização vinculada a sessão e pedido.
- Conflitos não resolvidos do manual acionam resposta determinística de revisão humana.
- Consultas isoladas de detalhes de produto são formatadas a partir de campos estruturados para preservar os rótulos técnicos de origem.
- Resultados de estoque e pedidos são identificados como snapshots.

## Limitações

- Os testes de adaptador simulam a API do provedor; a disponibilidade e os limites de Groq/Gemini são externos à suíte.
- O atendimento é uma CLI sem persistência do histórico.
- Estoque, promoções e pedidos não são sincronizados com sistemas de produção.
