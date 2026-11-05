# M5.2 — Fidelidade determinística dos detalhes de produto

## Problema observado

Na execução manual, o LLM interpretou o campo CSV `neck: Nato` como "Madeira da escala: Nato". O CSV informa somente o material do braço/pescoço; não informa o material da escala.

## Correção

Quando o modelo solicita somente `get_product_details`, o runtime formata a resposta final diretamente a partir do resultado estruturado da ferramenta, sem pedir ao LLM uma segunda geração para reinterpretar os campos.

Mapeamento implementado:

| Chave do CSV | Rótulo apresentado |
|---|---|
| `top` | Tampo |
| `back_sides` | Fundo e laterais |
| `neck` | Braço |
| `strings` | Cordas |
| `scale` | Comprimento da escala |
| `electronics` | Sistema eletrônico |
| `color` | Cor/acabamento |

Também são apresentados preço, disponibilidade, estoque cadastrado, status, descrição e promoção ativa, quando aplicável. A resposta informa que preço e estoque são snapshots.

## Teste de regressão

Foi incluído um teste que confirma que `neck: Nato` é renderizado como `Braço: Nato`, `scale: 650mm` como `Comprimento da escala: 650mm`, e que a resposta não contém "Madeira da escala".

Validação após a alteração: **103 testes aprovados** com `python -m pytest -q` em Python 3.13.5.
