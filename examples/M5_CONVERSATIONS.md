# Exemplos de interação — Empório da Música

Este arquivo reúne quatro cenários de demonstração do agente. Os nomes, preços, estoque e especificações de produto vêm do snapshot CSV fornecido; as regras de atendimento vêm do manual de políticas. A redação do LLM pode variar. Estoque, preços e pedidos não são consultas em tempo real.

## 1. Busca de produtos por orçamento

**Cliente:** Gostaria de um violão até R$ 1.000,00.

**Empório:** Encontrei opções cadastradas dentro desse orçamento:

| ID | Produto | Preço | Estoque no snapshot |
|---:|---|---:|---:|
| 83 | Tagima Memphis AC-39 Nylon Natural | R$ 429,90 | 15 |
| 85 | Rozini RC-104 Nylon Estudante | R$ 459,90 | 10 |
| 89 | Shelby SN-100 Folk Aço Preto | R$ 549,00 | 5 |
| 88 | Giannini GF-1R Aço Folk Sunburst | R$ 579,90 | 7 |
| 81 | Yamaha C40 Nylon Natural | R$ 599,90 | 12 |
| 84 | Giannini GN-15 Nylon Cedr Natural | R$ 689,00 | 6 |
| 87 | Yamaha F310 Aço Natural | R$ 699,90 | 14 |
| 86 | Tagima Dallas Tuner Aço Natural | R$ 749,00 | 9 |
| 107 | Shelby SGD-195E Elétrico Aço Sunburst | R$ 799,00 | 6 |
| 82 | Yamaha C70 Nylon Natural | R$ 849,00 | 8 |

Todos estão abaixo de R$ 1.000,00 e aparecem como disponíveis no snapshot consultado. Posso detalhar as diferenças entre os modelos.

**Ferramenta:** `search_products` com categoria, limite máximo de preço e disponibilidade.

## 2. Detalhes técnicos de um produto

**Cliente:** Gostaria de saber mais sobre o Yamaha C40, ID 81. Quais são suas especificações?

**Empório:**

**Yamaha C40 Nylon Natural** (ID 81)

| Campo | Informação cadastrada |
|---|---|
| Categoria | Violões |
| Preço | R$ 599,90 |
| Disponibilidade | Disponível |
| Estoque | 12 unidades (snapshot) |
| Tampo | Spruce |
| Fundo e laterais | Meranti |
| Braço | Nato |
| Cordas | Nylon |
| Comprimento da escala | 650 mm |
| Sistema eletrônico | Não |
| Cor/acabamento | Natural |

Descrição cadastrada: violão clássico com tampo em Spruce e fundo/laterais em Meranti, indicado para estudantes e iniciantes.

Os dados de preço e estoque refletem o snapshot do catálogo fornecido. As especificações são apresentadas a partir das chaves do CSV; por exemplo, `neck` é apresentado como braço, não como madeira da escala.

**Ferramenta:** `get_product_details`. A ficha acima é formatada pelo runtime a partir dos campos estruturados.

## 3. Direito de arrependimento em compra online

**Cliente:** Comprei pela internet e me arrependi. Até quando posso devolver?

**Empório:** Conforme a seção 4.1 do manual, a solicitação de devolução por arrependimento pode ser feita em até **7 dias corridos após o recebimento**. O manual também indica que o produto deve estar sem uso, na embalagem original e acompanhado dos acessórios e manuais. O reembolso é previsto na mesma forma de pagamento, em até 10 dias úteis, e o frete da devolução por arrependimento fica por conta da loja. (Manual, seção 4.1, página 4.)

**Ferramenta:** `search_store_policies`, que recupera o trecho de direito de arrependimento. A resposta deve ser usada como orientação baseada na versão fornecida do manual, não como confirmação de que a loja não publicou uma atualização posterior.

## 4. Pergunta ampla que envolve política conflitante

**Cliente:** Como funciona a política de troca e devolução da Empório da Música?

**Empório:** O manual apresenta duas orientações que precisam ser conciliadas: a seção 4.2 (página 4) menciona o acionamento do fabricante após 30 dias, enquanto a seção 8.1 (página 7) prevê garantia legal de 90 dias. O documento não esclarece como essas regras se aplicam em conjunto. Para não fornecer uma informação incorreta, não vou afirmar que a cobertura termina após 30 dias. A equipe da loja precisa confirmar o procedimento para o caso específico.

**Ferramenta:** `search_store_policies`. Como a ferramenta sinaliza `requires_human_review=true`, o runtime aplica uma barreira determinística e não solicita ao LLM que escolha uma interpretação.

---

## Observações sobre os exemplos

- Os cenários 1 e 2 foram exercitados manualmente no terminal durante a validação do agente; a formatação dos detalhes foi posteriormente endurecida no runtime para preservar os nomes técnicos das propriedades do CSV.
- O cenário 3 é um exemplo de recuperação de evidência de uma seção não conflitante do manual.
- O cenário 4 demonstra uma situação não trivial de política e revisão humana, exigida como um dos exemplos do desafio.
- Nenhum exemplo inclui telefone, CPF, e-mail ou dados pessoais de clientes.
