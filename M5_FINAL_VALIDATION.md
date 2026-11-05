# M5 — Registro de validação final

## Escopo validado

- Adaptador Groq via endpoint OpenAI-compatible com `openai/gpt-oss-20b`.
- Seis ferramentas registradas e despachadas pela aplicação.
- Busca de catálogo com CSVs reais.
- Detalhes de produto com formatação determinística das propriedades técnicas.
- Recuperação de política a partir do PDF real, com seção e página.
- Barreira determinística para política conflitante (M5.1).
- Verificação local de telefone para consulta de pedido.
- Proteção contra envio de telefone ao histórico do LLM.

## Testes automatizados

- Antes da correção de fidelidade dos detalhes do produto: 102 testes aprovados.
- Após a correção M5.2: **103 testes aprovados**.
- Ambiente desta validação: Python 3.13.5.
- Comando: `python -m pytest -q`.

Os testes de adaptador usam clientes simulados; eles não substituem testes manuais com a chave real do provedor. A execução manual com Groq foi validada pelo desenvolvedor para saudação e busca de catálogo; os detalhes de produto e a política de troca/devolução também foram testados no terminal. A formatação determinística de detalhes foi então coberta por teste de regressão.

## Correções de confiabilidade

### M5.1 — conflitos do manual

Quando a ferramenta de política sinaliza `requires_human_review=true`, o runtime não solicita uma nova resposta ao modelo. Para conflitos de garantia, apresenta as referências às seções 4.2 e 8.1 e solicita confirmação da equipe.

### M5.2 — fidelidade de especificações

Quando o LLM solicita apenas `get_product_details`, o runtime apresenta uma ficha determinística usando o mapa explícito:

- `top` → Tampo
- `back_sides` → Fundo e laterais
- `neck` → Braço
- `strings` → Cordas
- `scale` → Comprimento da escala
- `electronics` → Sistema eletrônico
- `color` → Cor/acabamento

Isso evita, por exemplo, que `neck: Nato` seja descrito incorretamente como madeira da escala.

## Limites remanescentes

- Os dados operacionais são snapshots, não dados em tempo real.
- A sessão CLI é volátil e não persiste o histórico.
- Não há interface web, CRM, checkout ou integração com equipe humana.
- Disponibilidade do modelo, latência e custo dependem do provedor externo.
